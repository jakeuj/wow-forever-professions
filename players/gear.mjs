import { guildDataOrigin, loadGuildSnapshot } from '../guild/data-source.mjs';
import { loadItems } from '../market/quotes.mjs';
import { element, link, table } from '../market/tools.mjs';

const drops = {
  5191: ['殘酷倒鉤', '死亡礦坑', 'deadmines', 'MAIN_HAND'],
  5193: ['兄弟會斗篷', '死亡礦坑', 'deadmines', 'BACK'],
  6449: ['發光的蜥蜴披風', '哀嚎洞穴', 'wailing-caverns', 'BACK'],
};
const slots = {
  HEAD: '頭部', NECK: '頸部', SHOULDER: '肩部', BACK: '背部', CHEST: '胸部', WRIST: '手腕',
  HANDS: '手部', WAIST: '腰部', LEGS: '腿部', FEET: '腳部', FINGER_1: '戒指一', FINGER_2: '戒指二',
  TRINKET_1: '飾品一', TRINKET_2: '飾品二', MAIN_HAND: '主手', OFF_HAND: '副手', RANGED: '遠程',
};
const compatible = {
  CHEST: ['CHEST', 'ROBE'], FINGER_1: ['FINGER'], FINGER_2: ['FINGER'], TRINKET_1: ['TRINKET'], TRINKET_2: ['TRINKET'],
  MAIN_HAND: ['WEAPONMAINHAND', 'TWOHWEAPON', 'WEAPON', 'MAIN_HAND'],
  OFF_HAND: ['WEAPONOFFHAND', 'HOLDABLE', 'SHIELD', 'WEAPON', 'OFF_HAND'],
  RANGED: ['RANGED', 'RANGEDRIGHT', 'THROWN', 'RELIC'],
};
const enchantSlots = {
  HEAD: /頭部/u, SHOULDER: /肩部/u, BACK: /披風/u, CHEST: /胸甲/u, WRIST: /護腕/u,
  HANDS: /手套/u, LEGS: /腿部/u, FEET: /靴子/u, MAIN_HAND: /武器/u, OFF_HAND: /盾牌|武器/u, FINGER_1: /戒指/u, FINGER_2: /戒指/u,
};
const statNames = {
  STRENGTH: '力量', AGILITY: '敏捷', STAMINA: '耐力', INTELLECT: '智力', SPIRIT: '精神',
  CRIT_RATING: '致命一擊', HASTE_RATING: '加速', ATTACK_POWER: '攻擊強度', SPELL_POWER: '法術能量',
};
const verifiedEnchants = {
  '附魔護腕-強效智力': ['智力 +7', 20008],
  '附魔護腕-初級精神': ['精神 +3', 7766],
  '附魔靴子-加速': ['移動速度 +8%', 1328948],
};

function enchantStats(text) {
  const attributes = {};
  for (const match of text.matchAll(/(力量|敏捷|耐力|智力|精神|護甲|移動速度)\s*\+\s*(\d+)(%?)|\+\s*(\d+)(%?)\s*(力量|敏捷|耐力|智力|精神|護甲|移動速度)/gu)) {
    const [, stat, amount, unit, prefix, prefixUnit, suffix] = match;
    attributes[stat || suffix] = { value: Number(amount || prefix), unit: unit || prefixUnit || '' };
  }
  return attributes;
}

export function slotLabel(item) {
  return slots[item.slot] || item.slotName || item.slot || '裝備';
}

