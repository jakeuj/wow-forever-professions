const MAX_TREND_AGE_MS = 3 * 3600e3;

const shortDay = iso => iso ? `${Number(iso.slice(5, 7))}/${Number(iso.slice(8, 10))}` : '';

// API hours are hours since the Unix epoch (UTC). The display uses Taiwan time.
function hourLabel(hour) {
  const date = new Date((hour + 8) * 3600e3);
  return `${date.getUTCMonth() + 1}/${date.getUTCDate()} ${date.getUTCHours()} 時`;
}

// The price at a change point persists up to the next point, including stock gaps.
export function priceAt(series, hour) {
  let value;
  for (const [time, price] of series) {
    if (time > hour) break;
    value = price;
  }
  return value;
}

export function marketItems(scan, official) {
  const scanTime = Date.parse(scan.snapshotAt || scan.savedAt || scan.scanStartedAt || scan.latestDay);
  const officialTime = Date.parse(official?.updatedAt);
  const auctions = official?.hours?.length && officialTime >= scanTime - MAX_TREND_AGE_MS ? official : null;
  const apiHour = auctions ? auctions.hours[auctions.hours.length - 1] : null;
  const apiNewer = Boolean(auctions && officialTime > scanTime);
  const items = scan.items.map(row => {
    const item = Object.fromEntries(scan.fields.map((field, index) => [field, row[index]]));
    const entry = auctions && auctions.items[item.id];
    if (!entry || !apiNewer) {
      // A newer snapshot lists the whole house, so an absent item is now out of stock.
      const listed = item.day === scan.latestDay && item.count !== 0 && !apiNewer;
      const day = shortDay(item.day);
      return {
        ...item, now: item.price, listed, base: item.prev, baseLabel: shortDay(item.prevDay),
        units: listed ? item.count : null,
        when: apiNewer ? `${day} 掃描看到，官方已沒貨` : listed ? `${day} 掃描` : `${day} 掃描看到`,
        ...(entry ? { series: entry[1] } : {}),
      };
    }

    const [count, series] = entry;
    const last = series[series.length - 1];
    const lastPrice = [...series].reverse().find(([, price]) => price != null);
    const listed = last[1] != null;
    return {
      ...item, series, listed, now: listed ? last[1] : lastPrice && lastPrice[1],
      units: listed ? count : null,
      when: listed ? `官方 ${auctions.updatedAt.slice(11, 16)}` : `${hourLabel(last[0])}起沒貨`,
      base: listed ? priceAt(series, apiHour - 24) : null,
      baseLabel: '24 小時前',
    };
  });
  return { items, apiHour, apiNewer, apiUpdatedAt: auctions?.updatedAt ?? null };
}

export function change(item) {
  return item.base && item.now != null ? (item.now - item.base) / item.base : null;
}

const sorters = {
  quality: (a, b) => (b.quality ?? -1) - (a.quality ?? -1) || (b.now ?? 0) - (a.now ?? 0),
  'price-desc': (a, b) => (b.now ?? 0) - (a.now ?? 0),
  'price-asc': (a, b) => (a.now ?? Infinity) - (b.now ?? Infinity),
  drop: (a, b) => (change(a) ?? Infinity) - (change(b) ?? Infinity),
  count: (a, b) => (b.units ?? 0) - (a.units ?? 0),
  name: (a, b) => a.name.localeCompare(b.name, 'zh-Hant-TW'),
};

export function sortMarketItems(items, sort) {
  const compare = Object.hasOwn(sorters, sort) ? sorters[sort] : sorters.quality;
  return [...items].sort(compare);
}
