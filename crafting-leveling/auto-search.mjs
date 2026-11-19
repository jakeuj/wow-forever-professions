import { advanceRank, canCraft, finishBatch, initialState, prepareBatch } from './auto-actions.mjs';
import { procurement } from './auto-cost.mjs';
import { nextCraft, probabilityAtLeast, skillGain } from './auto-risk.mjs';

export const DEFAULT_CONFIDENCE = .9;
export const SEARCH_BUDGET_MS = 5000;
const BEAM_WIDTH = 4;
const MAX_STATES = 12000;
const MAX_BATCH = 300;

const chance = (state, skill) => probabilityAtLeast(state.risk, skill);
const spending = (a, b) => a.total - b.total || chance(b, b.anchor) - chance(a, a.anchor) || a.crafts - b.crafts;

function stateKey(state) {
  const entries = map => [...map].filter(([, quantity]) => quantity).sort(([a], [b]) => a - b);
  return JSON.stringify([
    state.cap, [...state.learned].sort((a, b) => a - b), entries(state.stock), entries(state.crafted),
    [...state.items].filter(([, item]) => item.needed)
      .map(([id, item]) => [id, item.needed, item.bought, item.formula]).sort(([a], [b]) => a - b),
    state.risk.min, state.risk.max, [...state.risk.mass.slice(state.risk.min, state.risk.max + 1)],
  ]);
}

function summarize(context, state, complete, bounded) {
  if (!state) return { status: 'blocked', bounded, reason: context.reason || '這段技能暫無可核對的配方。' };
  const probability = chance(state, context.target);
  const status = state.missing || !complete ? 'partial' : probability >= context.confidence ? 'qualified' : 'under-threshold';
  return {
    status, bounded, probability, confidence: context.confidence, bottleneck: state.bottleneck,
    reason: complete && !state.missing ? '' : context.reason || '依目前資料找到以下可準備的步驟。', reached: state.anchor,
    plan: {
      name: '自動選路', steps: state.steps, total: state.total, training: state.training, missing: state.missing,
      missingFees: [], requirements: [], items: [...state.items.values()].map(item => ({
        ...item, name: context.catalog.items[item.id] || `物品 ${item.id}`,
      })),
    },
  };
}

function pickBatches(context, state, recipe, end, includeFlexible = true, explicit = 0) {
  const live = chance(state, 0);
  if (!live) return [];
  const expectedStages = Math.max(1, Math.ceil((context.target - state.anchor) / (end - state.anchor)));
  const remaining = Math.min(1, context.confidence / live);
  const preferences = includeFlexible
    ? [.80, context.confidence, remaining ** (1 / expectedStages), .995]
    : [Math.min(.9999, remaining ** (1 / expectedStages))];
  let risk = state.risk;
  let previous = chance(state, end);
  let last = 0;
  const result = new Set();
  const pending = [...new Set(preferences.map(value => value * live))].sort((a, b) => a - b);
  for (let count = 1; count <= MAX_BATCH && !context.expired(); count++) {
    risk = nextCraft(risk, recipe, state.cap);
    const probability = probabilityAtLeast(risk, end);
    if (probability > previous) {
      previous = probability;
      last = count;
      while (probability >= pending[0]) {
        result.add(count);
        pending.shift();
      }
    }
    if ((!pending.length && probability > 0) || (risk.min >= end && probability > 0)) break;
  }
  if (last && !result.size) result.add(last);
  if (explicit > 0 && explicit <= MAX_BATCH) result.add(explicit);
  return [...result].sort((a, b) => a - b);
}

function compareLowerChance(a, b) {
  return chance(b, b.anchor) - chance(a, a.anchor) || spending(a, b);
}

function batchVariants(context, state, recipe, count, end) {
  const prepared = prepareBatch(context, state, recipe, count);
  if (!prepared) return [];
  const route = finishBatch(prepared, recipe, count, end);
  if (!route.missing || state.missing || count === 1) return [route];
  // Retain the number of crafts the available lots can actually fund as a lower-probability option.
  let low = 1;
  let high = count - 1;
  let affordable;
  while (low <= high && !context.expired()) {
    const mid = (low + high) >>> 1;
    const candidate = prepareBatch(context, state, recipe, mid);
    if (candidate && !candidate.missing) {
      affordable = [candidate, mid];
      low = mid + 1;
    } else high = mid - 1;
  }
  return affordable ? [route, finishBatch(affordable[0], recipe, affordable[1], end)] : [route];
}

