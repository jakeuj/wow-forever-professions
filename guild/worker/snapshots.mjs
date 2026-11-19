export const SNAPSHOT_KEYS = new Map([
  ['/overview.json', 'overview'],
  ['/artisans.json', 'artisans'],
  ['/market-depth.json', 'market-depth'],
  ['/recipes.json', 'recipes'],
]);

export const MARKET_LIFETIME = 3 * 60 * 60 * 1000;

export function marketExpiry(snapshot) {
  const stamp = Date.parse(snapshot?.updatedAt);
  return snapshot?.schema === 1 && snapshot.region === 'tw' && snapshot.ruleset === 1 && snapshot.house === 113
    && snapshot.source === 'official' && snapshot.depth && Object.keys(snapshot.depth).length
    ? stamp + MARKET_LIFETIME : NaN;
}

export const SNAPSHOT_LIFETIME = 7 * 24 * 60 * 60 * 1000;

export function snapshotExpiry(snapshot) {
  const fetched = Date.parse(snapshot?.fetchedAt);
  const expires = Date.parse(snapshot?.expiresAt);
  return snapshot?.schema === 1 && expires > fetched && expires - fetched <= SNAPSHOT_LIFETIME ? expires : NaN;
}

export async function readSnapshot(kv, key, now = Date.now()) {
  const snapshot = await kv.get(key, 'json');
  return snapshotExpiry(snapshot) > now ? snapshot : null;
}
