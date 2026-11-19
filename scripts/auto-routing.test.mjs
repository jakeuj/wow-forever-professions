import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { advanceRank, finishBatch, initialState, prepareBatch } from '../crafting-leveling/auto-actions.mjs';
import { procurement, reserve } from '../crafting-leveling/auto-cost.mjs';
import { initialRisk, nextCraft, probabilityAtLeast, requireSkill } from '../crafting-leveling/auto-risk.mjs';
import { DEFAULT_CONFIDENCE, searchRoute } from '../crafting-leveling/auto-search.mjs';

const read = name => JSON.parse(readFileSync(new URL(`../crafting-leveling/${name}.json`, import.meta.url)));
const catalog = read('auto-recipes');
const fixed = read('routes');
const ranks = [{ cap: 75, skill: 1, level: 5, fee: 10 }, { cap: 150, skill: 50, level: 10, fee: 500 },
  { cap: 225, skill: 125, level: 20, fee: 5000 }, { cap: 300, skill: 200, level: 35, fee: 50000 }];
const fixture = { items: { 1: '甲材料', 2: '乙材料', 3: '半成品', 4: '圖樣' }, rods: [], tools: {}, supplies: {}, formulas: {} };
const input = { start: 187, target: 225, cap: 225, level: 60, inventory: [], known: [] };
function recipe(spell, item, options = {}) {
  return { spell, name: `配方 ${spell}`, learn: 1, yellow: 300, green: 300, grey: 300,
    grant: 1, offers: [], tools: [], reagents: [[item, 1]], product: 0, output: 0, ...options };
}

test('連續補貨跨價階，同一 NPC 整包不重複付款', () => {
  const shop = { ...fixture, supplies: { 2: [35, 5, '商人'] } };
  const quote = procurement(shop, { depth: { 1: [[10, 8], [12, 30]], 2: [[10, 15]] } });
  const state = initialState({ ...input, inventory: [[1, 2]] });
  reserve(state, 1, 7, { quote });
  reserve(state, 1, 4, { quote });
  assert.equal(state.items.get(1).owned, 2);
  assert.equal(state.items.get(1).bought, 9);
  assert.equal(state.total, 92);
  reserve(state, 2, 4, { quote });
  assert.equal(state.items.get(2).surplus, 1);
  assert.equal(state.items.get(2).spent, 35);
  reserve(state, 2, 1, { quote });
  assert.equal(state.items.get(2).spent, 35);
  assert.equal(state.items.get(2).surplus, 0);
});

test('圖樣只學一次，中間材料只自製一次，升階收取一次學費', () => {
  const component = recipe(11, 2, { product: 3, output: 3 });
  const craft = recipe(12, 3, { grant: 0, offers: [{ item: 4, fee: 0, level: 0, skill: 1 }] });
  const context = {
    catalog: fixture, recipes: { 11: component, 12: craft }, level: 60, ranks,
    producers: new Map([[3, component]]), quote: procurement(fixture, { depth: { 2: [[10, 50]], 4: [[20, 1]] } }),
  };
  const state = initialState({ ...input, start: 75, target: 80, cap: 75 });
  const trained = advanceRank(context, state);
  assert.equal(trained.cap, 150);
  assert.equal(trained.training, 500);
  const once = finishBatch(prepareBatch(context, trained, craft, 1), craft, 1, 77);
  const twice = finishBatch(prepareBatch(context, once, craft, 1), craft, 1, 78);
  assert.equal(twice.steps.filter(step => step.kind === 'learn').length, 1);
  assert.equal(twice.steps.filter(step => step.spell === 11).length, 1);
  assert.equal(twice.items.get(4).bought, 1);
  assert.equal(twice.items.get(3).crafted, 2);
  assert.equal(twice.total, 530);
});

