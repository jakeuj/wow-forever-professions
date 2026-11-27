import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import test from 'node:test';
import { advanceRank, canCraft, finishBatch, initialState, prepareBatch } from '../crafting-leveling/auto-actions.mjs';
import { procurement, reserve } from '../crafting-leveling/auto-cost.mjs';
import { initialRisk, nextCraft, probabilityAtLeast, requireSkill } from '../crafting-leveling/auto-risk.mjs';
import { DEFAULT_CONFIDENCE, searchRoute } from '../crafting-leveling/auto-search.mjs';
import { armoryLevelingPlan, levelingPlanKey, readLevelingPlan, writeLevelingPlan } from '../crafting-leveling/state.mjs';

const read = name => JSON.parse(readFileSync(new URL(`../crafting-leveling/${name}.json`, import.meta.url)));
const catalog = read('auto-recipes');
const fixed = read('routes');
const recipeMap = read('battle-net-recipe-map');
const ranks = [{ cap: 75, skill: 1, level: 5, fee: 10 }, { cap: 150, skill: 50, level: 10, fee: 500 },
  { cap: 225, skill: 125, level: 20, fee: 5000 }, { cap: 300, skill: 200, level: 35, fee: 50000 }];
const fixture = { items: { 1: '甲材料', 2: '乙材料', 3: '半成品', 4: '圖樣' }, rods: [], tools: {}, supplies: {}, formulas: {} };
const input = { start: 187, target: 225, cap: 225, level: 60, inventory: [], known: [] };

test('官方工程產量區間與求解器使用的估算分開保存', () => {
  const engineering = catalog.professions.engineering.recipes;
  assert.deepEqual(Object.entries(engineering).filter(([, row]) => row.output_range)
    .map(([spell, row]) => [Number(spell), row.output_range, row.output]), [
    [3931, [1, 4], 2], [3937, [1, 5], 3], [3941, [1, 4], 2], [3946, [1, 7], 3],
    [3950, [1, 5], 3], [3962, [1, 5], 3], [8339, [1, 4], 2],
  ]);
  const state = initialState(input);
  const result = finishBatch(state, { ...engineering[3962], spell:3962 }, 2, 187);
  assert.equal(result.crafted.get(4390), 6);
  assert.ok(catalog.professions.tailoring.recipes[12091].reagents.some(([id, count]) => id === 2324 && count === 1));
  const potion = catalog.professions.alchemy.recipes[1251750];
  assert.equal(potion.product, 250952);
  assert.equal(potion.output, 1);
  assert.equal(potion.battle_net_recipe_id, undefined);
});

function recipe(spell, item, options = {}) {
  return { spell, name: `配方 ${spell}`, learn: 1, yellow: 300, green: 300, grey: 300,
    grant: 1, offers: [], tools: [], reagents: [[item, 1]], product: 0, output: 0, ...options };
}

test('軍械庫以已核對的法術 ID 匯入，求解器把玉蛇刀列為已學', () => {
  assert.equal(recipeMap.catalogRelease, catalog.release);
  for (const [profession, mapping] of Object.entries(recipeMap.professions)) {
    const spells = Object.values(mapping);
    assert.equal(new Set(spells).size, spells.length);
    assert.ok(spells.every(spell => Object.hasOwn(catalog.professions[profession].recipes, spell)));
  }
  assert.equal(recipeMap.professions.enchanting[4289], 7418);
  const skill = { skill: 187, maxSkill: 225, recipes: [[1986], [1986], [999999]] };
  const plan = armoryLevelingPlan(undefined, '測試 鐵匠', skill, recipeMap.professions.blacksmithing);
  assert.deepEqual([plan.start, plan.cap, plan.target, plan.known], [187, '225', 225, [3493]]);
  assert.deepEqual(plan.armoryImport, { matched: 1, skipped: 1 });
  const blade = { ...catalog.professions.blacksmithing.recipes[3493], spell: 3493, grant: 0, offers: [] };
  assert.equal(canCraft({}, initialState(input), blade), false);
  assert.equal(canCraft({}, initialState({ ...input, known: plan.known }), blade), true);
});

