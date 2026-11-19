export const professionIds = {
  164: 'blacksmithing', 165: 'leatherworking', 171: 'alchemy', 182: 'herbalism',
  186: 'mining', 197: 'tailoring', 202: 'engineering', 333: 'enchanting', 393: 'skinning',
};

export const classNames = {
  1: '戰士', 2: '聖騎士', 3: '獵人', 4: '盜賊', 5: '牧師', 7: '薩滿', 8: '法師', 9: '術士', 11: '德魯伊',
};

export function characterSlug(value) {
  const slug = value.normalize('NFC').trim().toLowerCase().replace(/\s+/gu, '-');
  return /^[\p{L}\p{M}\p{N}]{1,24}-[\p{L}\p{M}\p{N}]{1,24}$/u.test(slug) ? slug : null;
}

export const characterKey = 'dawnblade.characters.v1';
export const knownRecipeKey = 'dawnblade.known-recipes.v1';
