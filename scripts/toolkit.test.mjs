import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { buyFromDepth, currentDepth, quoteLifetime } from '../market/quotes.mjs';
import { shoppingText } from '../market/tools.mjs';
import { compareRoutes } from '../crafting-leveling/route.mjs';
import { quoteRecipe } from '../professions/recipe-quotes.mjs';
import { characterSlug } from '../players/model.mjs';
import reader from '../guild/worker/index.mjs';
import { mergeItems, verifyPlan } from '../raid/model.mjs';

const catalog = JSON.parse(readFileSync(new URL('../crafting-leveling/routes.json', import.meta.url)));

test('批量報價只消耗實際價階，逾期及其他拍賣場不報價', () => {
  const now = Date.now();
  const snapshot = { schema: 1, region: 'tw', ruleset: 1, house: 113, updatedAt: new Date(now).toISOString(),
    depth: { 12359: [[10, 8], [12, 92]] } };
  const buy = buyFromDepth(currentDepth(snapshot, now), 12359, 103);
  assert.deepEqual([buy.bought, buy.spent, buy.missing], [100, 1184, 3]);
  assert.equal(currentDepth(snapshot, now + quoteLifetime), null);
  assert.equal(currentDepth({ ...snapshot, house: 114 }, now), null);
  assert.equal(buyFromDepth(null, 12359, 5).unknown, true);
});

test('六項製造都能中途起算，附魔符文棒依賴可解析', () => {
  const depth = { depth: Object.fromEntries(Object.keys(catalog.items).map(id => [id, [[10, 500000]]])) };
  for (const profession of Object.values(catalog.professions)) {
    for (const [start, target] of [[1, 150], [75, 150], [150, 225], [187, 225], [225, 300], [299, 300]]) {
      const { cost, stable } = compareRoutes(catalog, profession, { start, target, inventory: [], known: [] }, depth);
      assert.equal(cost.steps.at(-1).to, target);
      assert.equal(stable.steps.at(-1).to, target);
      assert.equal(cost.missing, 0);
    }
  }
});

test('成品產量、重複材料、自備庫存和抽成以整批為基礎計算', () => {
  const quote = quoteRecipe({
    product: { id: 2 }, units: 3,
    materials: [{ id: 1, quantity: 2 }, { id: 1, quantity: 1 }],
  }, 4, new Map([[1, 2]]), 5, { depth: { 1: [[100, 100]], 2: [[300, 100]] } });
  assert.equal(quote.batches, 2);
  assert.equal(quote.materialCost, 400);
  assert.equal(quote.direct.spent, 1200);
  assert.equal(Math.round(quote.net), 218);
});

test('雙名正規化與撤下名單會阻擋角色查詢和舊名冊', async t => {
  assert.equal(characterSlug('  測試　鐵匠 '), '測試-鐵匠');
  assert.equal(characterSlug('../測試'), null);
  const endpoint = 'https://worker.example';
  let excluded = [];
  let upstream = 0;
  t.mock.method(globalThis, 'fetch', async url => {
    upstream++;
    if (String(url).includes('oauth')) return Response.json({ access_token: 'demo', expires_in: 86400 });
    const path = decodeURIComponent(new URL(url).pathname);
    if (path.endsWith('/測試-鐵匠')) return Response.json({ id: 123, name: '測試', surname: '鐵匠', level: 50 });
    if (path.endsWith('/specializations')) return Response.json({
      specialization_groups: [{ is_active: true, specializations: [{
        specialization: { name: '武器' }, spent_points: 3, talents: [{ talent: { name: '強化英勇打擊' }, talent_rank: 3 }],
      }] }],
    });
    return Response.json({});
  });
  const fetched = new Date();
  const roster = { schema: 1, fetchedAt: fetched.toISOString(), expiresAt: new Date(+fetched + 864e5).toISOString(),
    artisans: [{ characterId: 123, name: '測試 鐵匠', professions: [] }] };
  const env = { PROFILE_RATE: { limit: async () => ({ success: true }) }, BLIZZARD_CLIENT_ID: 'demo',
    BLIZZARD_CLIENT_SECRET: 'demo', SNAPSHOTS: { get: async key => key === 'artisans' ? roster : excluded } };
  const request = new Request(`${endpoint}/characters/${encodeURIComponent('測試-鐵匠')}.json`);
  const first = await reader.fetch(request, env);
  assert.equal(first.status, 200);
  const data = await first.json();
  assert.equal(Object.hasOwn(data, 'id'), false);
  assert.deepEqual(data.talents[0].talents, [{ name: '強化英勇打擊', rank: 3 }]);
  const previous = upstream;
  excluded = [123];
  assert.equal((await reader.fetch(request, env)).status, 404);
  assert.equal(upstream, previous);
  const directory = await reader.fetch(new Request(`${endpoint}/artisans.json`), env);
  assert.deepEqual((await directory.json()).artisans, []);
});

test('備戰清單驗證分享資料，合併全團與職責採購', () => {
  const common = [{ id: 12359, name: '瑟銀錠', quantity: 2 }];
  const plan = verifyPlan({ schema: 1, title: '備戰', common, tank: [{ ...common[0], quantity: 3 }], healer: [], damage: [] });
  const merged = mergeItems([...plan.common, ...plan.tank]);
  assert.deepEqual(merged, [{ ...common[0], quantity: 5 }]);
  assert.equal(shoppingText('團本備戰', merged), '團本備戰^"瑟銀錠"');
  assert.throws(() => verifyPlan({ ...plan, common: [{ ...common[0], quantity: -1 }] }));
});
