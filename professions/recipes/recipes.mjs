import { loadGuildSnapshot } from '../../guild/data-source.mjs';
import { currentDepth, loadDepth, money, quoteLabel } from '../../market/quotes.mjs';
import { copyButton, element, link, numericItems, readLocal, saveLocal, shoppingButtons, table } from '../../market/tools.mjs';
import { knownRecipeKey } from '../../players/model.mjs';
import { quoteRecipe } from '../recipe-quotes.mjs';

const professions = new Map([[171, '鍊金術'], [164, '鍛造'], [333, '附魔'], [202, '工程學'], [165, '製皮'], [197, '裁縫']]);
const slugs = ['alchemy', 'blacksmithing', 'enchanting', 'engineering', 'leatherworking', 'tailoring'];
const known = new Set(readLocal(knownRecipeKey, []));
const form = document.querySelector('#recipe-search');
const status = document.querySelector('#recipe-status');
const output = document.querySelector('#recipe-results');
const selected = document.querySelector('#recipe-selection');
const parameters = new URLSearchParams(location.search);

async function fallbackRecipes() {
  const response = await fetch('../../crafting-leveling/routes.json');
  if (!response.ok) return [];
  const { items, professions: catalog } = await response.json();
  return [...professions.keys()].flatMap((profession, index) => Object.entries(catalog[slugs[index]].recipes)
    .map(([spell, recipe]) => ({
      id: `spell-${spell}`, profession, name: recipe.name, units: recipe.output,
      product: recipe.product ? { id: recipe.product, name: items[recipe.product] || recipe.name } : null,
      materials: recipe.reagents.map(([id, quantity]) => ({ id, quantity, name: items[id] })),
    })));
}

const [catalog, roster, initialDepth] = await Promise.all([
  loadGuildSnapshot('recipes').catch(() => null),
  loadGuildSnapshot('artisans').catch(() => null),
  loadDepth(),
]);
const recipes = catalog?.recipes || await fallbackRecipes().catch(() => []);
const getDepth = () => currentDepth(initialDepth);
const rosterFor = recipe => roster && Date.parse(roster.expiresAt) > Date.now()
  ? roster.artisans.filter(person => person.professions.some(skill => skill.id === recipe.profession && skill.recipeIds.includes(recipe.id))) : [];
const normalize = value => value.normalize('NFKC').trim().toLocaleLowerCase('zh-TW');

function renderEstimate(recipe, quantity, inventory, service, box) {
  const depth = getDepth();
  const quote = quoteRecipe(recipe, quantity, inventory, null, depth);
  box.replaceChildren(element('p', quoteLabel(depth)));
  if (!recipe.materials) box.append(element('p', '此配方的材料資料待確認。'));
  if (recipe.product) {
    const buy = quote.direct.missing ? `直購只查到 ${quote.direct.bought} 件` : `直購 ${money(quote.direct.spent)}`;
    box.append(element('p', `${buy} · 製作 ${quote.batches} 批`));
  }
  box.append(element('p', `${quote.incomplete ? '已知材料支出' : '代工支出'} ${money(quote.materialCost + service)}（含代工費 ${money(service)}）`));
  const name = item => item.name || `物品 ${item.id}`;
  if (quote.materials.length) box.append(table(['材料', '需求', '自備', '可買', '待補', '支出'], quote.materials.map(item => [
    `${name(item)} · ${item.id}`, item.quantity, item.owned, item.bought, item.missing, money(item.spent),
  ])));
  box.append(shoppingButtons('製造採購', quote.materials.filter(item => item.needed && item.name)
    .map(item => ({ name: item.name, quantity: item.needed }))));
}