export function gearComparison(profile) {
  const box = element('section');
  box.append(element('h3', '裝備升級比較'));
  const note = element('p', '選擇已穿戴的部位，再輸入候選物品名稱或 ID。');
  const form = element('form');
  form.className = 'tool-form';
  const slotLabel = element('label', '比較部位');
  const slot = element('select');
  for (const [index, item] of profile.equipment.entries()) slot.add(new Option(slots[item.slot] || item.slotName, index));
  slotLabel.append(slot);
  const itemLabel = element('label', '候選裝備');
  const item = element('input');
  item.required = true;
  item.setAttribute('list', 'gear-options');
  const options = element('datalist');
  options.id = 'gear-options';
  itemLabel.append(item, options);
  const enchantLabel = element('label', '候選附魔');
  const enchant = element('select');
  enchantLabel.append(enchant);
  const submit = element('button', '比較');
  submit.className = 'button-compact';
  form.append(slotLabel, itemLabel, enchantLabel, submit);
  const output = element('div');
  output.setAttribute('aria-live', 'polite');
  box.append(note, form, output);
  let recipes = [];
  let names = new Map();
  let request = 0;
  const update = () => {
    const current = profile.equipment[Number(slot.value)];
    const allowed = enchantSlots[current.slot];
    enchant.replaceChildren(new Option('保留或比較裝備本身', ''), ...recipes
      .filter(recipe => recipe.profession === 333 && allowed?.test(recipe.name))
      .map(recipe => new Option(recipe.name, recipe.id)));
    const suggestions = Object.entries(drops).filter(([, row]) => row[3] === current.slot);
    options.replaceChildren(...suggestions.map(([id, row]) => new Option(`${row[0]} · ${id}`)));
  };
  Promise.all([loadItems().catch(() => new Map()), loadGuildSnapshot('recipes').catch(() => null)]).then(([items, catalog]) => {
    names = items;
    recipes = catalog?.recipes || [];
    update();
  });
  slot.addEventListener('change', () => { request++; output.replaceChildren(); update(); });
  update();
  form.addEventListener('submit', async event => {
    event.preventDefault();
    const lookup = ++request;
    const current = profile.equipment[Number(slot.value)];
    const input = item.value.trim();
    const id = input.match(/(?:^| · )(\d{1,9})$/u)?.[1] ||
      [...names].find(([, name]) => name === input)?.[0] || Object.keys(drops).find(id => drops[id][0] === input);
    if (!id) {
      output.replaceChildren(element('p', '請輸入拍賣行情中的完整名稱或物品 ID。'));
      return;
    }
    const candidateEnchant = recipes.find(recipe => String(recipe.id) === enchant.value);
    output.replaceChildren(element('p', '讀取候選裝備…'));
    const candidate = await fetch(`${guildDataOrigin}/items/${id}.json`, { signal: AbortSignal.timeout(9000) })
      .then(response => response.ok ? response.json() : null).catch(() => null);
    if (lookup !== request) return;
    const allowed = compatible[current.slot] || [current.slot];
    const source = drops[id];
    if (candidate?.slot && !allowed.includes(candidate.slot)) {
      output.replaceChildren(element('p', `候選裝備的部位為${candidate.slotName || candidate.slot}。請選擇相同部位。`));
      return;
    }
    const title = candidate?.name || source?.[0] || names.get(Number(id)) || `物品 ${id}`;
    output.replaceChildren(element('h4', `${current.name} → ${title}`));
    if (candidate?.requiredLevel > profile.level) output.append(element('p', `候選裝備需要等級 ${candidate.requiredLevel}。`));
    const entries = Object.keys({ ...current.stats, ...candidate?.stats });
    if (candidate && entries.length) output.append(table(['屬性', '目前', '候選', '差異'], entries.map(key => {
      const original = current.stats[key] || 0;
      const next = candidate.stats[key] || 0;
      const delta = Math.round((next - original) * 100) / 100;
      return [statNames[key] || key, original, next, delta > 0 ? `+${delta}` : delta];
    })));
    else output.append(element('p', '此裝備的屬性暫時無法比較。'));
    const access = element('div');
    access.className = 'tool-actions';
    if (source) access.append(link(`掉落 · ${source[1]}`, `https://wowf.io/tw/dungeons/${source[2]}`));
    if (candidate?.binding !== 'ON_ACQUIRE') access.append(link('查拍賣掛單', `../market/?item=${id}#bulk`));
    if (recipes.some(recipe => Number(recipe.product?.id) === Number(id))) {
      access.append(link('配方與公會代工', `../professions/recipes/?item=${id}`));
    }
    access.append(link('永恆物品資料', `https://www.wowhead.com/forever/tw/item=${id}`));
    output.append(access);
    if (candidate?.source) output.append(element('p', candidate.source));
    if (candidateEnchant) {
      const row = element('p', `目前附魔 · ${current.enchants.join('、') || '無紀錄'} ｜ 候選 · `);
      row.append(link(candidateEnchant.name, `../professions/recipes/?recipe=${candidateEnchant.id}`));
      output.append(row);
      const reference = verifiedEnchants[candidateEnchant.name.replace(/\s+/gu, '')];
      const effect = candidateEnchant.effect || reference?.[0];
      if (effect) output.append(element('p', effect));
      if (reference) output.append(link('永恆附魔效果', `https://wowf.io/tw/recipes/enchanting/${reference[1]}`));
      const before = enchantStats(current.enchants.join('、'));
      const after = enchantStats(reference?.[0] || effect || '');
      for (const [attribute, next] of Object.entries(after)) {
        const previous = before[attribute];
        if (previous?.unit === next.unit || current.enchants.length === 0) {
          const difference = next.value - (previous?.value || 0);
          output.append(element('p', `附魔差異 · ${attribute} ${difference >= 0 ? '+' : ''}${difference}${next.unit}`));
        }
      }
    }
  });
  return box;
}
