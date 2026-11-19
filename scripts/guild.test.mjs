import test from 'node:test';
import assert from 'node:assert/strict';
import { timingSafeEqual } from 'node:crypto';
import reader from '../guild/worker/index.mjs';
import publisher from '../guild/worker/publish.mjs';
import { SNAPSHOT_LIFETIME } from '../guild/worker/snapshots.mjs';
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
