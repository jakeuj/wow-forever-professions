import { SNAPSHOT_KEYS, readSnapshot, snapshotExpiry } from './snapshots.mjs';

const headers = { 'Cache-Control': 'no-store', 'X-Robots-Tag': 'noindex' };
const encoder = new TextEncoder();

function authenticated(request, token) {
  if (!token) return false;
  const provided = encoder.encode(request.headers.get('Authorization') || '');
  const expected = encoder.encode(`Bearer ${token}`);
  return provided.length === expected.length && crypto.subtle.timingSafeEqual(provided, expected);
}

export default {
  async fetch(request, env) {
    if (!authenticated(request, env.PUBLISH_TOKEN)) return new Response(null, { status: 401, headers });
    const key = SNAPSHOT_KEYS.get(new URL(request.url).pathname);
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
    const expires = snapshotExpiry(snapshot);
    const rows = key === 'artisans' ? snapshot?.artisans : snapshot?.classes;
    if (!(expires >= now + 60_000) || Date.parse(snapshot?.fetchedAt) > now + 60_000 || !Array.isArray(rows)) {
      return new Response(null, { status: 400, headers });
    }
    await env.SNAPSHOTS.put(key, JSON.stringify(snapshot), { expiration: Math.floor(expires / 1000) });
    return new Response(null, { status: 204, headers });
  },
};
