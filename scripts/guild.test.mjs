import test from 'node:test';
import assert from 'node:assert/strict';
import { timingSafeEqual } from 'node:crypto';
import reader from '../guild/worker/index.mjs';
import publisher from '../guild/worker/publish.mjs';
import { SNAPSHOT_LIFETIME } from '../guild/worker/snapshots.mjs';
import { AUCTION_DISPATCH_URL, collectAuctionIfNeeded, dispatchAuctionCollect } from '../guild/worker/dispatch.mjs';
import { buildRecipeIndex, searchRecipes } from '../professions/artisans/search.mjs';

const sample = {
  artisans: [{ characterId: 123, name: '測試 工匠', professions: [
    { id: 197, skill: 150, maxSkill: 225, recipeIds: [1, 2] },
    { id: 164, skill: 100, maxSkill: 150, recipeIds: [3] },
  ] }],
  recipes: { 1: { name: '同名配方', originalName: 'TEST BAG' }, 2: { name: '同名配方' }, 3: { name: '測試鍛造' } },
};

function snapshot(start = Date.now()) {
  return { schema: 1, fetchedAt: new Date(start).toISOString(), expiresAt: new Date(start + SNAPSHOT_LIFETIME).toISOString(), ...sample };
}

test('同名配方按 ID 保留，支援原名與專業交叉搜尋', () => {
  const groups = buildRecipeIndex(sample);
  assert.deepEqual(searchRecipes(groups, '同名', '').map(item => item.id), [1, 2]);
  assert.deepEqual(searchRecipes(groups, ' ｔｅｓｔ bag ', '197').map(item => item.id), [1]);
  assert.deepEqual(searchRecipes(groups, '同名', '164'), []);
  assert.deepEqual(searchRecipes(groups, '', '164').map(item => item.id), [3]);
  assert.deepEqual(searchRecipes(groups, '', ''), []);
});

test('公開資料僅回傳有效快照，工匠資料排除內部 ID', async () => {
  const url = 'https://worker.example/artisans.json';
  const env = { SNAPSHOTS: { get: async () => snapshot() } };
  const response = await reader.fetch(new Request(url), env);
  assert.equal(response.status, 200);
  assert.equal(response.headers.get('Cache-Control'), 'no-store');
  const body = await response.json();
  assert.equal(body.artisans[0].name, '測試 工匠');
  assert.equal('characterId' in body.artisans[0], false);
  env.SNAPSHOTS.get = async () => snapshot(Date.now() - SNAPSHOT_LIFETIME);
  assert.equal((await reader.fetch(new Request(url), env)).status, 404);
  assert.equal((await reader.fetch(new Request(url, { method: 'PUT' }), env)).status, 405);
});

test('發布需授權，依原始到期時間寫入 KV', async () => {
  const url = 'https://publisher.example/artisans.json';
  const original = snapshot(Date.now() - 60_000);
  const writes = [];
  const env = { PUBLISH_TOKEN: 'synthetic', SNAPSHOTS: { put: async (...values) => writes.push(values) } };
  const without = await publisher.fetch(new Request(url, { method: 'PUT', body: JSON.stringify(original) }), env);
  assert.equal(without.status, 401);
  // Workers exposes this Web Crypto extension; Node provides the equivalent as a module function.
  const previous = crypto.subtle.timingSafeEqual;
  crypto.subtle.timingSafeEqual = timingSafeEqual;
  try {
    const headers = { Authorization: 'Bearer synthetic' };
    const response = await publisher.fetch(new Request(url, { method: 'PUT', headers, body: JSON.stringify(original) }), env);
    assert.equal(response.status, 204);
    assert.equal(writes.length, 1);
    assert.equal(writes[0][0], 'artisans');
    assert.equal(writes[0][2].expiration, Math.floor(Date.parse(original.expiresAt) / 1000));
    const expired = snapshot(Date.now() - SNAPSHOT_LIFETIME);
    assert.equal((await publisher.fetch(new Request(url, { method: 'PUT', headers, body: JSON.stringify(expired) }), env)).status, 400);
    assert.equal(writes.length, 1);
  } finally {
    if (previous) crypto.subtle.timingSafeEqual = previous;
    else delete crypto.subtle.timingSafeEqual;
  }
});

