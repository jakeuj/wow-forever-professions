import { formatTaipei, guildDataOrigin, loadGuildSnapshot } from '../guild/data-source.mjs';
import { copyButton, element, link, readLocal, saveLocal, table } from '../market/tools.mjs';
import { countPoints, crafting, normalizeProgress, professions as professionList } from '../professions/data.mjs';
import { gearComparison, slotLabel } from './gear.mjs';
import { characterKey, characterSlug, classNames, knownRecipeKey, professionIds } from './model.mjs';

const search = document.querySelector('#armory-search');
const status = document.querySelector('#armory-status');
const result = document.querySelector('#armory-result');
const favoritesList = document.querySelector('#armory-favorites');
const editor = document.querySelector('#character-editor');
const characterStatus = document.querySelector('#character-status');
const summary = document.querySelector('#character-progress');
const cards = document.querySelector('#character-list');
const favKey = 'dawnblade.armory-favorites.v1';
const favorites = readLocal(favKey, {});
const saved = readLocal(characterKey, {});
const namesBySlug = Object.fromEntries(professionList.map(profession => [profession.id, profession.name]));
const milestonesKey = 'wow-forever-professions:milestones:v1';
let sequence = 0;
let editing = '';

function renderFavorites() {
  favoritesList.replaceChildren(...Object.entries(favorites).map(([slug, name]) =>
    link(name, `?character=${encodeURIComponent(slug)}`)));
}

function renderCharacters() {
  const progress = normalizeProgress(readLocal(milestonesKey, {}));
  const assigned = new Set();
  cards.replaceChildren();
  for (const [id, person] of Object.entries(saved)) {
    const card = element('article');
    card.append(element('h3', person.name));
    if (person.slug) card.append(link('查看軍械庫', `?character=${encodeURIComponent(person.slug)}`));
    for (const skill of person.skills) {
      assigned.add(skill.slug);
      const next = [150, 225, 300].find(rank => rank > skill.skill);
      if (crafting.some(profession => profession.id === skill.slug)) {
        const stage = [150, 225, 300].filter(rank => rank <= skill.skill).length;
        progress[skill.slug] = Math.max(progress[skill.slug] || 0, stage);
      }
      const row = element('p', `${namesBySlug[skill.slug]} · ${skill.skill}`);
      if (next && crafting.some(profession => profession.id === skill.slug)) {
        const params = new URLSearchParams({ profession: skill.slug, from: skill.skill || 1, target: next, character: person.name });
        row.append(' ', link(`試算至 ${next}`, `../crafting-leveling/?${params}#calculator`));
      }
      card.append(row);
    }
    const actions = element('div');
    actions.className = 'tool-actions';
    const edit = element('button', '編輯');
    const remove = element('button', '移除');
    edit.className = remove.className = 'button-compact';
    edit.addEventListener('click', () => {
      editing = id;
      editor.elements.name.value = person.name;
      editor.elements.first.value = person.skills[0]?.slug || '';
      editor.elements.second.value = person.skills[1]?.slug || '';
      editor.elements.firstSkill.value = person.skills[0]?.skill || 1;
      editor.elements.secondSkill.value = person.skills[1]?.skill || 1;
      editor.elements.name.focus();
    });
    remove.addEventListener('click', () => {
      delete saved[id];
      saveLocal(characterKey, saved);
      if (editing === id) { editing = ''; editor.reset(); }
      renderCharacters();
    });
    actions.append(edit, remove);
    card.append(actions);
    cards.append(card);
  }
  const missing = professionList.filter(profession => !assigned.has(profession.id));
  summary.replaceChildren(
    element('p', `製造傳承進度 ${countPoints(progress)}／18 點`),
    element('p', missing.length ? `尚未分配 · ${missing.map(profession => profession.name).join('、')}` : '九項主要專業皆已分配。'),
    table(['製造專業', '已達里程碑'], crafting.map(profession => [profession.name, [0, 150, 225, 300][progress[profession.id]] || '尚未達 150'])),
  );
}

for (const input of [editor.elements.first, editor.elements.second]) {
  input.add(new Option('未指定', ''));
  for (const profession of professionList) input.add(new Option(profession.name, profession.id));
}
editor.addEventListener('submit', event => {
  event.preventDefault();
  const name = editor.elements.name.value.trim();
  const skills = [...new Map([
    [editor.elements.first.value, editor.elements.firstSkill.valueAsNumber],
    [editor.elements.second.value, editor.elements.secondSkill.valueAsNumber],
  ])].filter(([slug]) => slug).map(([slug, skill]) => ({ slug, skill }));
  if (!name) return;
  const id = editing || `manual:${name.toLowerCase()}`;
  saved[id] = { ...saved[id], name, skills };
  saveLocal(characterKey, saved);
  editing = '';
  editor.reset();
  characterStatus.textContent = `已儲存 ${name}。`;
  renderCharacters();
});

function importCharacter(profile) {
  const skills = profile.professions.filter(skill => professionIds[skill.id])
    .map(skill => ({ slug: professionIds[skill.id], skill: skill.skill }));
  saved[profile.slug] = { slug: profile.slug, name: profile.name, skills };
  const known = new Set(readLocal(knownRecipeKey, []));
  for (const skill of profile.professions) for (const [id] of skill.recipes) known.add(id);
  saveLocal(knownRecipeKey, [...known]);
  saveLocal(characterKey, saved);
  characterStatus.textContent = `已帶入 ${profile.name} 的專業與已學配方。`;
  renderCharacters();
}

