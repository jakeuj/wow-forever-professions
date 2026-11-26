import { SNAPSHOT_KEYS, marketExpiry, readSnapshot, snapshotExpiry } from './snapshots.mjs';
import { collectAuctionIfNeeded } from './dispatch.mjs';

const headers = { 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex' };
const encoder = new TextEncoder();

function authenticated(request, token) {
  if (!token) return false;
  const provided = encoder.encode(request.headers.get('Authorization') || '');
  const expected = encoder.encode(`Bearer ${token}`);
  return provided.length === expected.length && crypto.subtle.timingSafeEqual(provided, expected);
}

export default {
  async scheduled(controller, env) {
    await collectAuctionIfNeeded(controller, env);
  },

  async fetch(request, env) {
    if (!authenticated(request, env.PUBLISH_TOKEN)) return new Response(null, { status: 401, headers });
    const path = new URL(request.url).pathname;
    if (path === '/battle-net-token.json') {
      if (request.method !== 'PUT') return new Response(null, { status: 405, headers });
      const { accessToken } = await request.json().catch(() => ({})) || {};
      if (typeof accessToken !== 'string' || !/^[A-Za-z0-9._~+\/-]{10,2048}={0,2}$/u.test(accessToken)) {
        return new Response(null, { status: 400, headers });
      }
      await env.SNAPSHOTS.put('battle-net-token', accessToken, { expirationTtl: 3 * 3600 });
      return new Response(null, { status: 204, headers });
    }
    if (path === '/character-exclusions.json') {
      if (request.method !== 'PUT') return new Response(null, { status: 405, headers });
      const ids = await request.json().catch(() => null);
      if (!Array.isArray(ids) || !ids.every(id => Number.isSafeInteger(id) && id > 0)) {
        return new Response(null, { status: 400, headers });
      }
      await env.SNAPSHOTS.put('character-exclusions', JSON.stringify(ids));
      return new Response(null, { status: 204, headers });
    }
    const key = SNAPSHOT_KEYS.get(path);
    if (!key) return new Response(null, { status: 404, headers });
    if (request.method === 'GET') {
      const snapshot = await readSnapshot(env.SNAPSHOTS, key);
      return snapshot ? Response.json(snapshot, { headers }) : new Response(null, { status: 404, headers });
    }
    if (request.method === 'DELETE' && key === 'artisans') {
      await env.SNAPSHOTS.delete(key);
      return new Response(null, { status: 204, headers });
    }
    if (request.method !== 'PUT') return new Response(null, { status: 405, headers });

    let snapshot;
    try {
      snapshot = await request.json();
    } catch {
      return new Response(null, { status: 400, headers });
    }
    const now = Date.now();
    if (key === 'market-depth') {
      const expires = marketExpiry(snapshot);
      const stamp = Date.parse(snapshot?.updatedAt);
      if (!(expires >= now + 60_000) || stamp > now + 60_000) return new Response(null, { status: 400, headers });
      const previous = await env.SNAPSHOTS.get(key, 'json');
      if (!(marketExpiry(previous) > now && Date.parse(previous.updatedAt) >= stamp)) {
        await env.SNAPSHOTS.put(key, JSON.stringify(snapshot), { expiration: Math.floor(expires / 1000) });
      }
      return new Response(null, { status: 204, headers });
    }
    const expires = snapshotExpiry(snapshot);
    const rows = { artisans: snapshot?.artisans, overview: snapshot?.classes, recipes: snapshot?.recipes }[key];
    if (!(expires >= now + 60_000) || Date.parse(snapshot?.fetchedAt) > now + 60_000 || !Array.isArray(rows)) {
      return new Response(null, { status: 400, headers });
    }
    await env.SNAPSHOTS.put(key, JSON.stringify(snapshot), { expiration: Math.floor(expires / 1000) });
    return new Response(null, { status: 204, headers });
  },
};