test('半機率製作兩次為 75%，門檻排除未達的機率而不重設分母', () => {
  const mixed = recipe(12, 1, { yellow: 10, green: 20, grey: 30 });
  const initial = initialRisk(20, 22);
  const once = nextCraft(initial, mixed, 75);
  const twice = nextCraft(once, mixed, 75);
  assert.equal(probabilityAtLeast(twice, 21), .75);
  const accepted = requireSkill(once, 21);
  assert.equal(probabilityAtLeast(nextCraft(accepted, recipe(13, 1, { learn: 21 }), 75), 22), .5);
  assert.equal(probabilityAtLeast(nextCraft(initialRisk(30, 31), mixed, 75), 31), 0);
  assert.equal(probabilityAtLeast(nextCraft(initialRisk(75, 76), recipe(14, 1), 75), 76), 0);
});

test('搜尋依即時價階、缺貨與自備庫存更換鍛造 187 → 225 的配方', () => {
  const profession = { ranks, recipes: { 11: recipe(11, 1), 22: recipe(22, 2) } };
  const complete = searchRoute(fixture, profession, input, { depth: { 1: [[1, 38]], 2: [[4, 50]] } });
  const short = searchRoute(fixture, profession, input, { depth: { 1: [[1, 8]], 2: [[4, 50]] } });
  const owned = searchRoute(fixture, profession, { ...input, inventory: [[2, 38]] }, { depth: { 1: [[1, 38]], 2: [[4, 50]] } });
  for (const plan of [complete, short, owned]) assert.equal(plan.status, 'qualified');
  assert.equal(complete.plan.total, 38);
  assert.ok(short.plan.steps.some(step => step.spell === 22));
  assert.equal(short.plan.missing, 0);
  assert.ok(short.plan.items.find(item => item.id === 1)?.bought <= 8 || !short.plan.items.some(item => item.id === 1));
  assert.equal(owned.plan.total, 0);
  assert.equal(owned.plan.items.find(item => item.id === 2).owned, 38);
});

test('預設 90%，95% 需要多一次，只有三份材料時清楚回報 87.5%', () => {
  const mixed = { ranks, recipes: { 11: recipe(11, 1, { yellow: 10, green: 20, grey: 30 }) } };
  const settings = { ...input, start: 20, target: 21, cap: 75 };
  const normal = searchRoute(fixture, mixed, settings, { depth: { 1: [[10, 5]] } });
  const higher = searchRoute(fixture, mixed, { ...settings, confidence: .95 }, { depth: { 1: [[10, 5]] } });
  const short = searchRoute(fixture, mixed, settings, { depth: { 1: [[10, 3]] } });
  assert.equal(DEFAULT_CONFIDENCE, .9);
  assert.deepEqual([normal.status, normal.plan.total, normal.probability], ['qualified', 40, .9375]);
  assert.deepEqual([higher.status, higher.plan.total, higher.probability], ['qualified', 50, .96875]);
  assert.deepEqual([short.status, short.plan.total, short.probability], ['under-threshold', 30, .875]);
});

test('無價階與已知缺貨分開，搜尋預算耗盡會回報限制', () => {
  const profession = { ranks, recipes: { 11: recipe(11, 1) } };
  const settings = { ...input, start: 10, target: 11, cap: 75 };
  const stale = searchRoute(fixture, profession, settings, null);
  const soldOut = searchRoute(fixture, profession, settings, { depth: {} });
  assert.equal(stale.status, 'partial');
  assert.equal(stale.plan.items[0].unknown, true);
  assert.equal(stale.plan.items[0].missing, 1);
  assert.equal(soldOut.plan.items[0].unknown, false);
  assert.equal(searchRoute(fixture, profession, settings, null, { budget: 0 }).bounded, true);
});

test('六項製造的發布包資料都能從技能 1 搜尋到 300', () => {
  const depth = { depth: Object.fromEntries(Object.keys(catalog.items).map(id => [id, [[100, 50000]]])) };
  assert.deepEqual(Object.keys(catalog.professions).sort(), Object.keys(fixed.professions).sort());
  for (const [slug, profession] of Object.entries(catalog.professions)) {
    const options = { seeds: fixed.professions[slug].routes, components: fixed.professions[slug].components };
    const result = searchRoute(catalog, profession, { ...input, start: 1, cap: 75, target: 300 }, depth, options);
    assert.equal(result.status, 'qualified', `${slug} ${result.reason}`);
    assert.ok(result.probability >= .9);
    assert.equal(result.plan.missing, 0);
  }
});
