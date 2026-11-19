import { currentDepth, loadDepth, money, quoteLabel } from '../market/quotes.mjs?v=2';
import { element, readLocal, saveLocal, shoppingButtons, table } from '../market/tools.mjs';
import { compareRoutes } from './route.mjs';
import { DEFAULT_CONFIDENCE, SEARCH_BUDGET_MS } from './auto-search.mjs';

const form = document.querySelector('#leveling-form');
const status = document.querySelector('#leveling-status');
const output = document.querySelector('#leveling-result');
const key = 'dawnblade.leveling.v1';
const searchStatus = document.querySelector('#leveling-search-status');
const autoRun = document.querySelector('#leveling-auto-run');
const cancel = document.querySelector('#leveling-auto-cancel');
const options = document.querySelector('#leveling-auto-options');
const saved = readLocal(key, {});
const query = new URLSearchParams(location.search);
const character = (query.get('character') || '').trim().slice(0, 50);
const planKey = profession => character ? `${profession}:${character}` : profession;
const stampLabel = snapshot => [character, quoteLabel(snapshot)].filter(Boolean).join(' · ');
let active;

function stop() {
  if (!active) return;
  active.request.abort();
  active.worker?.terminate();
  clearTimeout(active.timer);
  active = null;
  cancel.hidden = true;
}

function percent(probability) {
  return `${(Math.floor(probability * 1000 + 1e-9) / 10).toFixed(1)}%`;
}

function showSearch(update, show) {
  const { status, probability, confidence, reason, reached, plan, bottleneck, bounded } = update;
  const label = {
    qualified: '本次搜尋找到的最低支出',
    'under-threshold': '可備料，達標機率低於設定門檻',
    partial: '部分估價',
    blocked: '暫無可行方案',
  }[status];
  searchStatus.textContent = [label, bounded && '已達搜尋預算', reason].filter(Boolean).join(' · ');
  if (!plan) return;
  show(plan);
  const description = probability > 0
    ? `達標機率估計 ${percent(probability)} · 設定門檻 ${Math.round(confidence * 100)}%${plan.missing ? '（材料備齊時）' : ''}`
    : `目前路線到技能 ${reached} · 目標尚未達成`;
  output.prepend(element('p', description));
  if (bottleneck) output.prepend(element('p', `學習門檻風險 · ${bottleneck.name}（技能 ${bottleneck.skill}）`));
}

function startWorker(job, payload, show, target) {
  searchStatus.textContent = '搜尋可行的配方組合…';
  let recent;
  const worker = new Worker(new URL('./auto-worker.mjs', import.meta.url), { type: 'module' });
  job.worker = worker;
  job.timer = setTimeout(() => {
    if (active !== job) return;
    stop();
    if (recent) showSearch({ ...recent, bounded: true }, show);
    else searchStatus.textContent = '搜尋逾時。可改用「比較路線」查看既有方案。';
  }, SEARCH_BUDGET_MS + 1000);
  worker.addEventListener('message', ({ data: update }) => {
    if (active !== job) return;
    if (update.type === 'progress') {
      recent = update.result || recent;
      searchStatus.textContent = `搜尋技能 ${update.skill} → ${target} 的配方…`;
    } else if (update.type === 'complete') {
      stop();
      showSearch(update.result, show);
    } else {
      stop();
      searchStatus.textContent = update.message;
    }
  });
  worker.addEventListener('error', () => {
    if (active !== job) return;
    stop();
    searchStatus.textContent = '自動選路暫時無法啟動。可改用「比較路線」。';
  });
  worker.postMessage(payload);
}

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
    const id = [plan.name, index, ...(step.kind ? [step.kind] : []), step.spell, step.from, step.to, step.count].join(':');
    box.checked = checked.has(id);
    box.addEventListener('change', () => {
      if (box.checked) checked.add(id);
      else checked.delete(id);
      update([...checked]);
    });
    const range = step.to === step.from ? '先備妥' : `${step.from} → ${step.to}`;
    const action = step.kind === 'train' || step.kind === 'learn'
      ? step.name : `${range} · ${step.name} × ${step.count}${step.uncertain ? '（預估）' : ''}`;
    label.append(box, action);
    row.append(label);
    steps.append(row);
  }
  output.append(steps);
  const rows = plan.items.map(item => [
    `${item.name} · ${item.id}`, item.owned, item.crafted, item.bought,
    item.vendorUnits ? `${item.vendorUnits} · ${item.vendor}${item.surplus ? `（剩 ${item.surplus}）` : ''}` : '—',
    item.unknown && item.missing ? `${item.missing} 件待查` : item.missing,
    item.unknown && !item.spent ? '—' : money(item.spent),
  ]);
  output.append(table(['材料／配方', '庫存', '自製', '拍賣場可買', 'NPC', '待補', '已知支出'], rows));
  output.append(shoppingButtons('專業練等', plan.items
    .filter(item => item.bought + item.missing > 0 && !item.name.startsWith('物品 '))
    .map(item => ({ name: item.name, quantity: item.bought + item.missing }))));
}