function seedRoute(context, state, route) {
  for (const [start, finish, spell, planned] of route.steps) {
    if (context.expired() || state.anchor >= context.target) break;
    const recipe = context.recipes[spell];
    if (!recipe) return null;
    if (start === finish) {
      if (start >= state.anchor && start < context.target) {
        if (recipe.product && (state.stock.get(recipe.product) || state.crafted.get(recipe.product))) continue;
        const prepared = prepareBatch(context, state, recipe, planned);
        if (!prepared) return null;
        state = finishBatch(prepared, recipe, planned, state.anchor);
      }
      continue;
    }
    if (finish <= state.anchor) continue;
    if (start > state.anchor) return null;
    while (state.anchor < Math.min(finish, context.target) && !context.expired()) {
      if (state.anchor === state.cap) state = advanceRank(context, state);
      if (!state) return null;
      const end = Math.min(finish, context.target, state.cap);
      const counts = pickBatches(context, state, recipe, end, false, state.anchor === start && end === finish ? planned : 0);
      const variants = counts.flatMap(count => batchVariants(context, state, recipe, count, end))
        .filter(candidate => chance(candidate, end) > 0);
      const previousMass = chance(state, 0);
      const floor = previousMass * Math.min(.9999, (Math.min(1, context.confidence / previousMass)) **
        (1 / Math.max(1, Math.ceil((context.target - state.anchor) / (end - state.anchor)))));
      const winner = variants.filter(candidate => chance(candidate, end) >= floor)
        .sort((a, b) => a.missing - b.missing || spending(a, b))[0] ||
        variants.sort((a, b) => a.missing - b.missing || compareLowerChance(a, b))[0];
      if (!winner) return null;
      state = winner;
    }
  }
  return state;
}

function chooseRecipes(context, state) {
  const choices = [];
  for (const recipe of Object.values(context.recipes)) {
    const gain = skillGain(recipe, state.anchor);
    if (!gain || !canCraft(context, state, recipe)) continue;
    let missing = 0;
    let cost = 0;
    for (const [id, count] of recipe.reagents) {
      const covered = (state.stock.get(id) || 0) + (state.crafted.get(id) || 0);
      const prior = state.items.get(id);
      const quote = context.quote(id, (prior?.needed || 0) + Math.max(0, count - covered));
      missing += quote.missing - (prior?.missing || 0);
      cost += quote.spent - (prior?.spent || 0);
    }
    choices.push({ recipe, missing, score: cost / gain, gain });
  }
  const byPrice = choices.sort((a, b) => a.missing - b.missing || a.score - b.score || b.gain - a.gain);
  const byGain = [...byPrice].sort((a, b) => a.missing - b.missing || b.gain - a.gain || a.score - b.score
    || b.recipe.grey - a.recipe.grey);
  return [...new Set([...byPrice.slice(0, 6), ...byGain.slice(0, 3)].map(entry => entry.recipe))];
}

