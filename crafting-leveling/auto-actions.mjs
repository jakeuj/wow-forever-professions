import { reserve } from './auto-cost.mjs';
import { initialRisk, nextCraft, probabilityAtLeast, requireSkill } from './auto-risk.mjs';

export function initialState(input) {
  return {
    anchor: input.start, cap: input.cap, risk: initialRisk(input.start, input.target),
    stock: new Map(input.inventory), crafted: new Map(), learned: new Set(input.known), items: new Map(),
    steps: [], total: 0, training: 0, missing: 0, crafts: 0, bottleneck: null,
  };
}

export function cloneState(state) {
  return { ...state, stock: new Map(state.stock), crafted: new Map(state.crafted),
    learned: new Set(state.learned), items: new Map(state.items), steps: state.steps.slice() };
}

function gate(state, skill, name) {
  const kept = probabilityAtLeast(state.risk, skill);
  if (kept === 0) return false;
  const loss = probabilityAtLeast(state.risk, 0) - kept;
  if (loss > (state.bottleneck?.loss || 0)) state.bottleneck = { name, skill, loss };
  state.risk = requireSkill(state.risk, skill);
  return true;
}

function available(state, id) {
  return (state.stock.get(id) || 0) + (state.crafted.get(id) || 0);
}

function learned(state, recipe) {
  return state.learned.has(recipe.spell) || (recipe.grant > 0 && recipe.grant * 75 <= state.cap);
}

export function learningOptions(context, state, recipe) {
  return learned(state, recipe) ? [] : recipe.offers.filter(offer => offer.skill <= state.anchor
    && (offer.level === 0 || offer.level <= context.level));
}

function learn(context, state, recipe) {
  if (learned(state, recipe)) return state;
  let chosen;
  for (const offer of learningOptions(context, state, recipe)) {
    const attempt = cloneState(state);
    if (!gate(attempt, offer.skill, recipe.name)) continue;
    if (offer.item) reserve(attempt, offer.item, 1, context, true);
    attempt.training += offer.fee;
    attempt.total += offer.fee;
    if (!chosen || attempt.missing < chosen.missing || (attempt.missing === chosen.missing
      && (attempt.total < chosen.total || (attempt.total === chosen.total
        && probabilityAtLeast(attempt.risk, 0) > probabilityAtLeast(chosen.risk, 0))))) chosen = attempt;
  }
  if (!chosen) return null;
  chosen.learned.add(recipe.spell);
  chosen.steps.push({ kind: 'learn', spell: recipe.spell, name: `學習 ${recipe.name}`, from: state.anchor, to: state.anchor, count: 1 });
  return chosen;
}

export function advanceRank(context, state) {
  const next = context.ranks.find(rank => rank.cap > state.cap);
  if (!next || context.level < next.level || state.anchor < next.skill) return null;
  const trained = cloneState(state);
  if (!gate(trained, next.skill, `訓練至技能上限 ${next.cap}`)) return null;
  trained.cap = next.cap;
  trained.training += next.fee;
  trained.total += next.fee;
  trained.steps.push({ kind: 'train', spell: next.cap, name: `訓練至技能上限 ${next.cap}`, from: next.skill, to: next.skill, count: 1 });
  return trained;
}

function cheaper(left, right) {
  return left.missing < right.missing || (left.missing === right.missing && left.total < right.total);
}

function obtainTool(context, state, id, visiting) {
  const rod = context.catalog.rods.indexOf(id);
  const substitutes = rod === -1 ? [id] : context.catalog.rods.slice(rod);
  if (substitutes.some(item => available(state, item))) return state;
  const producer = context.recipes[context.catalog.tools[id]];
  if (producer && !visiting.has(producer.spell)) {
    const prepared = prepareBatch(context, state, producer, 1, visiting);
    if (prepared) return finishBatch(prepared, producer, 1, state.anchor);
  }
  reserve(state, id, 1, context);
  state.crafted.set(id, 1);
  return state;
}

function obtainMaterial(context, state, id, count, visiting) {
  const need = count - available(state, id);
  const producer = context.producers.get(id);
  if (need <= 0 || !producer || visiting.has(producer.spell)) {
    reserve(state, id, count, context);
    return state;
  }
  const batches = Math.ceil(need / producer.output);
  const prepared = prepareBatch(context, state, producer, batches, visiting);
  const bought = cloneState(state);
  reserve(bought, id, count, context);
  if (!prepared) return bought;
  const made = finishBatch(prepared, producer, batches, state.anchor);
  reserve(made, id, count, context);
  // The recursive alternative may introduce a skill gate. Keep the safer purchase when it is cheaper or has equal cost.
  return cheaper(made, bought) ? made : bought;
}

export function canCraft(context, state, recipe) {
  return recipe.learn <= state.anchor && (learned(state, recipe) || learningOptions(context, state, recipe).length > 0);
}

export function prepareBatch(context, state, recipe, count, parent = new Set()) {
  if (parent.has(recipe.spell) || !canCraft(context, state, recipe)) return null;
  const visiting = new Set(parent).add(recipe.spell);
  let next = learn(context, cloneState(state), recipe);
  if (!next || !gate(next, recipe.learn, recipe.name)) return null;
  for (const id of recipe.tools) next = obtainTool(context, next, id, visiting);
  for (const [id, units] of recipe.reagents) next = obtainMaterial(context, next, id, count * units, visiting);
  return next;
}

export function finishBatch(state, recipe, count, to) {
  const from = state.anchor;
  if (recipe.product && recipe.output) state.crafted.set(recipe.product, (state.crafted.get(recipe.product) || 0) + recipe.output * count);
  for (let i = 0; i < count; i++) state.risk = nextCraft(state.risk, recipe, state.cap);
  state.crafts += count;
  state.anchor = to;
  state.steps.push({ kind: 'craft', spell: recipe.spell, name: recipe.name, from, to, count });
  return state;
}
