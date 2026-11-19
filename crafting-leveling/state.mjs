import { readLocal } from '../market/tools.mjs';

export const levelingKey = 'dawnblade.leveling.v1';

export function levelingPlanKey(profession, characterId = '', legacyName = '') {
  if (characterId) return JSON.stringify([characterId, profession]);
  return legacyName ? `${profession}:${legacyName}` : profession;
}

export function readLevelingPlan(plans, characters, profession, characterId = '', legacyName = '') {
  const key = levelingPlanKey(profession, characterId, legacyName);
  if (Object.hasOwn(plans, key)) return plans[key];
  if (!characterId || !Object.hasOwn(characters, characterId)) return undefined;

  const name = characters[characterId]?.name?.trim().slice(0, 50);
  if (!name || Object.values(characters).filter(person => person?.name?.trim().slice(0, 50) === name).length !== 1) {
    return undefined;
  }
  return plans[levelingPlanKey(profession, '', name)];
}

export function writeLevelingPlan(key, plan) {
  const plans = readLocal(levelingKey, {});
  localStorage.setItem(levelingKey, JSON.stringify({ ...plans, [key]: plan }));
}

export function armoryLevelingPlan(previous, characterName, skill, recipeMap) {
  const { skill: start, maxSkill, recipes } = skill;
  if (!Number.isInteger(start) || start < 1 || !Array.isArray(recipes)
      || recipes.some(row => !Array.isArray(row) || !Number.isSafeInteger(row[0]) || row[0] <= 0)) {
    throw new Error('軍械庫的專業資料不完整。');
  }
  if (start >= 300) throw new Error('這項專業已達練等上限 300。');
  if (![75, 150, 225, 300].includes(maxSkill) || maxSkill < start) {
    throw new Error('這項專業的技能上限超出練等工具支援範圍。');
  }
  if (!recipeMap || typeof recipeMap !== 'object' || Array.isArray(recipeMap)
      || Object.values(recipeMap).some(spell => !Number.isSafeInteger(spell) || spell <= 0)) {
    throw new Error('配方對照暫時無法讀取。');
  }

  const ids = new Set(recipes.map(([id]) => id));
  const known = [...new Set([...ids].filter(id => Object.hasOwn(recipeMap, id)).map(id => recipeMap[id]))];
  return {
    target: [150, 225, 300].find(rank => rank > start),
    ...previous,
    characterName, start, cap: String(maxSkill), known,
    armoryImport: { matched: known.length, skipped: ids.size - known.length },
  };
}