test('價階補建可覆寫同時間戳的無效快照，既有有效快照則跳過', async t => {
  const previous = crypto.subtle.timingSafeEqual;
  crypto.subtle.timingSafeEqual = timingSafeEqual;
  t.after(() => {
    if (previous) crypto.subtle.timingSafeEqual = previous;
    else delete crypto.subtle.timingSafeEqual;
  });
  const updatedAt = new Date(Date.now() - 60_000).toISOString();
  const snapshot = { schema: 1, region: 'tw', ruleset: 1, house: 113, source: 'official', updatedAt, depth: { 3: [[1600, 1]] } };
  const writes = [];
  const env = { PUBLISH_TOKEN: 'synthetic', SNAPSHOTS: {
    get: async () => ({ ...snapshot, depth: {} }), put: async (...args) => writes.push(args),
  } };
  const request = () => new Request('https://publisher.example/market-depth.json', { method: 'PUT',
    headers: { Authorization: 'Bearer synthetic' }, body: JSON.stringify(snapshot) });
  assert.equal((await publisher.fetch(request(), env)).status, 204);
  assert.deepEqual(writes.map(([key, data]) => [key, JSON.parse(data)]), [['market-depth', snapshot]]);
  env.SNAPSHOTS.get = async () => snapshot;
  assert.equal((await publisher.fetch(request(), env)).status, 204);
  assert.equal(writes.length, 1);
});

test('排程觸發拍賣收集：帶 token 呼叫 workflow_dispatch，失敗時丟錯', async () => {
  const calls = [];
  const ok = async (url, init) => { calls.push([url, init]); return new Response(null, { status: 204 }); };
  await dispatchAuctionCollect({ GITHUB_DISPATCH_TOKEN: 'synthetic' }, ok);
  assert.equal(calls.length, 1);
  assert.equal(calls[0][0], AUCTION_DISPATCH_URL);
  assert.equal(calls[0][1].method, 'POST');
  assert.equal(calls[0][1].headers.Authorization, 'Bearer synthetic');
  assert.deepEqual(JSON.parse(calls[0][1].body), { ref: 'main' });
  await assert.rejects(dispatchAuctionCollect({}, ok), /GITHUB_DISPATCH_TOKEN/u);
  assert.equal(calls.length, 1);
  const denied = async () => new Response('Bad credentials', { status: 401 });
  await assert.rejects(dispatchAuctionCollect({ GITHUB_DISPATCH_TOKEN: 'expired' }, denied), /HTTP 401 Bad credentials/u);
  assert.equal(typeof publisher.scheduled, 'function');
});

test('四個排程各讀一次 KV，午夜 :12 仍補上一天的 23 時', async () => {
  const cases = [
    ['12', '15:41', false], ['12', '14:41', true], ['12', '16:06', false],
    ['27', '16:26', false], ['27', '15:41', true], ['42', '16:41', false],
    ['42', '15:41', true], ['57', '16:41', false], ['57', '15:41', true],
  ];
  for (const [minute, snapshotTime, shouldDispatch] of cases) {
    const scheduledTime = Date.parse(`2026-11-25T16:${minute}:00Z`);
    const updatedAt = `2026-11-25T${snapshotTime}:00Z`;
    const snapshot = { schema: 1, region: 'tw', ruleset: 1, house: 113, source: 'official', updatedAt, depth: { 3: [[1600, 1]] } };
    const kvReads = [];
    const env = { GITHUB_DISPATCH_TOKEN: 'synthetic', SNAPSHOTS: { get: async (...args) => { kvReads.push(args); return snapshot; } } };
    const dispatches = [];
    const fetcher = async (_url, init) => { dispatches.push(JSON.parse(init.body)); return new Response(null, { status: 204 }); };
    await collectAuctionIfNeeded({ scheduledTime }, env, { fetcher, now: scheduledTime + 2 * 60_000 });
    assert.deepEqual(kvReads, [['market-depth', 'json']]);
    assert.deepEqual(dispatches, shouldDispatch ? [{ ref: 'main' }] : []);
  }
});

test('KV 無有效價階時要求補建，讀取失敗時保留錯誤', async () => {
  const scheduledTime = Date.parse('2026-11-25T16:57:00Z');
  const dispatches = [];
  const fetcher = async (_url, init) => { dispatches.push(JSON.parse(init.body)); return new Response(null, { status: 204 }); };
  const options = { fetcher, now: scheduledTime };
  const env = { GITHUB_DISPATCH_TOKEN: 'synthetic', SNAPSHOTS: { get: async () => null } };
  await collectAuctionIfNeeded({ scheduledTime }, env, options);
  env.SNAPSHOTS.get = async () => ({ updatedAt: '2026-11-25T16:41:00Z' });
  await collectAuctionIfNeeded({ scheduledTime }, env, options);
  const recovery = { ref: 'main', inputs: { force_refresh: 'true' } };
  assert.deepEqual(dispatches, [recovery, recovery]);
  env.SNAPSHOTS.get = async () => { throw new Error('KV unavailable'); };
  await assert.rejects(collectAuctionIfNeeded({ scheduledTime }, env, options), /KV unavailable/u);
  assert.equal(dispatches.length, 2);
});
