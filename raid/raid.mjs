import { buyFromDepth, currentDepth, loadDepth, loadItems, money, quoteLabel } from '../market/quotes.mjs';
import { copyButton, element, link, readLocal, saveLocal, shoppingButtons, table } from '../market/tools.mjs';
import { groups, mergeItems, verifyPlan } from './model.mjs';

const editor = document.querySelector('#raid-editor');
const roleForm = document.querySelector('#raid-role');
const status = document.querySelector('#raid-status');
const list = document.querySelector('#raid-checklist');
const quote = document.querySelector('#raid-quote');
const share = document.querySelector('#raid-share');
const panel = document.querySelector('#raid-editor-panel');
const [items, initialDepth] = await Promise.all([loadItems().catch(() => new Map()), loadDepth()]);
const ids = new Map();
for (const [id, name] of items) {
  if (ids.has(name)) ids.set(name, null);
  else ids.set(name, id);
}
let plan;
let key = '';
let done = {};

function parseGroup(text) {
  return text.split('\n').filter(row => row.trim()).map(row => {
    const pair = row.match(/^(.+?)\s*[:：×]\s*(\d+)\s*$/u);
    if (!pair) throw new Error('每列填「物品名稱：數量」，例如 13446：5。');
    const name = pair[1].trim();
    const id = /^\d{1,9}$/u.test(name) ? Number(name) : ids.get(name) || null;
    return { id, name: items.get(id) || (id ? `物品 ${id}` : name), quantity: Number(pair[2]) };
  });
}

function renderQuote(rows, checked) {
  const snapshot = currentDepth(initialDepth);
  const needed = rows.filter(row => !checked.has(row.id || row.name));
  quote.replaceChildren(element('p', quoteLabel(snapshot)));
  if (!needed.length) {
    quote.append(element('p', '這個職責的物品已經備妥。'));
    return;
  }
  const estimates = needed.map(row => ({
    ...row, estimate: row.id ? buyFromDepth(snapshot, row.id, row.quantity) : null,
  }));
  const complete = estimates.every(row => row.estimate && !row.estimate.missing);
  const total = estimates.reduce((sum, row) => sum + (row.estimate?.spent || 0), 0);
  quote.append(element('p', `${complete ? '缺料預估總價' : '缺料已知小計'} ${money(total)}`));
  quote.append(table(['待補物品', '需求', '可買', '已知價格'], estimates.map(row => [
    row.id ? link(row.name, `../market/?item=${row.id}#bulk`) : row.name, row.quantity,
    row.estimate && !row.estimate.unknown ? row.estimate.bought : '待查',
    row.estimate?.spent ? money(row.estimate.spent) : '—',
  ])));
  quote.append(shoppingButtons('團本備戰', needed.filter(row => !row.name.startsWith('物品 '))));
}

function render() {
  const role = roleForm.elements.role.value;
  const rows = mergeItems([...plan.common, ...plan[role]]);
  const checked = new Set(done[role] || []);
  const checklist = element('ul');
  checklist.className = 'tool-steps';
  for (const item of rows) {
    const row = element('li');
    const label = element('label');
    const control = element('input');
    const id = item.id || item.name;
    control.type = 'checkbox';
    control.checked = checked.has(id);
    control.addEventListener('change', () => {
      if (control.checked) checked.add(id);
      else checked.delete(id);
      done[role] = [...checked];
      saveLocal(key, done);
      renderQuote(rows, checked);
    });
    label.append(control, `${item.name} × ${item.quantity}`);
    row.append(label);
    checklist.append(row);
  }
  list.replaceChildren(element('h2', plan.title), rows.length ? checklist : element('p', '這個職責沒有待辦項目。'));
  renderQuote(rows, checked);
}

function load(data) {
  plan = verifyPlan(data);
  const contents = JSON.stringify(plan);
  const url = new URL(location.href);
  url.hash = `plan=${encodeURIComponent(contents)}`;
  if (url.href.length > 12000) throw new Error('清單連結過長，請減少品項或縮短名稱。');
  key = `dawnblade.raid.v1:${contents}`;
  done = readLocal(key, {});
  roleForm.elements.role.value = ['tank', 'healer', 'damage'].includes(done.role) ? done.role : 'tank';
  roleForm.hidden = false;
  editor.elements.title.value = plan.title;
  for (const group of groups) {
    editor.elements[group].value = plan[group].map(item =>
      `${item.id || item.name}：${item.quantity}`).join('\n');
  }
  status.textContent = '';
  share.replaceChildren(copyButton('複製分享連結', url.href));
  history.replaceState(null, '', url);
  render();
}

roleForm.addEventListener('change', () => {
  done.role = roleForm.elements.role.value;
  saveLocal(key, done);
  render();
});
editor.addEventListener('submit', event => {
  event.preventDefault();
  try {
    const data = Object.fromEntries(groups.map(group => [group, parseGroup(editor.elements[group].value)]));
    load({ schema: 1, title: editor.elements.title.value.trim(), ...data });
  } catch (error) {
    status.textContent = error.message;
  }
});
if (location.hash.startsWith('#plan=')) {
  try {
    load(JSON.parse(decodeURIComponent(location.hash.slice(6))));
    panel.open = false;
  } catch (error) {
    status.textContent = error.message;
  }
}
