import { buyFromDepth, currentDepth, loadDepth, loadItems, money, quoteLabel } from './quotes.mjs';
import { element, shoppingButtons, table } from './tools.mjs';

const form = document.querySelector('#bulk-form');
const status = document.querySelector('#bulk-status');
const result = document.querySelector('#bulk-result');
const list = document.querySelector('#bulk-items');
const input = form.elements.namedItem('item');
const [items, depth] = await Promise.all([loadItems().catch(() => new Map()), loadDepth()]);
const itemIds = new Map();
for (const [id, name] of items) {
  const option = element('option');
  option.value = `${name} · ${id}`;
  itemIds.set(option.value, id);
  list.append(option);
}
status.textContent = quoteLabel(depth);
form.addEventListener('submit', event => {
  event.preventDefault();
  const query = input.value.trim();
  const matching = [...items].filter(([, name]) => name === query);
  const id = itemIds.get(query) || (/^\d+$/u.test(query) ? Number(query) : null) ||
    (matching.length === 1 ? matching[0][0] : null);
  if (!id) {
    result.replaceChildren(element('p', '請選一個搜尋結果，或輸入物品 ID。'));
    return;
  }
  const snapshot = currentDepth(depth);
  status.textContent = quoteLabel(snapshot);
  const name = items.get(id) || `物品 ${id}`;
  const quantity = form.elements.amount.valueAsNumber;
  const quote = buyFromDepth(snapshot, id, quantity);
  const summary = quote.unknown ? '目前無法確認價格或在售量。' : [
    `可買 ${quote.bought} 件 · 缺 ${quote.missing} 件`,
    `總價 ${money(quote.spent)}`,
    quote.bought ? `均價 ${money(quote.spent / quote.bought)}` : '',
  ].filter(Boolean).join(' · ');
  result.replaceChildren(element('p', `${name} × ${quantity} · ${summary}`));
  if (quote.tiers.length) result.append(table(['單價', '採買件數'], quote.tiers.map(tier => [money(tier.price), tier.units])));
  result.append(shoppingButtons('批量採買', [{ name, quantity }]));
});
const item = new URLSearchParams(location.search).get('item');
if (item && /^\d+$/u.test(item)) {
  input.value = item;
  form.requestSubmit();
}