function renderProfile(profile) {
  result.replaceChildren(element('h2', profile.name));
  const detail = [profile.level ? `${profile.level} 級` : '', profile.className, profile.guild].filter(Boolean);
  if (detail.length) result.append(element('p', detail.join(' · ')));
  if (profile.fetchedAt) result.append(element('p', `資料更新 ${formatTaipei(profile.fetchedAt, true)}（台灣時間）`));
  if (profile.missing?.length) result.append(element('p', '部分裝備、天賦或專業資料暫時無法讀取。'));
  const actions = element('div');
  actions.className = 'tool-actions';
  const favorite = element('button', favorites[profile.slug] ? '取消收藏' : '收藏角色');
  favorite.className = 'button-compact';
  favorite.addEventListener('click', () => {
    if (favorites[profile.slug]) delete favorites[profile.slug];
    else favorites[profile.slug] = profile.name;
    favorite.textContent = favorites[profile.slug] ? '取消收藏' : '收藏角色';
    saveLocal(favKey, favorites);
    renderFavorites();
  });
  actions.append(favorite, copyButton('複製角色連結', () => location.href));
  if (profile.professions.length) {
    const include = element('button', '加入我的角色');
    include.className = 'button-compact';
    include.addEventListener('click', () => {
      importCharacter(profile);
      document.querySelector('#my-characters').scrollIntoView();
    });
    actions.append(include);
  }
  result.append(actions, element('h3', '專業與配方'));
  if (!profile.professions.length) result.append(element('p', '目前沒有可顯示的專業。'));
  for (const skill of profile.professions) {
    const details = element('details');
    details.append(element('summary', `${namesBySlug[professionIds[skill.id]] || skill.name || skill.id} · ${skill.skill}／${skill.maxSkill} · ${skill.recipes.length} 項配方`));
    const recipes = element('ul');
    for (const [id, name] of skill.recipes) {
      const row = element('li');
      row.append(link(name || `配方 ${id}`, `../professions/recipes/?recipe=${id}`));
      recipes.append(row);
    }
    details.append(recipes);
    result.append(details);
  }
  if (profile.equipment.length) {
    result.append(element('h3', '裝備'), table(['部位', '物品', '附魔'], profile.equipment.map(item => [
      slotLabel(item), link(item.name || `物品 ${item.id}`, `https://www.wowhead.com/forever/tw/item=${item.id}`),
      item.enchants.join('、') || '—',
    ])), gearComparison(profile));
  }
  if (profile.talents.length) {
    result.append(element('h3', '天賦'));
    for (const spec of profile.talents) {
      const specRows = spec.loadouts.find(loadout => loadout.active)?.talents || spec.talents;
      const details = element('details');
      details.append(element('summary', `${spec.name || '天賦配置'}${spec.points !== undefined ? ` · ${spec.points} 點` : ''}`),
        element('p', specRows.map(talent => `${talent.name} ${talent.rank}`).join('、') || '暫無已配置天賦。'));
      result.append(details);
    }
  }
}

async function lookup(slug) {
  const id = ++sequence;
  result.replaceChildren();
  status.textContent = '查詢角色…';
  const profileResponse = await fetch(`${guildDataOrigin}/characters/${encodeURIComponent(slug)}.json`, {
    signal: AbortSignal.timeout(18000),
  }).catch(() => null);
  if (id !== sequence) return;
  if (profileResponse?.ok) {
    const profile = await profileResponse.json().catch(() => null);
    if (id !== sequence) return;
    if (profile) {
      status.textContent = '';
      renderProfile(profile);
      return;
    }
  }
  if (profileResponse?.status === 429) {
    status.textContent = '查詢次數較多，請稍後重試。';
    return;
  }
  if (profileResponse?.status === 404 && profileResponse.headers.get('X-Dawnblade-Armory') === '1') {
    status.textContent = '目前查不到這個角色。請確認名字、姓氏以及角色是否已達 10 級並登出。';
    return;
  }
  const roster = await loadGuildSnapshot('artisans').catch(() => null);
  if (id !== sequence) return;
  const person = roster?.artisans.find(person => (person.slug || characterSlug(person.name)) === slug);
  if (person) {
    status.textContent = '顯示公會工匠快照。';
    renderProfile({
      ...person, slug, guild: '黎明之劍', className: classNames[person.classId], fetchedAt: roster.fetchedAt,
      equipment: [], talents: [], professions: person.professions.map(skill => ({
        ...skill, name: roster.professions[skill.id], recipes: skill.recipeIds.map(recipeId => [recipeId, roster.recipes[recipeId]?.name]),
      })),
    });
  } else status.textContent = '目前查不到角色，或台服查詢暫時無法使用。';
}

search.addEventListener('submit', event => {
  event.preventDefault();
  const slug = characterSlug(search.elements.character.value);
  if (!slug) {
    status.textContent = '請輸入完整名字與姓氏。';
    return;
  }
  const url = new URL(location.href);
  url.searchParams.set('character', slug);
  history.replaceState(null, '', url);
  lookup(slug);
});
const initial = new URLSearchParams(location.search).get('character');
if (initial) {
  search.elements.character.value = initial.replace('-', ' ');
  search.requestSubmit();
}
renderFavorites();
renderCharacters();