try {
  const [catalog, auto, initialDepth] = await Promise.all([
    fetch('./routes.json').then(response => {
      if (!response.ok) throw new Error('練等路線資料暫時無法讀取。');
      return response.json();
    }),
    fetch('./auto-recipes.json').then(response => response.ok ? response.json() : null).catch(() => null),
    loadDepth(),
  ]);
  for (const [id, profession] of Object.entries(catalog.professions)) {
    form.elements.profession.add(new Option(profession.name, id));
  }
  const updateOptions = () => {
    const id = form.elements.profession.value;
    const state = saved[planKey(id)] || {};
    const known = new Set(state.known || []);
    const recipes = { ...catalog.professions[id].recipes, ...auto?.professions[id]?.recipes };
    form.elements.known.replaceChildren(...Object.entries(recipes)
      .sort(([, a], [, b]) => a.learn - b.learn || a.name.localeCompare(b.name, 'zh-TW'))
      .map(([spell, recipe]) => new Option(`${recipe.learn} · ${recipe.name}`, spell, false, known.has(Number(spell)))));
    form.elements.from.value = state.start || 1;
    form.elements.target.value = state.target || 150;
    form.elements.inventory.value = state.inventory || '';
    form.elements.cap.value = state.cap || '';
    form.elements.characterLevel.value = state.level || '';
    form.elements.confidence.value = state.confidence || '.9';
    autoRun.hidden = options.hidden = !auto?.professions[id];
  };
  if (Object.hasOwn(catalog.professions, query.get('profession'))) form.elements.profession.value = query.get('profession');
  updateOptions();
  for (const name of ['from', 'target']) {
    if (/^\d{1,3}$/u.test(query.get(name) || '')) form.elements[name].value = query.get(name);
  }
  form.elements.profession.addEventListener('change', updateOptions);
  const choices = document.querySelector('#leveling-choices');
  status.textContent = stampLabel(currentDepth(initialDepth));
  form.hidden = false;
  form.addEventListener('input', () => {
    if (active) {
      stop();
      searchStatus.textContent = '輸入已變更，可重新計算。';
    }
  });
  cancel.addEventListener('click', () => {
    stop();
    searchStatus.textContent = '已取消計算。';
  });
  form.addEventListener('submit', async event => {
    event.preventDefault();
    stop();
    const id = form.elements.profession.value;
    const runAuto = event.submitter === autoRun && Boolean(auto?.professions[id]);
    const job = { request: new AbortController() };
    active = job;
    cancel.hidden = !runAuto;
    searchStatus.textContent = '確認本次使用的行情…';
    choices.replaceChildren();
    output.replaceChildren();
    const start = form.elements.from.valueAsNumber;
    const target = form.elements.target.valueAsNumber;
    const data = form.elements.inventory.value;
    const capSetting = form.elements.cap.value;
    const cap = capSetting ? Number(capSetting) : Math.ceil(start / 75) * 75;
    const level = Number(form.elements.characterLevel.value) || 0;
    const confidence = form.elements.confidence.value;
    const known = [...form.elements.known.selectedOptions].map(option => Number(option.value));
    try {
      if (start >= target) throw new Error('目標技能需高於目前技能。');
      if (runAuto && start > cap) throw new Error('目前技能高於選取的技能上限。');
      const materials = inventory(data, { ...catalog.items, ...auto?.items });
      const snapshot = await loadDepth({ signal: job.request.signal });
      if (active !== job) return;
      status.textContent = stampLabel(snapshot);
      const storage = planKey(id);
      const state = { start, target, known, inventory: data, cap: capSetting, level, confidence, done: saved[storage]?.done || [] };
      saved[storage] = state;
      saveLocal(key, saved);
      const checked = new Set(state.done);
      const show = plan => renderPlan(plan, checked, done => {
        state.done = done;
        saveLocal(key, saved);
      });
      if (runAuto) {
        const { professions, ...source } = auto;
        startWorker(job, { catalog: source, profession: professions[id], snapshot, seeds: catalog.professions[id].routes,
          components: catalog.professions[id].components, input: {
            start, target, known, cap, level, confidence: Number(confidence) || DEFAULT_CONFIDENCE, inventory: [...materials],
          } }, show, target);
        return;
      }
      const routes = compareRoutes(catalog, catalog.professions[id], { start, target, known, inventory: materials }, snapshot);
      stop();
      searchStatus.textContent = '';
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
      if (active !== job) return;
      stop();
      searchStatus.textContent = '';
      output.append(element('p', error.message));
    }
  });
  if (query.has('from') || query.has('target')) form.requestSubmit();
} catch (error) {
  status.textContent = error.message;
}