export function searchRoute(catalog, profession, input, snapshot, { seeds = [], components = [], progress = () => {},
  budget = SEARCH_BUDGET_MS, maxStates = MAX_STATES } = {}) {
  const startTime = performance.now();
  const confidence = input.confidence ?? DEFAULT_CONFIDENCE;
  if (!Number.isInteger(input.start) || !Number.isInteger(input.target) || input.start < 1 || input.start >= input.target
    || input.target > 300 || !profession.ranks.some(rank => rank.cap === input.cap) || input.start > input.cap
    || !(confidence > 0 && confidence <= 1)) throw new Error('請確認目前技能、技能上限與目標設定。');
  const recipes = Object.fromEntries(Object.entries(profession.recipes).map(([spell, recipe]) => [spell, { ...recipe, spell: Number(spell) }]));
  const checkpoints = [...new Set(Object.values(recipes)
    .filter(recipe => recipe.grant || input.known.includes(recipe.spell)
      || recipe.offers.some(offer => offer.level <= (input.level || 0)))
    .map(recipe => recipe.learn))].sort((a, b) => a - b);
  const context = {
    catalog, recipes, ranks: profession.ranks, target: input.target, confidence, level: input.level || 0,
    producers: new Map(components.map(spell => recipes[spell]).filter(recipe => recipe?.product && recipe.output)
      .map(recipe => [recipe.product, recipe])),
    quote: procurement(catalog, snapshot), expired: () => performance.now() - startTime >= budget,
  };
  const initial = initialState(input);
  const buckets = new Map([[input.start, new Map([[stateKey(initial), initial]])]]);
  let qualified;
  let lowChance;
  let partial;
  let expanded = 0;
  let lastProgress = 0;

  function consider(state) {
    if (!state || state.steps.length === 0) return;
    const probability = chance(state, input.target);
    if (state.anchor >= input.target && probability && !state.missing) {
      if (probability >= confidence) {
        if (!qualified || spending(state, qualified) < 0) qualified = state;
      } else if (!lowChance || compareLowerChance(state, lowChance) < 0) lowChance = state;
    } else if (!partial || state.anchor > partial.anchor || (state.anchor === partial.anchor
      && (state.missing - partial.missing || compareLowerChance(state, partial)) < 0)) partial = state;
  }

  function add(state) {
    consider(state);
    if (state.anchor >= input.target || chance(state, state.anchor) === 0) return;
    const bucket = buckets.get(state.anchor) || new Map();
    const key = stateKey(state);
    if (!bucket.has(key) || spending(state, bucket.get(key)) < 0) bucket.set(key, state);
    buckets.set(state.anchor, bucket);
  }

  for (const seed of seeds) {
    if (context.expired()) break;
    consider(seedRoute(context, initial, seed));
  }
  for (let skill = input.start; skill < input.target && expanded < maxStates && !context.expired(); skill++) {
    const states = [...(buckets.get(skill)?.values() || [])];
    if (!states.length) continue;
    buckets.delete(skill);
    const byCost = (a, b) => a.missing - b.missing || spending(a, b);
    const byChance = (a, b) => a.missing - b.missing || compareLowerChance(a, b);
    const beam = new Set([...states.sort(byCost).slice(0, BEAM_WIDTH - 1), ...states.sort(byChance).slice(0, 1)]);
    for (let state of beam) {
      if (context.expired() || ++expanded > maxStates) break;
      if (skill >= state.cap) {
        const trained = advanceRank(context, state);
        if (!trained) {
          context.reason = `到達 ${state.cap} 後需先學習下一階。請確認角色等級與目前技能上限。`;
          continue;
        }
        state = trained;
      }
      const available = chooseRecipes(context, state);
      if (!available.length) {
        const needsLevel = Object.values(recipes).some(recipe => skillGain(recipe, skill) > 0
          && recipe.offers.some(offer => offer.skill <= skill && offer.level > context.level));
        context.reason = needsLevel ? '請填寫角色等級以核對配方學習條件。'
          : `技能 ${skill} 缺少可學或已學的升點配方。`;
      }
      for (const recipe of available) {
        if (context.expired()) break;
        const nextRecipe = checkpoints.find(level => level > skill) || input.target;
        const end = Math.min(input.target, state.cap, recipe.grey, nextRecipe, Math.floor(skill / 10 + 1) * 10);
        for (const count of pickBatches(context, state, recipe, end)) {
          if (context.expired()) break;
          for (const candidate of batchVariants(context, state, recipe, count, end)) {
            if (chance(candidate, end) > 0) add(candidate);
            else if (candidate.risk.max > skill) {
              candidate.anchor = candidate.risk.max;
              candidate.steps.at(-1).to = candidate.anchor;
              add(candidate);
            }
          }
        }
      }
    }
    if (performance.now() - lastProgress >= 250) {
      lastProgress = performance.now();
      const best = qualified || lowChance;
      progress({ skill, result: best ? summarize(context, best, true, true) : null });
    }
  }
  const best = qualified || lowChance || partial;
  return summarize(context, best, Boolean(best?.anchor >= context.target), context.expired() || expanded >= maxStates);
}
