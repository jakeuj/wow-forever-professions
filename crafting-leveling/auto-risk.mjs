export function skillGain(recipe, skill) {
  if (skill < (recipe.orange ?? recipe.learn) || skill < recipe.learn || skill >= recipe.grey) return 0;
  if (skill < recipe.yellow) return 1;
  if (skill < recipe.green) return 1 - .5 * (skill - recipe.yellow) / (recipe.green - recipe.yellow);
  return Math.max(.05, .5 - .45 * (skill - recipe.green) / Math.max(1, recipe.grey - recipe.green));
}

export function initialRisk(start, target) {
  return { min: start, max: start, mass: Float64Array.from({ length: target + 1 }, (_, skill) => Number(skill === start)) };
}

export function probabilityAtLeast(risk, skill) {
  let probability = 0;
  for (let level = Math.max(risk.min, skill); level <= risk.max; level++) probability += risk.mass[level];
  return Math.min(1, probability);
}

export function requireSkill(risk, skill) {
  if (skill <= risk.min) return risk;
  const mass = risk.mass.slice();
  mass.fill(0, risk.min, Math.min(skill, mass.length));
  return { min: Math.max(risk.min, skill), max: risk.max, mass };
}

export function nextCraft(risk, recipe, cap) {
  const mass = new Float64Array(risk.mass.length);
  const ceiling = Math.min(cap, mass.length - 1);
  let min = risk.max + 1;
  let max = 0;
  for (let skill = risk.min; skill <= risk.max; skill++) {
    const weight = risk.mass[skill];
    if (!weight) continue;
    const gain = skill < ceiling ? skillGain(recipe, skill) : 0;
    if (gain < 1) {
      mass[skill] += weight * (1 - gain);
      min = Math.min(min, skill);
      max = Math.max(max, skill);
    }
    if (gain > 0) {
      mass[skill + 1] += weight * gain;
      min = Math.min(min, skill + 1);
      max = Math.max(max, skill + 1);
    }
  }
  return { min, max, mass };
}
