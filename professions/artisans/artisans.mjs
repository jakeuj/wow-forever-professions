import { formatTaipei, loadGuildSnapshot, watchGuildSnapshot } from '../../guild/data-source.mjs?v=1';
import { buildRecipeIndex, searchRecipes } from './search.mjs?v=1';

const pageSize = 25;
const form = document.querySelector('#artisan-search');
const search = form.elements.recipe;
const profession = form.elements.profession;
const status = document.querySelector('#artisan-status');
const resultCount = document.querySelector('#artisan-count');
const results = document.querySelector('#artisan-results');
const more = document.querySelector('#artisan-more');
const copied = document.querySelector('#artisan-copy-status');

function element(tag, className, text) {
  const node = document.createElement(tag);
  if (className) node.className = className;
  if (text !== undefined) node.textContent = text;
  return node;
}

function artisanRow({ name, skill, maxSkill }) {
  const row = element('li', 'artisan-person');
  const character = element('span', 'artisan-name', name);
  const points = element('span', 'artisan-skill', `技能 ${skill} / ${maxSkill}`);
  const copy = element('button', 'button-compact', '複製名稱');
  copy.type = 'button';
  copy.setAttribute('aria-label', `複製「${name}」的角色名稱`);
  let reset;
  copy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(name);
      copy.textContent = '已複製';
      copied.textContent = `已複製「${name}」`;
    } catch {
      const selection = window.getSelection();
      const range = document.createRange();
      range.selectNodeContents(character);
      selection.removeAllRanges();
      selection.addRange(range);
      copy.textContent = '已選取';
      copied.textContent = '無法自動複製，已選取角色名稱。';
    }
    clearTimeout(reset);
    reset = setTimeout(() => { copy.textContent = '複製名稱'; }, 2400);
  });
  row.append(character, points, copy);
  return row;
}

function recipeRow(recipe, professions, expanded) {
  const row = element('li', 'artisan-recipe');
  const details = element('details');
  details.open = expanded;
  const heading = element('summary');
  heading.append(
    element('strong', 'artisan-recipe-name', recipe.name),
    element('span', 'artisan-recipe-meta', `${professions[recipe.professionId]} · ${recipe.artisans.length} 位工匠`),
  );
  const people = element('ul', 'artisan-people');
  people.append(...recipe.artisans.map(artisanRow));
  details.append(heading, people);
  row.append(details);
  return row;
}

function showUnavailable() {
  form.hidden = true;
  results.replaceChildren();
  more.hidden = true;
  resultCount.textContent = '';
  copied.textContent = '';
  status.textContent = '工匠名冊暫無資料，請稍後再查看。';
}

status.hidden = false;
try {
  const snapshot = await loadGuildSnapshot('artisans');
  const groups = buildRecipeIndex(snapshot);
  const time = formatTaipei(snapshot.fetchedAt, true);
  const partial = snapshot.failedProfiles ? '。部分角色專業查詢暫時失敗' : '';
  const summary = `${snapshot.artisans.length.toLocaleString('zh-TW')} 位工匠 · 資料更新 ${time}（台灣時間）${partial}`;
  status.textContent = summary;
  watchGuildSnapshot(snapshot, () => { status.textContent = `${summary} · 待更新`; }, showUnavailable);

  for (const [id, name] of Object.entries(snapshot.professions)) profession.add(new Option(name, id));
  let matches = [];
  let displayed = 0;

  function showMore() {
    const batch = matches.slice(displayed, displayed + pageSize);
    results.append(...batch.map(recipe => recipeRow(recipe, snapshot.professions, matches.length === 1)));
    displayed += batch.length;
    more.hidden = displayed === matches.length;
    if (matches.length) resultCount.textContent = `共 ${matches.length.toLocaleString('zh-TW')} 項配方，顯示 ${displayed.toLocaleString('zh-TW')} 項。`;
  }

  function render() {
    results.replaceChildren();
    copied.textContent = '';
    displayed = 0;
    matches = searchRecipes(groups, search.value, profession.value);
    resultCount.textContent = search.value.trim() || profession.value
      ? '找不到符合的配方。可以換個名稱，或選擇全部專業。'
      : '輸入配方名稱，或選擇一項製造專業。';
    showMore();
  }

  if (groups.length) {
    form.hidden = false;
    form.addEventListener('submit', event => { event.preventDefault(); render(); });
    search.addEventListener('input', render);
    profession.addEventListener('change', render);
    more.addEventListener('click', showMore);
    render();
  } else {
    resultCount.textContent = '本次更新暫無可查詢的配方。';
  }
} catch {
  showUnavailable();
}
