import { formatTaipei, guildDataOrigin } from '../guild/data-source.mjs';

export const quoteLifetime = 3 * 60 * 60 * 1000;
export const marketName = '台區 PvP 部落';

export function currentDepth(snapshot, now = Date.now()) {
  const timestamp = Date.parse(snapshot?.updatedAt);
  return snapshot?.schema === 1 && snapshot.region === 'tw' && snapshot.ruleset === 1 && snapshot.house === 113
    && timestamp <= now && timestamp + quoteLifetime > now && snapshot.depth
    ? snapshot : null;
}

export async function loadDepth() {
  for (const url of [`${guildDataOrigin}/market-depth.json`, new URL('./scan-depth.json', import.meta.url)]) {
    try {
      const response = await fetch(url, { signal: AbortSignal.timeout(5000) });
      if (response.ok) {
        const snapshot = currentDepth(await response.json());
        if (snapshot) return snapshot;
      }
    } catch {
      // The second source can be used when the current one is unavailable.
    }
  }
  return null;
}

export function quoteLabel(snapshot) {
  return snapshot
    ? `${marketName} · ${snapshot.source === 'scan' ? '完整掃描' : '官方行情'} ${formatTaipei(snapshot.updatedAt, true)}`
    : `${marketName} · 行情待更新`;
}

export function buyFromDepth(snapshot, id, needed, priceLimit = Infinity) {
  const ladder = snapshot?.depth[id];
  let remaining = needed;
  let spent = 0;
  const tiers = [];
  for (const [price, count] of ladder || []) {
    if (!remaining || price >= priceLimit) break;
    const units = Math.min(count, remaining);
    tiers.push({ price, units });
    spent += price * units;
    remaining -= units;
  }
  return { needed, bought: needed - remaining, missing: remaining, spent: Math.ceil(spent), tiers,
    unknown: needed > 0 && (!snapshot || ladder === null) };
}

export function money(copper) {
  const whole = Math.round(copper);
  const amount = Math.abs(whole);
  return `${whole < 0 ? '−' : ''}${Math.floor(amount / 10000).toLocaleString('zh-TW')}金 ${Math.floor(amount / 100) % 100}銀 ${amount % 100}銅`;
}

export async function loadItems() {
  const response = await fetch(new URL('./data.json', import.meta.url));
  if (!response.ok) throw new Error('物品資料暫時無法讀取');
  const { fields, items } = await response.json();
  const id = fields.indexOf('id');
  const name = fields.indexOf('name');
  return new Map(items.map(row => [row[id], row[name]]));
}
