// The Publisher's cron trigger (wrangler.publish.toml) starts the auction collector.
// GitHub ran the workflow's own hourly schedule only 3-4 times a day (2026-11-19 to
// 11-23), but starts a workflow_dispatch within seconds, so the Worker asks for one.
// GITHUB_DISPATCH_TOKEN is a fine-grained token for this repository with
// Actions: Read and write; a failed request throws, so it shows up as an error
// in the Worker's cron events.
export const AUCTION_DISPATCH_URL =
  'https://api.github.com/repos/jakeuj/wow-forever-professions/actions/workflows/auction-collect.yml/dispatches';

export async function dispatchAuctionCollect(env, fetcher = fetch) {
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
    body: JSON.stringify({ ref: 'main' }),
  });
  if (!response.ok) {
    const detail = (await response.text().catch(() => '')).slice(0, 200);
    throw new Error(`auction-collect.yml dispatch failed: HTTP ${response.status} ${detail}`);
  }
}
