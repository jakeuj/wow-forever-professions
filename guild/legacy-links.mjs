const plannerAnchors = new Set(['#plans', '#legacy', '#principles', '#sources']);
const plannerFields = ['plan', 'stage', 'route'];

export function legacyPlannerUrl(homeUrl) {
  const current = new URL(homeUrl);
  const params = new URLSearchParams(current.hash.slice(1));
  if (!plannerAnchors.has(current.hash) && !plannerFields.some(field => params.has(field))) {
    return null;
  }

  const planner = new URL('./professions/', current);
  planner.search = current.search;
  planner.hash = current.hash;
  return planner.href;
}
