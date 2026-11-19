const normalize = value => value.normalize('NFKC').trim().toLocaleLowerCase('zh-TW');

export function buildRecipeIndex(snapshot) {
  const groups = new Map();
  for (const artisan of snapshot.artisans) {
    for (const { id: professionId, skill, maxSkill, recipeIds } of artisan.professions) {
      for (const id of recipeIds) {
        const recipe = snapshot.recipes[id];
        if (!recipe) continue;
        const key = `${professionId}:${id}`;
        if (!groups.has(key)) groups.set(key, { id, professionId, ...recipe, artisans: [] });
      groups.get(key).artisans.push({ name: artisan.name, skill, maxSkill, slug: artisan.slug });
      }
    }
  }
  for (const group of groups.values()) {
    group.artisans.sort((a, b) => b.skill - a.skill || a.name.localeCompare(b.name, 'zh-TW'));
  }
  return [...groups.values()].sort((a, b) => a.name.localeCompare(b.name, 'zh-TW') || a.id - b.id);
}

export function searchRecipes(groups, query, professionId) {
  const keyword = normalize(query);
  if (!keyword && !professionId) return [];
  return groups.filter(recipe => (
    (!professionId || String(recipe.professionId) === professionId) &&
    (!keyword || normalize(recipe.name).includes(keyword) || normalize(recipe.originalName || '').includes(keyword))
  ));
}
