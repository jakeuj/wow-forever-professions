import { loadDepth, money, quoteLabel } from '../market/quotes.mjs';
import { element, shoppingButtons, table } from '../market/tools.mjs';
import { crates, names, payouts } from './data.mjs';
import { overview, plan } from './optimizer.mjs';

const tierNames = { apprentice: '初級', journeyman: '中級', expert: '高級', artisan: '專家級' };
const kinds = crates.map(([id, tier, quality, level, bundles]) => {
  const [favor, refund] = payouts[tier][quality - 1];
  return { id, tier, quality, level, bundles, favor, refund };
});

const form = document.querySelector('#waylaid-form');
const status = document.querySelector('#waylaid-status');
const planBox = document.querySelector('#waylaid-plan');
const rankBox = document.querySelector('#waylaid-rank');

const nameOf = id => names.get(id) || `物品 ${id}`;
const shortName = id => nameOf(id).replace(/^遭攔截的木箱：/u, '');
const kindLabel = kind => `${tierNames[kind.tier]}・${kind.quality === 1 ? '白' : '綠'}`;
const per100 = copper => `${money(copper * 100)}`;

function cell(text, className) {
  const node = element('span', text);
  if (className) node.className = className;
  return node;
}

function itemName(id, label = nameOf(id)) {
  return cell(label, 'wl-name');
}

function readForm() {
  const goal = Math.min(5000, Math.max(5, Math.round(form.elements.goal.valueAsNumber) || 300));
  const level = Math.min(60, Math.max(10, Math.round(form.elements.level.valueAsNumber) || 60));
  form.elements.goal.value = goal;
  form.elements.level.value = level;
  return { goal, level };
}

function renderPlan(depth, goal, level) {
  const usable = kinds.filter(kind => kind.level <= level);
  const result = plan(usable, depth, goal);
  if (!result.picks.length) {
    planBox.replaceChildren(element('p', '目前拍賣場上買不齊任何一種木箱。'));
    return;
  }
  const summary = element('p');
  summary.className = 'wl-summary';
  summary.append(
    cell(`${result.favor} 點`, 'wl-strong'), ` · 買 ${money(result.spend)}，繳交退回 ${money(result.refund)}，淨花 `,
    cell(money(result.cost), 'wl-strong'),
    ` · 每 100 點 ${per100(result.cost / result.favor)}`,
  );
  const notes = [summary];
  if (result.short) notes.push(element('p', `拍賣場的貨只夠 ${result.favor} 點，未達目標 ${goal} 點。`));
  const crateRows = result.picks.map(pick => [
    itemName(pick.kind.id, shortName(pick.kind.id)), cell(kindLabel(pick.kind)), cell(`${pick.count} 箱`),
    cell(`${pick.favor} 點`), cell(money(pick.cost)), cell(per100(pick.cost / pick.favor)),
  ]);
  const shopping = [];
  const lineRows = result.picks.flatMap(pick => pick.lines.map(line => {
    shopping.push({ name: nameOf(line.item), quantity: line.units });
    return [
      itemName(line.item), cell(line.crate ? `${line.units} 個` : `${line.units}（${line.bundles} 組 × ${line.per}）`),
      cell(money(line.top)), cell(money(line.cost)),
    ];
  }));
  planBox.replaceChildren(
    ...notes,
    table(['木箱', '階級', '箱數', '貢獻點', '淨成本', '每 100 點'], crateRows),
    element('h3', '要買的東西'),
    table(['物品', '數量', '最高單價', '小計'], lineRows),
    shoppingButtons(`木箱貢獻${goal}`, shopping),
  );
}

function renderRank(depth, level) {
  const rows = overview(kinds, depth).map(row => {
    const { kind } = row;
    const tooHigh = kind.level > level;
    const name = itemName(kind.id, shortName(kind.id));
    const bundle = row.bundle ? `${nameOf(row.bundle[0])} × ${row.bundle[1]}` : '買不齊';
    const cells = [
      name, cell(kindLabel(kind)), cell(`${kind.level}${tooHigh ? '（未達）' : ''}`), cell(`${kind.favor}`),
      cell(bundle), cell(row.spend === undefined ? '—' : money(row.spend)),
      cell(row.perFavor === undefined ? '—' : per100(row.perFavor), 'wl-strong'), cell(`${row.stock}`),
    ];
    if (tooHigh) cells.forEach(node => node.classList.add('wl-muted'));
    return cells;
  });
  rankBox.replaceChildren(table(['木箱', '階級', '需求等級', '貢獻點', '最便宜的填法', '一箱總價', '每 100 點', '在售箱數'], rows));
}

const depth = await loadDepth();
function render() {
  const { goal, level } = readForm();
  const params = new URLSearchParams(location.search);
  params.set('goal', goal);
  params.set('level', level);
  history.replaceState(null, '', `?${params}${location.hash}`);
  if (!depth) {
    status.textContent = `${quoteLabel(null)}：三小時內的價位資料暫時讀不到，請稍後再試。`;
    planBox.replaceChildren();
    rankBox.replaceChildren(element('p', '行情待更新。'));
    return;
  }
  status.textContent = quoteLabel(depth);
  renderPlan(depth.depth, goal, level);
  renderRank(depth.depth, level);
}

const params = new URLSearchParams(location.search);
if (/^\d+$/u.test(params.get('goal') || '')) form.elements.goal.value = params.get('goal');
if (/^\d+$/u.test(params.get('level') || '')) form.elements.level.value = params.get('level');
form.addEventListener('submit', event => {
  event.preventDefault();
  render();
});
render();
