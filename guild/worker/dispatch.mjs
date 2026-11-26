import { marketExpiry } from './snapshots.mjs';

// The Publisher's cron trigger starts the collector if its target hour is missing.
// GITHUB_DISPATCH_TOKEN is a fine-grained token for this repository with
// Actions: Read and write; a failed request throws, so it shows up as an error
// in the Worker's cron events.
export const AUCTION_DISPATCH_URL =
  'https://api.github.com/repos/jakeuj/wow-forever-professions/actions/workflows/auction-collect.yml/dispatches';

export async function dispatchAuctionCollect(env, fetcher = fetch, { forceRefresh = false } = {}) {
  if (!env.GITHUB_DISPATCH_TOKEN) throw new Error('GITHUB_DISPATCH_TOKEN is not set; auction-collect.yml was not started');
  const response = await fetcher(AUCTION_DISPATCH_URL, {
    method: 'POST',
    headers: {
      Accept: 'application/vnd.github+json',
      Authorization: `Bearer ${env.GITHUB_DISPATCH_TOKEN}`,
      'Content-Type': 'application/json',
      'User-Agent': 'dawnblade-guild-publish',
      'X-GitHub-Api-Version': '2022-11-28',
    },
    body: JSON.stringify({ ref: 'main', ...(forceRefresh ? { inputs: { force_refresh: 'true' } } : {}) }),
  });
  if (!response.ok) {
    const detail = (await response.text().catch(() => '')).slice(0, 200);
    throw new Error(`auction-collect.yml dispatch failed: HTTP ${response.status} ${detail}`);
  }
}

export async function collectAuctionIfNeeded(controller, env, { fetcher = fetch, now = Date.now() } = {}) {
  const scheduled = new Date(controller.scheduledTime);
  const hoursAgo = scheduled.getUTCMinutes() === 12 ? 1 : 0;
  const hour = 3_600_000;
  const target = (Math.floor(controller.scheduledTime / hour) - hoursAgo) * hour;
  const snapshot = await env.SNAPSHOTS.get('market-depth', 'json');
  const valid = marketExpiry(snapshot) > now;
  const updatedAt = snapshot?.updatedAt ?? null;
  const details = { scheduledAt: scheduled.toISOString(), targetHour: new Date(target).toISOString(), updatedAt };
  if (valid && Date.parse(updatedAt) >= target) {
    console.info('Auction snapshot already available', details);
    return;
  }
  await dispatchAuctionCollect(env, fetcher, { forceRefresh: !valid });
  console.info('Auction collection dispatched', { ...details, forceRefresh: !valid });
}
