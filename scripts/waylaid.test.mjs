import assert from 'node:assert/strict';
import test from 'node:test';

import { crates, names, payouts } from '../waylaid/data.mjs';
import { curve, overview, plan, take } from '../waylaid/optimizer.mjs';

const kindA = { id: 1, favor: 10, refund: 500, bundles: [[11, 20], [12, 10]] };
const kindB = { id: 2, favor: 30, refund: 1500, bundles: [[21, 10]] };
const depth = {
  1: [[50, 3], [80, 10]],
  11: [[7, 30], [9, 100]],
  12: [[30, 5], [40, 50]],
  2: [[20, 2], [100, 5]],
  21: [[500, 8], [700, 30]],
};

test('take walks the ladder and stops when it runs dry', () => {
  assert.deepEqual(take(depth[11], 0, 40), { cost: 30 * 7 + 10 * 9, top: 9 });
  assert.deepEqual(take(depth[11], 25, 10), { cost: 5 * 7 + 5 * 9, top: 9 });
  assert.equal(take(depth[12], 0, 56), null);
  assert.equal(take(undefined, 0, 1), null);
});

test('curve takes the cheapest next bundle for each crate', () => {
  const steps = curve(kindA, depth, 3);
  // Crate 1: 50 + min(20×7=140, 5×30+5×40=350) → bundle 0.
  assert.equal(steps[0].bundle, 0);
  assert.equal(steps[0].spend, 190);
  assert.equal(steps[0].total, 0);
  // Crate 2: 50 + min(10×7+10×9=160, 350) = 210 more.
  assert.equal(steps[1].spend, 400);
});

function brute(kinds, need) {
  const curves = kinds.map(kind => curve(kind, depth, Math.ceil(need / kind.favor)));
  let best = Infinity;
  const walk = (index, favor, cost) => {
    if (index === kinds.length) {
      if (favor >= need) best = Math.min(best, cost);
      return;
    }
    walk(index + 1, favor, cost);
    curves[index].forEach((step, k) => walk(index + 1, favor + (k + 1) * kinds[index].favor, cost + step.total));
  };
  walk(0, 0, 0);
  return best;
}

test('plan matches brute force over every goal', () => {
  for (let need = 10; need <= 200; need += 10) {
    const result = plan([kindA, kindB], depth, need);
    assert.ok(result.favor >= need, `need ${need}`);
    assert.equal(result.cost, brute([kindA, kindB], need), `need ${need}`);
    assert.equal(result.spend - result.refund, result.cost);
  }
});

test('plan reports a shortfall when listings run out', () => {
  const result = plan([kindB], depth, 1000);
  assert.equal(result.short, true);
  assert.equal(result.favor, 3 * 30);
});

test('overview puts unsold crates last', () => {
  const rows = overview([{ id: 3, favor: 5, refund: 0, bundles: [[11, 1]] }, kindA], depth);
  assert.equal(rows[0].kind, kindA);
  assert.equal(rows[1].perFavor, undefined);
});

test('crate data names every crate and material', () => {
  assert.equal(crates.length, 30);
  for (const [id, tier, quality, level, bundles] of crates) {
    assert.ok(payouts[tier]?.[quality - 1], `${id} payout`);
    assert.ok([10, 20, 35].includes(level));
    for (const item of [id, ...bundles.map(([bundleItem]) => bundleItem)]) assert.ok(names.get(item), `${item} name`);
  }
});
