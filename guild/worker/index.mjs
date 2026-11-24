import { SNAPSHOT_KEYS, marketExpiry, readSnapshot } from './snapshots.mjs';
import { armoryResponse } from './armory.mjs';
import { mcpResponse } from './mcp.mjs';

const headers = {
  'Access-Control-Allow-Origin': 'https://jakeuj.com',
  'Cache-Control': 'no-store',
  'X-Robots-Tag': 'noindex',
};

export default {
  async fetch(request, env) {
    const pathname = new URL(request.url).pathname;
    if (pathname === '/mcp') return mcpResponse(request, env);
    const lookup = pathname.match(/^\/(characters|items)\/([^/]+)\.json$/u);
    if (lookup) {
      const armoryHeaders = { ...headers, 'X-Dawnblade-Armory': '1', 'Access-Control-Expose-Headers': 'X-Dawnblade-Armory' };
      try { return await armoryResponse(request, env, { kind: lookup[1], value: decodeURIComponent(lookup[2]) }, armoryHeaders); }
      catch { return new Response(null, { status: 400, headers }); }
    }
    const key = SNAPSHOT_KEYS.get(pathname);
    if (!key) return new Response(null, { status: 404, headers });
    if (request.method !== 'GET') {
      return new Response(null, { status: 405, headers: { ...headers, Allow: 'GET' } });
    }
    if (key === 'market-depth') {
      const market = await env.SNAPSHOTS.get(key, 'json');
      return marketExpiry(market) > Date.now()
        ? Response.json(market, { headers })
        : new Response(null, { status: 404, headers });
    }
    const snapshot = await readSnapshot(env.SNAPSHOTS, key);
    if (!snapshot) return new Response(null, { status: 404, headers });

    const { schema, fetchedAt, expiresAt } = snapshot;
    const dates = { schema, fetchedAt, expiresAt };
    if (key === 'recipes') return Response.json({ ...dates, recipes: snapshot.recipes }, { headers });
    if (key === 'overview') {
      const { createdAt, rosterUpdatedAt, characterCount, classes, levels } = snapshot;
      return Response.json({ ...dates, createdAt, rosterUpdatedAt, characterCount, classes, levels }, { headers });
    }
    const { artisans, failedProfiles, professions, recipes } = snapshot;
    const blocked = await env.SNAPSHOTS.get('character-exclusions', 'json');
    return Response.json({
      ...dates, failedProfiles, professions, recipes,
      artisans: artisans.filter(person => !Array.isArray(blocked) || !blocked.includes(person.characterId))
        .map(({ name, slug, level, classId, professions: skills }) => ({
        name, slug, level, classId, professions: skills.map(({ id, skill, maxSkill, recipeIds }) => ({ id, skill, maxSkill, recipeIds })),
      })),
    }, { headers });
  },
};
