import assert from 'node:assert/strict';
import { test } from 'node:test';
import { change, marketItems, priceAt, sortMarketItems } from '../market/model.mjs';

const scan = {
  latestDay: '2026-11-20',
  snapshotAt: '2026-11-20T12:00:00+08:00',
  fields: ['id', 'name', 'day', 'count', 'price', 'prev', 'prevDay'],
  items: [
    [1, '銅礦石', '2026-11-20', 20, 100, 125, '2026-11-19'],
    [2, '錫礦石', '2026-11-20', 4, 130, 120, '2026-11-19'],
    [3, '鐵礦石', '2026-11-19', 3, 150, 145, '2026-11-18'],
  ],
};
const hour = Date.parse('2026-11-20T13:00:00+08:00') / 3600e3;
const official = {
  hours: [hour - 30, hour - 1, hour],
  updatedAt: '2026-11-20T13:00:00+08:00',
  items: { 1: [10, [[hour - 30, 160], [hour - 1, 120]]], 3: [0, [[hour - 30, 170], [hour, null]]] },
};

test('較新的官方快照提供現價與 24 小時比較，缺貨保留最近看到的價格', () => {
  const before = structuredClone({ scan, official });
  const { items: [copper, tin, iron], apiHour, apiUpdatedAt, apiNewer } = marketItems(scan, official);
  assert.deepEqual([apiHour, apiUpdatedAt, apiNewer], [hour, official.updatedAt, true]);
  assert.deepEqual([copper.now, copper.base, copper.units, copper.listed, change(copper)], [120, 160, 10, true, -0.25]);
  assert.deepEqual([tin.now, tin.units, tin.listed, tin.when], [130, null, false, '11/20 掃描看到，官方已沒貨']);
  assert.deepEqual([iron.now, iron.units, iron.listed, iron.when, change(iron)], [170, null, false, '11/20 13 時起沒貨', null]);
  assert.deepEqual({ scan, official }, before);
});

test('同時或三小時內較舊的官方快照只提供走勢，逾期、缺失或無小時資料時回退掃描', () => {
  for (const updatedAt of [scan.snapshotAt, '2026-11-20T09:00:00+08:00']) {
    const result = marketItems(scan, { ...official, updatedAt });
    assert.deepEqual([result.apiUpdatedAt, result.apiNewer], [updatedAt, false]);
    assert.deepEqual([result.items[0].now, result.items[0].units, result.items[0].when], [100, 20, '11/20 掃描']);
    assert.deepEqual(result.items[0].series, official.items[1][1]);
    assert.equal(result.items[2].listed, false);
  }
  for (const invalid of [null, { ...official, updatedAt: '2026-11-20T08:59:59+08:00' }, { ...official, hours: [] }]) {
    const result = marketItems(scan, invalid);
    assert.deepEqual([result.apiHour, result.apiUpdatedAt, result.apiNewer], [null, null, false]);
    assert.equal(result.items[0].now, 100);
    assert.equal(result.items[0].series, undefined);
  }
});

test('走勢保留缺貨時段，排序保留價格缺值與品質的既有順序', () => {
  const series = [[10, 150], [12, null], [14, 100]];
  assert.deepEqual([9, 11, 13, 15].map(hour => priceAt(series, hour)), [undefined, 150, null, 100]);
  const items = [
    { id: 1, name: 'B', quality: 4, now: null, base: 9, units: null },
    { id: 2, name: 'A', quality: 3, now: 5, base: 10, units: 2 },
    { id: 3, name: 'C', quality: 4, now: 15, base: 10, units: 3 },
  ];
  const order = sort => sortMarketItems(items, sort).map(item => item.id);
  assert.deepEqual(order('quality'), [3, 1, 2]);
  assert.deepEqual(order('price-asc'), [2, 3, 1]);
  assert.deepEqual(order('price-desc'), [3, 2, 1]);
  assert.deepEqual(order('drop'), [2, 3, 1]);
  assert.deepEqual(order('count'), [3, 2, 1]);
  assert.deepEqual(order('name'), [2, 1, 3]);
  assert.deepEqual(items.map(item => item.id), [1, 2, 3]);
});
