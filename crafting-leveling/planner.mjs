import { currentDepth, loadDepth, money, quoteLabel } from '../market/quotes.mjs';
import { element, readLocal, saveLocal, shoppingButtons, table } from '../market/tools.mjs';
import { compareRoutes } from './route.mjs';

const form = document.querySelector('#leveling-form');
const status = document.querySelector('#leveling-status');
const output = document.querySelector('#leveling-result');
const key = 'dawnblade.leveling.v1';
const saved = readLocal(key, {});
const query = new URLSearchParams(location.search);
const character = (query.get('character') || '').trim().slice(0, 50);
const planKey = profession => character ? `${profession}:${character}` : profession;
const stampLabel = snapshot => [character, quoteLabel(snapshot)].filter(Boolean).join(' · ');

function inventory(text, names) {
  const counts = new Map();
  for (const row of text.split('\n').filter(line => line.trim())) {
    const pair = row.match(/^(.+?)\s*[:：×]\s*(\d+)\s*$/u);
    const value = pair && Number(pair[2]);
    if (!pair || !Number.isSafeInteger(value) || value > 999999) throw new Error('庫存每列填「物品名稱：數量」。');
    const term = pair[1].trim();
    const matching = Object.entries(names).filter(([, name]) => name === term);
    const id = /^\d+$/u.test(term) && names[term] ? Number(term) : matching.length === 1 ? Number(matching[0][0]) : 0;
    if (!id) throw new Error(`找不到唯一的物品「${term}」，請用物品 ID。`);
    counts.set(id, (counts.get(id) || 0) + value);
  }
  return counts;
}

function renderPlan(plan, checked, update) {
  output.replaceChildren(
    element('h3', plan.name),
    element('p', `${plan.missing || plan.missingFees.length ? '已知支出' : '預估支出'} ${money(plan.total)} · 學費 ${money(plan.training)} · 缺料 ${plan.missing} 件`),
  );
  if (plan.requirements.length) output.append(element('p', `前置條件 · ${plan.requirements.join('、')}`));
  if (plan.missingFees.length) output.append(element('p', `學費待查 · ${plan.missingFees.join('、')}`));
  const steps = element('ol');
  steps.className = 'tool-steps';
  for (const [index, step] of plan.steps.entries()) {
    const row = element('li');
    const label = element('label');
    const box = element('input');
    box.type = 'checkbox';
    const id = [plan.name, index, step.spell, step.from, step.to, step.count].join(':');
    box.checked = checked.has(id);
    box.addEventListener('change', () => {
      if (box.checked) checked.add(id);
      else checked.delete(id);
      update([...checked]);
    });
    const range = step.to === step.from ? '先備妥' : `${step.from} → ${step.to}`;
    label.append(box, `${range} · ${step.name} × ${step.count}${step.uncertain ? '（預估）' : ''}`);
    row.append(label);
    steps.append(row);
  }
  output.append(steps);
  const rows = plan.items.map(item => [
    `${item.name} · ${item.id}`, item.owned, item.crafted, item.bought,
    item.vendorUnits ? `${item.vendorUnits} · ${item.vendor}` : '—',
    item.unknown && item.missing ? `${item.missing} 件待查` : item.missing,
    item.unknown && !item.spent ? '—' : money(item.spent),
  ]);
  output.append(table(['材料／配方', '庫存', '自製', '拍賣場可買', 'NPC', '待補', '已知支出'], rows));
  output.append(shoppingButtons('專業練等', plan.items
    .filter(item => item.bought + item.missing > 0 && !item.name.startsWith('物品 '))
    .map(item => ({ name: item.name, quantity: item.bought + item.missing }))));
}

try {
  const [catalog, initialDepth] = await Promise.all([
    fetch('./routes.json').then(response => {
      if (!response.ok) throw new Error('練等路線資料暫時無法讀取。');
      return response.json();
    }),
    loadDepth(),
  ]);
  for (const [id, profession] of Object.entries(catalog.professions)) {
    form.elements.profession.add(new Option(profession.name, id));
  }
  const updateOptions = () => {
    const id = form.elements.profession.value;
    const state = saved[planKey(id)] || {};
    const known = new Set(state.known || []);
    form.elements.known.replaceChildren(...Object.entries(catalog.professions[id].recipes)
      .sort(([, a], [, b]) => a.learn - b.learn || a.name.localeCompare(b.name, 'zh-TW'))
      .map(([spell, recipe]) => new Option(`${recipe.learn} · ${recipe.name}`, spell, false, known.has(Number(spell)))));
    form.elements.from.value = state.start || 1;
    form.elements.target.value = state.target || 150;
    form.elements.inventory.value = state.inventory || '';
  };
  if (Object.hasOwn(catalog.professions, query.get('profession'))) form.elements.profession.value = query.get('profession');
  updateOptions();
  for (const name of ['from', 'target']) {
    if (/^\d{1,3}$/u.test(query.get(name) || '')) form.elements[name].value = query.get(name);
  }
  form.elements.profession.addEventListener('change', updateOptions);
  const choices = document.querySelector('#leveling-choices');
  const stamp = () => currentDepth(initialDepth);
  status.textContent = stampLabel(stamp());
  form.hidden = false;
  form.addEventListener('submit', event => {
    event.preventDefault();
    const id = form.elements.profession.value;
    choices.replaceChildren();
    output.replaceChildren();
    const start = form.elements.from.valueAsNumber;
    const target = form.elements.target.valueAsNumber;
    const data = form.elements.inventory.value;
    const known = [...form.elements.known.selectedOptions].map(option => Number(option.value));
    try {
      if (start >= target) throw new Error('目標技能需高於目前技能。');
      const snapshot = stamp();
      status.textContent = stampLabel(snapshot);
      const routes = compareRoutes(catalog, catalog.professions[id],
        { start, target, known, inventory: inventory(data, catalog.items) }, snapshot);
      const storage = planKey(id);
      const state = { start, target, known, inventory: data, done: saved[storage]?.done || [] };
      saved[storage] = state;
      saveLocal(key, saved);
      const checked = new Set(state.done);
      const show = plan => renderPlan(plan, checked, done => {
        state.done = done;
        saveLocal(key, saved);
      });
      for (const [mode, label] of [['cost', '省金幣'], ['stable', '穩定升點']]) {
        const plan = routes[mode];
        const button = element('button', `${label} · ${money(plan.total)}${plan.missing ? '（部分）' : ''}`);
        button.type = 'button';
        button.className = 'button-compact';
        button.addEventListener('click', () => {
          for (const choice of choices.children) choice.setAttribute('aria-pressed', String(choice === button));
          show(plan);
        });
        choices.append(button);
      }
      choices.firstElementChild.click();
    } catch (error) {
      output.append(element('p', error.message));
    }
  });
  if (query.has('from') || query.has('target')) form.requestSubmit();
} catch (error) {
  status.textContent = error.message;
}