test('重新匯入只更新官方欄位，不將同名或其他專業的計畫混在一起', () => {
  const legacy = { start: 175, cap: '225', known: [2660], target: 300, inventory: '銅錠：3', level: 40,
    confidence: '.95', done: ['first'] };
  const a = '測試-鐵匠';
  const b = '另位-鐵匠';
  const characters = { [a]: { name: '鐵匠' }, [b]: { name: '鐵匠' } };
  const plans = { 'blacksmithing:鐵匠': legacy };
  assert.equal(readLevelingPlan(plans, characters, 'blacksmithing', a), undefined);
  assert.equal(readLevelingPlan(plans, { [a]: characters[a] }, 'blacksmithing', a), legacy);
  assert.equal(readLevelingPlan(plans, {}, 'blacksmithing', '', '鐵匠'), legacy);

  const makePlan = (previous, recipes, skill = 187, maxSkill = 225) =>
    armoryLevelingPlan(previous, '鐵匠', { skill, maxSkill, recipes }, recipeMap.professions.blacksmithing);
  const aPlan = makePlan(legacy, [[1986]]);
  assert.deepEqual(aPlan, { ...legacy, start: 187, known: [3493], characterName: '鐵匠',
    armoryImport: { matched: 1, skipped: 0 } });
  plans[levelingPlanKey('blacksmithing', a)] = aPlan;
  plans[levelingPlanKey('blacksmithing', b)] = makePlan(undefined, [], 150);
  plans[levelingPlanKey('alchemy', a)] = { start: 75, known: [] };
  assert.equal(readLevelingPlan(plans, characters, 'blacksmithing', a), aPlan);
  assert.deepEqual(readLevelingPlan(plans, characters, 'blacksmithing', b).known, []);
  assert.equal(readLevelingPlan(plans, characters, 'alchemy', a).start, 75);
  assert.throws(() => makePlan(aPlan, undefined), /專業資料不完整/u);
  assert.throws(() => makePlan(aPlan, [], 187, 200), /技能上限/u);
  assert.throws(() => makePlan(aPlan, [], 300, 300), /已達練等上限/u);
  assert.throws(() => armoryLevelingPlan(aPlan, '鐵匠', { skill: 187, maxSkill: 225, recipes: [] }, null), /配方對照/u);
});

test('保存單一角色專業能保留其他計畫，寫入失敗會回報', t => {
  const storage = new Map();
  const descriptor = Object.getOwnPropertyDescriptor(globalThis, 'localStorage');
  const local = { getItem: key => storage.get(key) ?? null, setItem: (key, value) => storage.set(key, value) };
  Object.defineProperty(globalThis, 'localStorage', { configurable: true, value: local });
  t.after(() => {
    if (descriptor) Object.defineProperty(globalThis, 'localStorage', descriptor);
    else delete globalThis.localStorage;
  });
  const a = levelingPlanKey('blacksmithing', '測試-鐵匠');
  const b = levelingPlanKey('alchemy', '測試-鐵匠');
  writeLevelingPlan(a, { start: 187, known: [3493] });
  writeLevelingPlan(b, { start: 70, known: [] });
  const saved = [...storage];
  assert.equal(Object.keys(JSON.parse(saved[0][1])).length, 2);
  t.mock.method(local, 'setItem', () => { throw new Error('Storage disabled'); });
  assert.throws(() => writeLevelingPlan(a, { start: 188 }), /Storage disabled/u);
  assert.deepEqual([...storage], saved);
});

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

test('鍛造 225 → 300 依官方設計圖門檻 230 學黑檀剃刃，在 255 前就採用', () => {
  const blacksmithing = catalog.professions.blacksmithing;
  const shiv = blacksmithing.recipes[10013];
  assert.deepEqual(shiv.offers.map(offer => [offer.item, offer.skill]), [[8030, 230]]);
  const cheap = new Set([shiv.formula, ...shiv.tools, ...shiv.reagents.map(([id]) => id)]);
  const depth = { depth: Object.fromEntries(Object.keys(catalog.items)
    .map(id => [id, [[cheap.has(Number(id)) ? 1 : 10000, 50000]]])) };
  const result = searchRoute(catalog, blacksmithing, { ...input, start: 225, cap: 300, target: 300 }, depth);
  assert.equal(result.status, 'qualified');
  const [learned, firstCraft] = result.plan.steps.filter(step => step.spell === 10013);
  assert.equal(learned.kind, 'learn');
  assert.ok(learned.from < 255 && firstCraft.from < 255, `${learned.from} → ${firstCraft.from}`);
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
