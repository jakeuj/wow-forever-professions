function priceBook(tiers) {
  let units = 0;
  let spent = 0;
  return (tiers || []).map(([price, count]) => {
    units += count;
    spent += price * count;
    return { price, units, spent };
  });
}

function prefix(book, count) {
  if (!count) return 0;
  let low = 0;
  let high = book.length - 1;
  while (low < high) {
    const middle = (low + high) >>> 1;
    if (book[middle].units < count) low = middle + 1;
    else high = middle;
  }
  const tier = book[low];
  return tier.spent - (tier.units - count) * tier.price;
}

function quote(book, needed, offer, unknown) {
  const available = book.at(-1)?.units || 0;
  const bought = Math.min(needed, available);
  if (!offer || needed === 0) {
    return { bought, vendorUnits: 0, surplus: 0, missing: needed - bought, spent: Math.ceil(prefix(book, bought)), unknown };
  }
  const [price, pack, vendor] = offer;
  const cheap = book.findLast(tier => tier.price * pack < price)?.units || 0;
  const min = Math.max(0, Math.ceil((needed - available) / pack));
  const max = Math.ceil(needed / pack);
  const optimum = Math.max(min, (needed - cheap) / pack);
  let best;
  // Auction total cost is convex. Rounding at the pack boundary gives the best whole-pack mix.
  for (const packs of new Set([min, Math.floor(optimum), Math.ceil(optimum), max])) {
    const vendorUnits = packs * pack;
    const auction = Math.max(0, needed - vendorUnits);
    const spent = Math.ceil(prefix(book, auction) + packs * price);
    if (!best || spent < best.spent || (spent === best.spent && auction < best.bought)) {
      best = { bought: auction, vendorUnits, vendor, surplus: Math.max(0, vendorUnits - needed), missing: 0, spent, unknown: false };
    }
  }
  return best;
}

export function procurement(catalog, snapshot) {
  const books = new Map();
  const prices = new Map();
  return (id, needed, formula = false) => {
    if (!books.has(id)) books.set(id, priceBook(snapshot?.depth[id]));
    const key = `${id}:${needed}:${Number(formula)}`;
    if (!prices.has(key)) {
      prices.set(key, quote(books.get(id), needed, (formula ? catalog.formulas : catalog.supplies)?.[id],
        needed > 0 && (!snapshot || snapshot.depth[id] === null)));
    }
    return prices.get(key);
  };
}

export function reserve(state, id, count, context, formula = false) {
  const previous = state.items.get(id) || { needed: 0, owned: 0, crafted: 0, spent: 0, missing: 0 };
  const owned = Math.min(state.stock.get(id) || 0, count);
  const crafted = Math.min(state.crafted.get(id) || 0, count - owned);
  if (owned) state.stock.set(id, state.stock.get(id) - owned);
  if (crafted) state.crafted.set(id, state.crafted.get(id) - crafted);
  const needed = previous.needed + count - owned - crafted;
  const asFormula = formula || previous.formula;
  const next = context.quote(id, needed, asFormula);
  state.total += next.spent - previous.spent;
  state.missing += next.missing - previous.missing;
  state.items.set(id, { id, ...next, needed, formula: asFormula, owned: previous.owned + owned, crafted: previous.crafted + crafted });
}
