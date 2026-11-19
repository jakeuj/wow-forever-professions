import { SNAPSHOT_KEYS, readSnapshot } from './snapshots.mjs';

const headers = {
  'Access-Control-Allow-Origin': 'https://jakeuj.com',
  'Cache-Control': 'no-store',
  'X-Robots-Tag': 'noindex',
};

export default {
  async fetch(request, env) {
    const key = SNAPSHOT_KEYS.get(new URL(request.url).pathname);
    if (!key) return new Response(null, { status: 404, headers });
    if (request.method !== 'GET') {
      return new Response(null, { status: 405, headers: { ...headers, Allow: 'GET' } });
    }
    const snapshot = await readSnapshot(env.SNAPSHOTS, key);
    if (!snapshot) return new Response(null, { status: 404, headers });

    const { schema, fetchedAt, expiresAt } = snapshot;
    const dates = { schema, fetchedAt, expiresAt };
    if (key === 'overview') {
      const { createdAt, rosterUpdatedAt, characterCount, classes, levels } = snapshot;
      return Response.json({ ...dates, createdAt, rosterUpdatedAt, characterCount, classes, levels }, { headers });
    }
    const { artisans, failedProfiles, professions, recipes } = snapshot;
    return Response.json({
      ...dates, failedProfiles, professions, recipes,
      artisans: artisans.map(({ name, professions: skills }) => ({
        name, professions: skills.map(({ id, skill, maxSkill, recipeIds }) => ({ id, skill, maxSkill, recipeIds })),
      })),
    }, { headers });
  },
};
