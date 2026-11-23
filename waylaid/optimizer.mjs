// The cheapest Waylaid Crates for a Merchant's Favor goal, after Waylaid Auction Helper's Optimizer.lua.
// A ladder is one item's listings, cheapest first: [[copper per unit, units], ...].
// No two crates share a material, so each kind is costed on its own: the k-th crate takes the next
// cheapest crate plus the cheapest next bundle. A knapsack over favor then picks how many of each.

// Cost and dearest unit price of `units` after the first `skip` on a ladder; null when it runs dry.
export function take(ladder, skip, units) {
  if (units <= 0) return { cost: 0, top: 0 };
  let cost = 0;
  let top = 0;
  for (const [price, count] of ladder || []) {
    if (skip >= count) {
      skip -= count;
      continue;
    }
    const used = Math.min(count - skip, units);
    skip = 0;
    cost += used * price;
    top = Math.max(top, price);
    units -= used;
    if (!units) return { cost, top };
  }
  return null;
}

// steps[k - 1] for k crates: spend, total (spend less refunds, not below 0) and the k-th crate's bundle.
export function curve(kind, depth, max) {
  const steps = [];
  const used = [];
  let spend = 0;
  for (let k = 1; k <= max; k += 1) {
    const crate = take(depth[kind.id], k - 1, 1);
    if (!crate) break;
    let best = -1;
    let bestCost = Infinity;
    kind.bundles.forEach(([item, units], index) => {
      const bundle = take(depth[item], (used[index] || 0) * units, units);
      if (bundle && bundle.cost < bestCost) [best, bestCost] = [index, bundle.cost];
    });
    if (best < 0) break;
    used[best] = (used[best] || 0) + 1;
    spend += crate.cost + bestCost;
    steps.push({ spend, total: Math.max(0, spend - k * kind.refund), bundle: best });
  }
  return steps;
}

function gcd(a, b) {
  while (b) [a, b] = [b, a % b];
  return a;
}

// Shopping lines for `count` crates of a kind, taking bundles as its curve did.
function lines(kind, steps, count, depth) {
  const uses = new Map();
  for (const step of steps.slice(0, count)) uses.set(step.bundle, (uses.get(step.bundle) || 0) + 1);
  const line = (item, units, extra) => ({ item, units, ...take(depth[item], 0, units), ...extra });
  return [
    line(kind.id, count, { crate: true }),
    ...kind.bundles.flatMap(([item, units], index) => uses.has(index)
      ? [line(item, uses.get(index) * units, { bundles: uses.get(index), per: units })] : []),
  ];
}

// { need, favor, cost, spend, refund, short, picks: [{ kind, count, favor, cost, spend, refund, lines }] }
export function plan(kinds, depth, need) {
  const result = { need, favor: 0, cost: 0, spend: 0, refund: 0, picks: [], short: false };
  if (need <= 0) return result;
  const options = [];
  let unit = 0;
  for (const kind of kinds) {
    const steps = curve(kind, depth, Math.ceil(need / kind.favor));
    if (!steps.length) continue;
    options.push({ kind, steps });
    unit = gcd(kind.favor, unit);
  }
  if (!options.length) return { ...result, short: true };
  const size = Math.ceil(need / unit);
  let best = new Array(size + 1).fill(Infinity);
  best[0] = 0;
  const choices = [];
  for (const { kind, steps } of options) {
    const weight = kind.favor / unit;
    const next = best.slice();
    const pick = new Map();
    for (let x = 0; x <= size; x += 1) {
      if (best[x] === Infinity) continue;
      steps.forEach((step, index) => {
        const y = Math.min(size, x + (index + 1) * weight);
        const cost = best[x] + step.total;
        if (cost < next[y]) {
          next[y] = cost;
          pick.set(y, [x, index + 1]);
        }
      });
    }
    best = next;
    choices.push(pick);
  }
  let y = size;
  while (y > 0 && best[y] === Infinity) y -= 1;
  const counts = [];
  for (let t = options.length - 1; t >= 0; t -= 1) {
    const step = choices[t].get(y);
    if (step) [y, counts[t]] = step;
  }
  options.forEach(({ kind, steps }, t) => {
    const count = counts[t];
    if (!count) return;
    const step = steps[count - 1];
    const pick = { kind, count, favor: count * kind.favor, cost: step.total, spend: step.spend,
      refund: step.spend - step.total, lines: lines(kind, steps, count, depth) };
    result.picks.push(pick);
    result.favor += pick.favor;
    result.cost += pick.cost;
    result.spend += pick.spend;
    result.refund += pick.refund;
  });
  result.picks.sort((a, b) => a.cost * b.favor - b.cost * a.favor);
  result.short = result.favor < need;
  return result;
}

// One crate of each kind with its cheapest bundle, cheapest per favor first; unsold kinds last.
export function overview(kinds, depth) {
  const rows = kinds.map(kind => {
    const stock = (depth[kind.id] || []).reduce((sum, [, count]) => sum + count, 0);
    const step = curve(kind, depth, 1)[0];
    if (!step) return { kind, stock };
    const crate = take(depth[kind.id], 0, 1).cost;
    return { kind, stock, crate, bundle: kind.bundles[step.bundle], bundleCost: step.spend - crate,
      spend: step.spend, perFavor: step.total / kind.favor };
  });
  return rows.sort((a, b) => (a.perFavor === undefined) - (b.perFavor === undefined)
    || (a.perFavor ?? 0) - (b.perFavor ?? 0) || a.kind.favor - b.kind.favor);
}
