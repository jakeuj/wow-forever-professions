export const guildDataOrigin = 'https://dawnblade-guild-data.jakeuj.workers.dev';
const staleAfter = 48 * 60 * 60 * 1000;
const date = new Intl.DateTimeFormat('zh-TW', {
  timeZone: 'Asia/Taipei', year: 'numeric', month: '2-digit', day: '2-digit',
});
const stamp = new Intl.DateTimeFormat('zh-TW', {
  timeZone: 'Asia/Taipei', year: 'numeric', month: '2-digit', day: '2-digit',
  hour: '2-digit', minute: '2-digit', hourCycle: 'h23',
});

export async function loadGuildSnapshot(key) {
  const response = await fetch(`${guildDataOrigin}/${key}.json`, { signal: AbortSignal.timeout(10_000) });
  if (!response.ok) throw new Error(`Guild data HTTP ${response.status}`);
  const data = await response.json();
  if (data.schema !== 1 || !(Date.parse(data.expiresAt) > Date.now())) throw new Error('Guild data expired');
  return data;
}

export function formatTaipei(value, withTime = false) {
  return (withTime ? stamp : date).format(new Date(value));
}

export function watchGuildSnapshot(snapshot, pending, expired) {
  const now = Date.now();
  const untilStale = Math.max(0, Date.parse(snapshot.fetchedAt) + staleAfter - now);
  const untilExpired = Math.max(0, Date.parse(snapshot.expiresAt) - now);
  if (untilStale < untilExpired) {
    if (untilStale === 0) pending();
    else setTimeout(pending, untilStale);
  }
  setTimeout(expired, untilExpired);
}
