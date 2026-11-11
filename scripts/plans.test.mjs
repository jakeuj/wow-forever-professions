import test from 'node:test';
import assert from 'node:assert/strict';
import { professions, crafting, getRows, summarize, normalizeProgress, countPoints } from '../data.mjs';

for (const plan of ['crafting', 'gathering', 'balanced', 'paladin']) {
  test(`${plan}: 五種職業、九項專業與十八點長期里程碑`, () => {
    const rows = getRows(plan, 'final');
    assert.equal(rows.length, 5);
    assert.equal(new Set(rows.map(row => row.classId)).size, 5);
    assert.ok(rows.every(row => row.profs.length >= 1 && row.profs.length <= 2 && new Set(row.profs).size === row.profs.length));
    assert.deepEqual([...summarize(rows).ids].sort(), professions.map(p => p.id).sort());
    assert.equal(summarize(rows).points, 18);
  });
}
test('集中雙製造保留主號雙採集，六項製造各一次集中於三隻小號', () => {
  const rows = getRows('crafting');
  const craftRows = rows.filter(row => row.profs.some(id => crafting.some(p => p.id === id)));
  assert.deepEqual(rows[0].profs, ['herbalism', 'skinning']);
  assert.equal(craftRows.length, 3);
  assert.ok(craftRows.every(row => row.profs.length === 2 && row.profs.every(id => crafting.some(p => p.id === id))));
  assert.deepEqual(craftRows.flatMap(row => row.profs).sort(), crafting.map(p => p.id).sort());
  assert.equal(summarize(rows).craftCharacters, 3);
  assert.deepEqual(rows.find(row => row.classId === 'rogue').profs, ['mining']);
  assert.equal(rows.find(row => row.classId === 'rogue').flexibleSlot, true);
  assert.deepEqual(getRows('crafting', 'start'), getRows('crafting', 'final'));
});
test('雙採集開局缺煉金，上限十五點；轉職只替換德魯伊剝皮', () => {
  const early = getRows('gathering', 'start');
  const late = getRows('gathering', 'final');
  assert.deepEqual(early[0].profs, ['skinning', 'herbalism']);
  assert.equal(summarize(early).covered, 8);
  assert.equal(summarize(early).points, 15);
  assert.equal(summarize(early).ids.has('alchemy'), false);
  assert.deepEqual(late[0].profs, ['herbalism', 'alchemy']);
  assert.deepEqual(early.slice(1), late.slice(1));
});
test('聖騎士保留既有採礦／鍛造，法師承接裁縫／附魔', () => {
  const rows = getRows('paladin');
  assert.equal(rows[0].classId, 'paladin');
  assert.deepEqual(rows[0].profs, ['mining', 'blacksmithing']);
  assert.deepEqual(rows.find(r => r.classId === 'mage').profs, ['tailoring', 'enchanting']);
});
test('進度按帳號專業計一次，每一階段累計六、十二、十八點', () => {
  for (const stage of [0, 1, 2, 3]) {
    assert.equal(countPoints(Object.fromEntries(crafting.map(p => [p.id, stage]))), stage * 6);
  }
  assert.equal(countPoints({ tailoring: 3, enchanting: 2 }), 5);
});
test('破損或無效儲存資料不會虛增傳承點數', () => {
  for (const value of [null, [], 'invalid', { alchemy: -1, tailoring: 999, enchanting: '3', engineering: 1.5, mining: 3 }]) {
    assert.equal(countPoints(value), 0);
    assert.equal(Object.keys(normalizeProgress(value)).length, 6);
  }
  assert.equal(countPoints({ alchemy: 3, unknown: 100 }), 3);
});
