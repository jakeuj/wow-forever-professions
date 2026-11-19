export const SNAPSHOT_KEYS = new Map([
  ['/overview.json', 'overview'],
  ['/artisans.json', 'artisans'],
]);

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
