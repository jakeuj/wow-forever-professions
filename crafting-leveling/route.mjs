import { buyFromDepth } from '../market/quotes.mjs';

const add = (items, id, count) => items.set(id, (items.get(id) || 0) + count);

function probability(recipe, skill) {
  if (skill < recipe.yellow) return 1;
  if (skill < recipe.green) return 1 - .5 * (skill - recipe.yellow) / (recipe.green - recipe.yellow);
  return Math.max(.05, .5 - .45 * (skill - recipe.green) / Math.max(1, recipe.grey - recipe.green));
}

function consumption(items, id, needed) {
  const consumed = Math.min(needed, items.get(id) || 0);
  if (consumed) add(items, id, -consumed);
  return consumed;
}

function procure(snapshot, id, required, offer) {
  const quote = buyFromDepth(snapshot, id, required);
  if (!offer || !quote.missing) return { ...quote, vendorUnits: 0 };
  const [price, pack, vendor] = offer;
  const packs = Math.ceil(quote.missing / pack);
  return { ...quote, vendor, vendorUnits: pack * packs, spent: quote.spent + price * packs,
    missing: 0, unknown: false };
}

export function planRoute(catalog, profession, route, input, snapshot) {
  const { start, target } = input;
  const stock = new Map(input.inventory);
  const made = new Map();
  const usedStock = new Map();
  const usedMade = new Map();
  const demand = new Map();
  const formulas = new Set();
  const learned = new Set(input.known);
  const requirements = new Set();
  const requirementsPaid = new Set();
  const missingFees = new Set();
  const steps = [];
  const recipes = profession.recipes;
  const components = new Map(profession.components.map(spell => [recipes[spell].product, spell]));
  const thresholds = [0, 75, 150, 225];
  let training = profession.rankFees.reduce((cost, fee, i) =>
    cost + (i === 0 ? (start === 1 ? fee : 0) : (start <= thresholds[i] && thresholds[i] < target ? fee : 0)), 0);
  let uncertain = 0;

  function take(id, needed) {
    const owned = consumption(stock, id, needed);
    const crafted = consumption(made, id, needed - owned);
    if (owned) add(usedStock, id, owned);
    if (crafted) add(usedMade, id, crafted);
    return needed - owned - crafted;
  }

  function craft(spell, count, level, end, visiting = new Set()) {
    const recipe = recipes[spell];
    if (!recipe || level < recipe.learn || visiting.has(spell) || end > recipe.grey && end > level) {
      throw new Error('這條路線的配方或前置條件有缺漏。');
    }
    const next = new Set(visiting).add(spell);
    for (const id of recipe.tools) {
      const index = catalog.rods.indexOf(id);
      const substitutes = index === -1 ? [id] : catalog.rods.slice(index);
      if (substitutes.some(item => (stock.get(item) || 0) + (made.get(item) || 0) > 0)) continue;
      const producer = catalog.tools[id];
      if (producer && recipes[producer]?.learn <= level) craft(producer, 1, level, level, next);
      else {
        add(demand, id, 1);
        add(made, id, 1);
      }
    }
    if (!learned.has(spell)) {
      learned.add(spell);
      if (recipe.requirement) {
        requirements.add(recipe.requirement);
        if (!requirementsPaid.has(recipe.requirement)) {
          requirementsPaid.add(recipe.requirement);
          for (const [id, quantity] of recipe.unlock_materials) add(demand, id, take(id, quantity));
        }
      }
      if (recipe.formula) {
        if (!formulas.has(recipe.formula)) add(demand, recipe.formula, take(recipe.formula, 1));
        formulas.add(recipe.formula);
      } else if (recipe.fee === null) missingFees.add(recipe.name);
      else training += recipe.fee;
    }
    for (const [id, quantity] of recipe.reagents) {
      let remaining = take(id, quantity * count);
      const producer = components.get(id);
      const component = recipes[producer];
      const needsCurrentTool = component?.tools.some(tool => next.has(catalog.tools[tool]));
      if (remaining && component && component.output && component.learn <= level && !next.has(producer) && !needsCurrentTool) {
        craft(producer, Math.ceil(remaining / component.output), level, level, next);
        remaining = take(id, remaining);
      }
      if (remaining) add(demand, id, remaining);
    }
    if (recipe.product && recipe.output) add(made, recipe.product, recipe.output * count);
    steps.push({ spell, from: level, to: end, count, name: recipe.name, uncertain: end > recipe.yellow && end > level });
  }

  let position = start;
  for (const [from, to, spell, proposed] of route.steps) {
    if (from === to) {
      const product = recipes[spell].product;
      if (from >= start && from < target && !(stock.get(product) || made.get(product))) craft(spell, proposed, from, to);
      continue;
    }
    const left = Math.max(start, from);
    const right = Math.min(target, to);
    if (left >= right) continue;
    if (left !== position) throw new Error('路線在目前技能與目標之間有缺段。');
    const recipe = recipes[spell];
    let estimate = 0;
    for (let skill = left; skill < right; skill++) {
      const expected = 1 / probability(recipe, skill);
      estimate += expected;
      if (skill >= recipe.yellow) uncertain += expected;
    }
    craft(spell, left === from && right === to ? (proposed || Math.ceil(estimate)) : Math.ceil(estimate), left, right);
    position = right;
  }
  if (position !== target) throw new Error('這條路線未能到達目標。');

  const items = [...new Set([...usedStock.keys(), ...usedMade.keys(), ...demand.keys()])].map(id => {
    const offer = formulas.has(id) ? catalog.formulas[id] : catalog.supplies[id];
    return { id, name: catalog.items[id] || `物品 ${id}`, owned: usedStock.get(id) || 0,
      crafted: usedMade.get(id) || 0, ...procure(snapshot, id, demand.get(id) || 0, offer) };
  });
  return {
    name: route.name, steps, items, training, requirements: [...requirements], missingFees: [...missingFees],
    total: training + items.reduce((sum, item) => sum + item.spent, 0),
    missing: items.reduce((sum, item) => sum + item.missing, 0), uncertain,
  };
}

export function compareRoutes(catalog, profession, input, snapshot) {
  const routes = [];
  for (const route of profession.routes) {
    try { routes.push(planRoute(catalog, profession, route, input, snapshot)); }
    catch (error) {
      if (!(error instanceof Error) || !/[路線這條]/u.test(error.message)) throw error;
    }
  }
  if (!routes.length) throw new Error('這段技能目前沒有已核對的路線。');
  const availability = (a, b) => Number(Boolean(a.missing)) - Number(Boolean(b.missing))
    || Number(Boolean(a.missingFees.length)) - Number(Boolean(b.missingFees.length)) || a.missing - b.missing;
  return {
    cost: routes.slice().sort((a, b) => availability(a, b) || a.total - b.total || a.uncertain - b.uncertain)[0],
    stable: routes.slice().sort((a, b) => availability(a, b) || a.uncertain - b.uncertain || a.total - b.total)[0],
  };
}