function showRecipe(recipe) {
  const details = element('article');
  details.append(element('h2', recipe.name));
  const controls = element('form');
  controls.className = 'tool-form';
  const quantityLabel = element('label', recipe.product ? '成品需求件數' : '代工批次');
  const amount = element('input');
  Object.assign(amount, { type: 'number', min: '1', max: '9999', value: '1', required: true });
  quantityLabel.append(amount);
  const inventoryLabel = element('label', '手邊材料（每列物品 ID：數量）');
  const inventory = element('textarea');
  inventoryLabel.append(inventory);
  const feeLabel = element('label', '代工費（銅）');
  const fee = element('input');
  Object.assign(fee, { type: 'number', min: '0', max: '999999999', value: '0', required: true });
  feeLabel.append(fee);
  const knownLabel = element('label');
  const learned = element('input');
  learned.type = 'checkbox';
  learned.checked = known.has(recipe.id);
  learned.addEventListener('change', () => {
    if (learned.checked) known.add(recipe.id);
    else known.delete(recipe.id);
    saveLocal(knownRecipeKey, [...known]);
    render();
  });
  knownLabel.append(learned, '我已學這項配方');
  const calculate = element('button', '更新估價');
  calculate.className = 'button-compact';
  controls.append(quantityLabel, feeLabel, inventoryLabel, knownLabel, calculate);
  const estimate = element('div');
  estimate.setAttribute('aria-live', 'polite');
  controls.addEventListener('submit', event => {
    event.preventDefault();
    try { renderEstimate(recipe, amount.valueAsNumber, numericItems(inventory.value), fee.valueAsNumber, estimate); }
    catch (error) { estimate.replaceChildren(element('p', error.message)); }
  });
  details.append(controls, estimate, element('h3', '公會代工'));
  const artisans = rosterFor(recipe);
  if (!artisans.length) details.append(element('p', '目前名冊無可查的工匠。'));
  for (const person of artisans) {
    const row = element('p');
    const slug = person.slug || person.name.replace(/\s+/gu, '-').toLowerCase();
    row.append(link(person.name, `../../players/?character=${encodeURIComponent(slug)}`), ' ',
      copyButton('複製密語', `/w ${person.name.replace(/\s+/gu, '-')} 您好，想請問能代工${recipe.name}嗎？材料和代工費可以再確認，謝謝！`));
    details.append(row);
  }
  selected.replaceChildren(details);
  controls.requestSubmit();
}

function render() {
  const depth = getDepth();
  const keyword = normalize(form.elements.keyword.value);
  const profession = Number(form.elements.profession.value);
  const minimum = form.elements.stock.valueAsNumber || 0;
  const fee = form.elements.fee.value === '' ? null : form.elements.fee.valueAsNumber;
  const scores = recipes
    .filter(recipe => (!profession || profession === recipe.profession) && (!form.elements.known.checked || known.has(recipe.id)))
    .filter(recipe => [recipe.name, recipe.product?.name || '', String(recipe.product?.id || ''), String(recipe.id)]
      .some(value => normalize(value).includes(keyword)))
    .filter(recipe => !minimum || (recipe.materials?.length && recipe.materials.every(item =>
      (depth?.depth[item.id]?.reduce((sum, [, count]) => sum + count, 0) || 0) >= minimum)))
    .map(recipe => ({ recipe, ...quoteRecipe(recipe, 1, new Map(), fee, depth) }))
    .sort((a, b) => ((b.net ?? b.gross) ?? -Infinity) - ((a.net ?? a.gross) ?? -Infinity)
      || a.recipe.name.localeCompare(b.recipe.name, 'zh-TW'));
  status.textContent = `${quoteLabel(depth)} · ${catalog ? '官方配方' : '已核對的練等配方'}`;
  output.replaceChildren(element('p', `共 ${scores.length} 項配方。金額依掛單估算。`));
  let visible = 0;
  const results = element('div');
  const more = element('button', '顯示更多配方');
  more.className = 'button-compact';
  const next = () => {
    const page = scores.slice(visible, visible + 25);
    if (page.length) results.append(table(['配方', '每批材料成本', '成品單價', fee === null ? '單位毛利' : '扣費後單位毛利'], page.map(score => {
      const button = element('button', score.recipe.name);
      button.className = 'button-compact';
      button.addEventListener('click', () => {
        showRecipe(score.recipe);
        selected.scrollIntoView({ block: 'start' });
      });
      const profit = fee === null ? score.gross : score.net;
      return [button, score.incomplete ? '資料或材料不足' : money(score.materialCost),
        score.askingPrice ? money(score.askingPrice) : '—', profit !== null ? money(profit) : '—'];
    })));
    visible += page.length;
    more.hidden = visible >= scores.length;
  };
  more.addEventListener('click', next);
  output.append(results, more);
  next();
}

for (const [id, name] of professions) form.elements.profession.add(new Option(name, id));
form.hidden = false;
form.addEventListener('submit', event => { event.preventDefault(); render(); });
const selectedRecipe = recipes.find(recipe => String(recipe.id) === parameters.get('recipe'))
  || recipes.find(recipe => String(recipe.product?.id) === parameters.get('item'));
if (selectedRecipe) {
  form.elements.keyword.value = selectedRecipe.name;
  showRecipe(selectedRecipe);
} else if (parameters.has('recipe')) {
  selected.append(element('p', '這份配方的詳細資料暫時無法讀取。'));
}
render();
