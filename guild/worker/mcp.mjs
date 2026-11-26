// Public, read-only MCP endpoint (Streamable HTTP, stateless, no auth, no SSE).
import { armoryResponse } from './armory.mjs';
import { marketExpiry } from './snapshots.mjs';
import { guildDataOrigin } from '../data-source.mjs';
import { priceAt } from '../../market/model.mjs';
import { buyFromDepth } from '../../market/quotes.mjs';
import { shoppingText } from '../../market/tools.mjs';

const MARKET_URL = 'https://raw.githubusercontent.com/jakeuj/wow-forever-professions/main/market/data.json';
const AUCTIONS_URL = 'https://raw.githubusercontent.com/jakeuj/wow-forever-professions/auction-data/auctions.json';
const CATALOG_TTL = 15 * 60 * 1000;
const AUCTIONS_TTL = 5 * 60 * 1000;
const MAX_BODY = 256 * 1024;
const MAX_BATCH = 20;
const MAX_QUANTITY = 1_000_000;
const PROTOCOLS = ['2025-06-18', '2025-03-26', '2024-11-05'];
const DEFAULT_PROTOCOL = '2025-03-26';
const ALLOW = 'POST, DELETE, OPTIONS';

const headers = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Methods': 'POST, GET, DELETE, OPTIONS',
  'Access-Control-Allow-Headers': 'Content-Type, Accept, Mcp-Session-Id, MCP-Protocol-Version',
  'Access-Control-Expose-Headers': 'Mcp-Session-Id',
  'Cache-Control': 'no-store',
  'X-Robots-Tag': 'noindex',
};

// Its message is shown to the caller; any other error becomes a generic one.
class ToolError extends Error {}

// Keyed by fetch implementation, so an injected fetch never sees another one's data.
const caches = new WeakMap();

async function cachedJson(ctx, url, ttl, prepare) {
  let cache = caches.get(ctx.fetch);
  if (!cache) caches.set(ctx.fetch, cache = new Map());
  const hit = cache.get(url);
  if (hit?.expires > ctx.now()) return hit.value;
  try {
    const { fetch: load } = ctx;
    const response = await load(url, { signal: AbortSignal.timeout(8000) });
    if (!response.ok) throw new Error(`HTTP ${response.status}`);
    const value = prepare(await response.json());
    cache.set(url, { value, expires: ctx.now() + ttl });
    return value;
  } catch (error) {
    if (hit) return hit.value;
    throw error;
  }
}

function moneyText(copper) {
  if (copper === null) return null;
  const value = Math.round(copper * 100) / 100;
  if (value >= 10000) return `${(value / 10000).toFixed(2)}g`;
  if (value >= 100) return `${(value / 100).toFixed(2)}s`;
  return `${value}c`;
}

function alertPriceText(copper) {
  if (copper < 10000) return moneyText(copper);
  const gold = Math.floor(copper / 10000);
  const fraction = String(copper % 10000).padStart(4, '0');
  return `${gold}.${fraction}g`;
}

// Taiwan time (UTC+8, no daylight saving). Intl's zh-TW output holds non-ASCII spaces that vary by ICU version.
function taipeiText(value) {
  return new Date(Date.parse(value) + 8 * 3600e3).toISOString().slice(0, 16).replace('T', ' ');
}

// Hours are counted from the Unix epoch (UTC).
function hourText(hour) {
  const text = new Date((hour + 8) * 3600e3).toISOString().slice(5, 13).replace('-', '/').replace('T', ' ');
  return `${text}:00`;
}

// ---- Arguments

function argumentsOf(value) {
  if (value === undefined || value === null) return {};
  if (typeof value !== 'object' || Array.isArray(value)) throw new ToolError('arguments 必須是物件。');
  return value;
}

function numberOf(value, label, { integer = false, min = 0, max = Number.MAX_SAFE_INTEGER } = {}) {
  if (value === undefined || value === null) return null;
  if (typeof value !== 'number' || !Number.isFinite(value) || (integer && !Number.isInteger(value))
    || value < min || value > max) {
    throw new ToolError(`${label} 必須是 ${min} 到 ${max} 之間的${integer ? '整數' : '數字'}。`);
  }
  return value;
}

function priceOf(entry, field, label) {
  const copper = numberOf(entry[`${field}Copper`], `${label}.${field}Copper`, { min: 1 });
  const gold = numberOf(entry[`${field}Gold`], `${label}.${field}Gold`, { min: 0.0001 });
  return copper ?? (gold === null ? null : Math.round(gold * 10000));
}

function entriesOf(items, max) {
  if (!Array.isArray(items) || !items.length) throw new ToolError('items 必須是至少一筆的陣列。');
  if (items.length > max) throw new ToolError(`items 最多 ${max} 筆，這次有 ${items.length} 筆。`);
  return items.map((raw, index) => {
    const label = `items[${index}]`;
    const entry = typeof raw === 'string' || typeof raw === 'number' ? { query: raw } : raw;
    if (!entry || typeof entry !== 'object' || Array.isArray(entry)) {
      throw new ToolError(`${label} 必須是物品名稱、物品 ID，或含 query 的物件。`);
    }
    const { query } = entry;
    const valid = typeof query === 'number' ? Number.isSafeInteger(query) && query > 0
      : typeof query === 'string' && query.trim() && query.length <= 100;
    if (!valid) throw new ToolError(`${label}.query 必須是物品名稱（100 字內）或正整數物品 ID。`);
    return { ...entry, query: typeof query === 'string' ? query.trim() : query, label,
      quantity: numberOf(entry.quantity, `${label}.quantity`, { integer: true, max: MAX_QUANTITY }) || 0 };
  });
}

// ---- Data

async function readMarket(ctx) {
  const market = await ctx.env.SNAPSHOTS.get('market-depth', 'json');
  return marketExpiry(market) > ctx.now() ? market : null;
}

async function requireMarket(ctx) {
  const market = await readMarket(ctx);
  if (!market) throw new ToolError('目前沒有三小時內的部落拍賣場價階，請等下一次每小時更新後再查。');
  return market;
}

function marketHeader(market) {
  return { market: '亞服 PvP 部落 113 號拍賣場', updatedAt: market.updatedAt,
    updatedAtTaipei: taipeiText(market.updatedAt) };
}

const normalized = text => text.normalize('NFKC').trim().toLowerCase();

function prepareCatalog({ fields, items }) {
  const [id, name, quality] = ['id', 'name', 'quality'].map(field => fields.indexOf(field));
  const rows = items.filter(row => typeof row[name] === 'string')
    .map(row => ({ id: row[id], name: row[name], junk: row[quality] === 0, key: normalized(row[name]) }));
  return { rows, byId: new Map(rows.map(row => [row.id, row])) };
}

function itemId(query) {
  if (typeof query === 'number') return query;
  return /^[1-9]\d{0,9}$/u.test(query) ? Number(query) : null;
}

// Numeric queries still work without names when the catalog is down.
async function loadCatalog(ctx, entries) {
  try {
    return await cachedJson(ctx, ctx.marketUrl, CATALOG_TTL, prepareCatalog);
  } catch {
    if (entries.every(entry => itemId(entry.query) !== null)) return { rows: [], byId: new Map(), missing: true };
    throw new ToolError('物品名稱目錄暫時無法讀取，請稍後再試，或改用物品 ID 查詢。');
  }
}

function resolveItem(catalog, query) {
  const id = itemId(query);
  if (id !== null) return { query, id, name: catalog.byId.get(id)?.name ?? null };
  const key = normalized(query);
  const same = catalog.rows.filter(row => row.key === key);
  const exact = same.filter(row => !row.junk);
  const brief = rows => rows.slice(0, 10).map(row => ({ id: row.id, name: row.name }));
  if (exact.length) {
    return { query, id: exact[0].id, name: exact[0].name,
      ...(exact.length > 1 ? { sameNameIds: exact.slice(1).map(row => row.id) } : {}) };
  }
  if (same.length) return { query, error: '同名物品都是垃圾品質，需要時請改用物品 ID 查詢。', candidates: brief(same) };
  const partial = catalog.rows.filter(row => !row.junk && row.key.includes(key));
  if (partial.length === 1) return { query, id: partial[0].id, name: partial[0].name, matchedBy: 'partial' };
  return partial.length
    ? { query, error: `有 ${partial.length} 個名稱包含「${query}」的物品，請指定完整名稱或物品 ID。`, candidates: brief(partial) }
    : { query, error: `找不到名稱包含「${query}」的物品。` };
}

function ladderOf(market, id) {
  const tiers = market.depth[id];
  return Array.isArray(tiers) ? tiers : [];
}

// The collector stores null when an item's listings could not be read reliably.
function unreadable(market, id) {
  return Object.hasOwn(market.depth, id) && !Array.isArray(market.depth[id]);
}

function tierRows(ladder, count) {
  return ladder.slice(0, count).map(([price, quantity]) => ({ priceCopper: price, priceText: moneyText(price), quantity }));
}

function units(ladder, limit = Infinity) {
  return ladder.reduce((sum, [price, quantity]) => sum + (price <= limit ? quantity : 0), 0);
}

function fillOf(market, id, quantity) {
  const { bought, missing, spent } = buyFromDepth(market, id, quantity);
  const average = bought ? Math.round(spent / bought * 100) / 100 : null;
  return { requested: quantity, fillable: bought, shortfall: missing, totalCopper: spent, totalText: moneyText(spent),
    avgCopper: average, avgText: moneyText(average) };
}

function quoteOf(market, id) {
  const ladder = ladderOf(market, id);
  const lowest = ladder[0]?.[0] ?? null;
  return { totalAvailable: units(ladder), minPriceCopper: lowest, minPriceText: moneyText(lowest),
    ...(unreadable(market, id) ? { warning: '這項物品的官方掛單資料異常，無法判斷價格與件數。' } : {}) };
}

const catalogWarning = catalog => catalog.missing ? { warning: '物品名稱目錄暫時無法讀取，只能顯示物品 ID。' } : {};

// ---- Tools

async function getItemPrices(ctx, args) {
  const entries = entriesOf(args.items, 50);
  const market = await requireMarket(ctx);
  const catalog = await loadCatalog(ctx, entries);
  return { ...marketHeader(market), ...catalogWarning(catalog), items: entries.map(({ query, quantity }) => {
    const item = resolveItem(catalog, query);
    if (item.error) return item;
    return { ...item, ...quoteOf(market, item.id), tiers: tierRows(ladderOf(market, item.id), 8),
      ...(quantity ? { buyFill: fillOf(market, item.id, quantity) } : {}) };
  }) };
}

// Linear interpolation between closest ranks.
function quantile(sorted, share) {
  const position = (sorted.length - 1) * share;
  const low = Math.floor(position);
  const high = Math.ceil(position);
  return Math.round(sorted[low] + (sorted[high] - sorted[low]) * (position - low));
}

const price = copper => ({ copper, text: moneyText(copper) });

async function getItemTrend(ctx, args) {
  const entries = entriesOf(args.items, 20);
  const days = numberOf(args.days, 'days', { integer: true, min: 1, max: 30 }) ?? 7;
  const catalog = await loadCatalog(ctx, entries);
  let record;
  try {
    record = await cachedJson(ctx, ctx.auctionsUrl, AUCTIONS_TTL, data => data);
  } catch {
    throw new ToolError('每小時拍賣紀錄暫時無法讀取，請稍後再試。');
  }
  if (!record.hours?.length) throw new ToolError('每小時拍賣紀錄目前沒有快照。');
  const market = await readMarket(ctx).catch(() => null);
  const latest = record.hours.at(-1);
  const since = latest - days * 24;
  const hours = record.hours.filter(hour => hour > since);
  const taken = new Set(hours);
  return {
    market: '亞服 PvP 部落 113 號拍賣場', updatedAt: record.updatedAt, updatedAtTaipei: taipeiText(record.updatedAt),
    days, windowFrom: hourText(hours[0]), windowTo: hourText(latest), windowSnapshots: hours.length,
    ...(record.hourlyFrom > since + 1
      ? { coverageNote: `逐小時紀錄從 ${hourText(record.hourlyFrom)} 起，更早的時段不列入統計。` } : {}),
    liveUpdatedAt: market?.updatedAt ?? null, ...catalogWarning(catalog),
    items: entries.map(({ query }) => {
      const item = resolveItem(catalog, query);
      if (item.error) return item;
      const series = record.items[item.id]?.[1] || [];
      const prices = hours.map(hour => priceAt(series, hour)).filter(value => Number.isFinite(value) && value > 0)
        .sort((a, b) => a - b);
      const stat = share => prices.length ? price(quantile(prices, share)) : null;
      return {
        ...item, snapshots: prices.length, min: stat(0), q1: stat(0.25), median: stat(0.5), q3: stat(0.75), max: stat(1),
        // Only real snapshots: older points are daily lows, or restate the price at hourlyFrom.
        recentChanges: series.filter(([hour]) => taken.has(hour)).slice(-12).map(([hour, value]) => ({
          time: hourText(hour), priceCopper: value ?? null, priceText: value === null ? '沒貨' : moneyText(value),
        })),
        ...(market ? { liveTiers: tierRows(ladderOf(market, item.id), 3) } : {}),
        ...(prices.length ? {} : { note: '這段期間沒有這項物品的價格紀錄。' }),
      };
    }),
  };
}

// Percentages are compared in integers, so 30 % and 20 % boundaries are exact.
function buyStatus(ladder, trigger, planned, unitCost) {
  if (!ladder.length) return 'out_of_stock';
  const lowest = ladder[0][0];
  if (trigger !== null) {
    if (lowest <= trigger) return units(ladder, trigger) <= 3 ? 'buy_now' : 'at_trigger_plenty';
    if (lowest * 10 <= trigger * 13) return 'near_trigger';
  }
  return planned !== null && unitCost * 10 > planned * 12 ? 'above_planned' : 'ok_to_buy';
}

const statusTexts = {
  buy_now: '達觸發價，且該價位以下最多 3 件，現在買',
  at_trigger_plenty: '達觸發價，貨還多',
  near_trigger: '高於觸發價 30% 內',
  above_planned: '比路線估價貴超過 20%',
  ok_to_buy: '可以買',
  out_of_stock: '目前沒貨',
};

async function checkBuyList(ctx, args) {
  if (args.listName !== undefined && args.listName !== null && typeof args.listName !== 'string') {
    throw new ToolError('listName 必須是文字。');
  }
  // These characters separate lists and fields in Auctionator's import format.
  const listName = (args.listName ?? '').replace(/[\^;"\r\n]+/gu, ' ').trim().slice(0, 60) || 'MCP採買清單';
  const entries = entriesOf(args.items, 50).map(entry => ({ ...entry,
    trigger: priceOf(entry, 'buyBelow', entry.label), planned: priceOf(entry, 'planned', entry.label) }));
  const market = await requireMarket(ctx);
  const catalog = await loadCatalog(ctx, entries);
  const rows = entries.map(({ query, quantity, trigger, planned, note }) => {
    const item = resolveItem(catalog, query);
    const extra = typeof note === 'string' && note ? { note: note.slice(0, 200) } : {};
    if (item.error) return { ...item, ...extra };
    const ladder = ladderOf(market, item.id);
    const fill = quantity ? fillOf(market, item.id, quantity) : null;
    const lowest = ladder[0]?.[0] ?? null;
    const status = buyStatus(ladder, trigger, planned, fill?.avgCopper ?? lowest);
    const aboveTrigger = trigger !== null && status !== 'near_trigger' && lowest > trigger
      ? { aboveTriggerPercent: Math.round((lowest / trigger - 1) * 100) } : {};
    return { ...item, status, statusText: statusTexts[status], ...aboveTrigger, quantity, ...quoteOf(market, item.id),
      ...(trigger === null ? {} : { buyBelowCopper: trigger, buyBelowText: moneyText(trigger),
        unitsAtOrBelowTrigger: units(ladder, trigger) }),
      ...(planned === null ? {} : { plannedCopper: planned, plannedText: moneyText(planned) }),
      ...(fill ? { buyFill: fill } : {}), ...extra };
  });
  const found = rows.filter(row => row.status);
  const actionable = found.filter(row => row.status !== 'out_of_stock' && row.status !== 'above_planned');
  const unnamed = found.filter(row => !row.name).map(row => row.id);
  return { ...marketHeader(market), listName, ...catalogWarning(catalog), items: rows,
    ...(unnamed.length ? { importSkippedIds: unnamed } : {}),
    auctionatorImport: shoppingText(listName, found),
    auctionatorImportActionable: shoppingText(listName, actionable) };
}

async function checkPriceAlerts(ctx, { items, includeNonMatches = false, snapshotHour = 'current' }) {
  if (!Array.isArray(items) || items.length < 1 || items.length > 50) {
    throw new ToolError('items 必須有 1 到 50 筆物品。');
  }
  if (typeof includeNonMatches !== 'boolean') throw new ToolError('includeNonMatches 必須是布林值。');
  if (snapshotHour !== 'current' && snapshotHour !== 'previous') {
    throw new ToolError('snapshotHour 必須是 current 或 previous。');
  }
  const entries = items.map((entry, index) => {
    const itemId = numberOf(entry?.itemId, `items[${index}].itemId`, { integer: true, min: 1 });
    const limit = numberOf(entry?.maxUnitPriceCopper, `items[${index}].maxUnitPriceCopper`, { integer: true, min: 1 });
    if (itemId === null || limit === null) throw new ToolError(`items[${index}] 必須有 itemId 和 maxUnitPriceCopper。`);
    return { itemId, limit };
  });

  const market = await readMarket(ctx);
  if (!market) return { status: 'unavailable' };
  const updatedAtTaipei = taipeiText(market.updatedAt);
  const hour = 3_600_000;
  const target = (Math.floor(ctx.now() / hour) - (snapshotHour === 'previous' ? 1 : 0)) * hour;
  if (Date.parse(market.updatedAt) < target) return { status: 'stale', updatedAtTaipei };

  const alerts = [];
  const nonMatches = [];
  const unreadableItemIds = [];
  for (const { itemId, limit } of entries) {
    if (unreadable(market, itemId)) {
      unreadableItemIds.push(itemId);
      continue;
    }
    const ladder = ladderOf(market, itemId);
    const lowest = ladder[0]?.[0];
    if (lowest !== undefined && lowest <= limit) {
      alerts.push({ itemId, minPriceText: alertPriceText(lowest), maxUnitPriceText: alertPriceText(limit),
        unitsAtOrBelowTrigger: units(ladder, limit),
        tiers: ladder.slice(0, 3).map(([price, quantity]) => [alertPriceText(price), quantity]) });
    } else if (includeNonMatches) {
      nonMatches.push({ itemId, minPriceText: lowest === undefined ? null : alertPriceText(lowest) });
    }
  }
  return { status: alerts.length ? 'match' : 'no_match', updatedAtTaipei,
    ...(alerts.length ? { alerts } : {}), ...(includeNonMatches ? { nonMatches } : {}),
    ...(unreadableItemIds.length ? { unreadableItemIds } : {}) };
}

const armoryErrors = {
  400: '角色名稱格式不正確，請用「名字-姓氏」，例如 測試-角色。',
  404: '找不到這個角色，或該角色沒有公開資料。',
  429: '角色查詢太頻繁，請約一分鐘後再試。',
  503: 'Battle.net 角色資料暫時無法取得，請稍後再試。',
};

async function getCharacterProfessions(ctx, args) {
  const { slug, includeRecipes = false } = args;
  if (typeof slug !== 'string' || !slug.trim() || slug.length > 100 || !slug.isWellFormed()) {
    throw new ToolError(armoryErrors[400]);
  }
  if (typeof includeRecipes !== 'boolean') throw new ToolError('includeRecipes 必須是 true 或 false。');
  const address = ctx.request.headers.get('CF-Connecting-IP');
  const request = new Request(`${guildDataOrigin}/characters/${encodeURIComponent(slug)}.json`,
    { headers: address ? { 'CF-Connecting-IP': address } : {} });
  const response = await armoryResponse(request, ctx.env, { kind: 'characters', value: slug }, {});
  if (!response.ok) throw new ToolError(armoryErrors[response.status] || armoryErrors[503]);
  const { name, slug: key, level, className, guild, fetchedAt, professions, missing } = await response.json();
  // A failed section reads as an empty list; do not report it as "no professions".
  if (missing.includes('professions')) throw new ToolError('Battle.net 暫時沒有回傳這個角色的專業資料，請稍後再試。');
  return { name, slug: key, level, className, guild, fetchedAt, fetchedAtTaipei: taipeiText(fetchedAt),
    professions: professions.map(({ id, name: title, skill, maxSkill, recipes }) => ({
      id, name: title, skill, maxSkill, recipeCount: recipes.length,
      ...(includeRecipes ? { recipes: recipes.map(([recipeId, recipeName]) => ({ id: recipeId, name: recipeName })) } : {}),
    })) };
}

const itemQuery = {
  anyOf: [{ type: 'string' }, { type: 'integer', minimum: 1 }],
  description: '物品的繁體中文名稱，或物品 ID。',
};
const quantity = { type: 'integer', minimum: 0, maximum: MAX_QUANTITY };
const annotations = { readOnlyHint: true, openWorldHint: true };

const tools = new Map([
  ['get_item_prices', { run: getItemPrices, definition: {
    description: '查《魔獸世界：永恆》亞服 PvP 部落 113 號拍賣場的最新價階：在售件數、最低單價與前 8 個價位。'
      + '給 quantity 會試算由便宜往上買滿的總價與均價。價格是掛單的一口價，每小時更新。',
    inputSchema: { type: 'object', required: ['items'], properties: {
      items: { type: 'array', minItems: 1, maxItems: 50, description: '要查的物品，最多 50 筆。', items: { anyOf: [
        { type: 'string', description: '物品名稱或 ID。' },
        { type: 'integer', minimum: 1, description: '物品 ID。' },
        { type: 'object', required: ['query'], properties: {
          query: itemQuery, quantity: { ...quantity, description: '想買的件數，用來試算總價。' },
        } },
      ] } },
    } },
  } }],
  ['get_item_trend', { run: getItemTrend, definition: {
    description: '查部落 113 號拍賣場每小時最低單價的走勢：最低、第一四分位、中位數、第三四分位、最高，'
      + '以及最近 12 筆變動（台灣時間）與即時前 3 個價階。逐小時紀錄約保留 7 天。',
    inputSchema: { type: 'object', required: ['items'], properties: {
      items: { type: 'array', minItems: 1, maxItems: 20, description: '要查的物品名稱或 ID，最多 20 筆。', items: itemQuery },
      days: { type: 'integer', minimum: 1, maximum: 30, default: 7, description: '往回統計幾天，預設 7。' },
    } },
  } }],
  ['check_buy_list', { run: checkBuyList, definition: {
    description: '把採買清單比對部落 113 號拍賣場的即時價階，判斷每項該不該買，並產生拍賣小幫手（Auctionator）匯入字串。'
      + 'status：buy_now 達觸發價且最多 3 件、at_trigger_plenty 達觸發價且貨多、near_trigger 高於觸發價 30% 內、'
      + 'above_planned 比路線估價貴超過 20%、ok_to_buy 可以買、out_of_stock 沒貨。'
      + 'auctionatorImport 是整份清單，auctionatorImportActionable 排除沒貨與太貴的。',
    inputSchema: { type: 'object', required: ['items'], properties: {
      listName: { type: 'string', default: 'MCP採買清單', description: '匯入後的購物清單名稱。' },
      items: { type: 'array', minItems: 1, maxItems: 50, description: '採買項目，最多 50 筆。', items: {
        type: 'object', required: ['query'], properties: {
          query: itemQuery,
          quantity: { ...quantity, description: '要買的件數。' },
          buyBelowCopper: { type: 'number', description: '觸發價（每件，銅）。與 buyBelowGold 同時給時以此為準。' },
          buyBelowGold: { type: 'number', description: '觸發價（每件，金）。' },
          plannedCopper: { type: 'number', description: '路線估價（每件，銅）。與 plannedGold 同時給時以此為準。' },
          plannedGold: { type: 'number', description: '路線估價（每件，金）。' },
          note: { type: 'string', description: '備註，原樣帶回。' },
        },
      } },
    } },
  } }],
  ['check_price_alerts', { run: checkPriceAlerts, compact: true, definition: {
    annotations: { readOnlyHint: true, destructiveHint: false, idempotentHint: true, openWorldHint: false },
    description: '用一次查詢比對部落 113 號拍賣場的物品清單。單價小於或等於門檻時 status 為 match，'
      + 'alerts 回傳最低價、門檻、門檻內總件數和最低三檔 [單價, 件數]。其餘狀態為 no_match、stale、unavailable。',
    inputSchema: { type: 'object', required: ['items'], properties: {
      items: { type: 'array', minItems: 1, maxItems: 50, items: {
        type: 'object', required: ['itemId', 'maxUnitPriceCopper'], properties: {
          itemId: { type: 'integer', minimum: 1, description: '物品 ID。' },
          maxUnitPriceCopper: { type: 'integer', minimum: 1, description: '每件的到價門檻，單位為銅。' },
        },
      } },
      includeNonMatches: { type: 'boolean', default: false, description: '附上超價或缺貨物品的最低價，缺貨回 null。' },
      snapshotHour: { type: 'string', enum: ['current', 'previous'], default: 'current',
        description: '快照至少是本小時（current）或上一小時（previous）。' },
    } },
  } }],
  ['get_character_professions', { run: getCharacterProfessions, definition: {
    description: '查《魔獸世界：永恆》台區角色的等級、職業、公會與各專業目前技能點數、上限和已學配方數。',
    inputSchema: { type: 'object', required: ['slug'], properties: {
      slug: { type: 'string', description: '角色的「名字-姓氏」，例如 測試-角色。' },
      includeRecipes: { type: 'boolean', default: false, description: '設為 true 才列出已學配方。' },
    } },
  } }],
]);

// ---- JSON-RPC

const rpcError = (id, code, message) => ({ jsonrpc: '2.0', id, error: { code, message } });
const isObject = value => Boolean(value) && typeof value === 'object' && !Array.isArray(value);

async function callTool(ctx, tool, args) {
  try {
    const payload = await tool.run(ctx, argumentsOf(args));
    return { content: [{ type: 'text', text: JSON.stringify(payload, null, tool.compact ? 0 : 2) }] };
  } catch (error) {
    const text = error instanceof ToolError ? error.message : '工具執行失敗，請稍後再試。';
    return { content: [{ type: 'text', text }], isError: true };
  }
}

// Returns null for messages that get no reply.
async function answer(ctx, message) {
  if (!isObject(message) || message.jsonrpc !== '2.0') return rpcError(null, -32600, 'Invalid Request');
  const { id, method, params = {} } = message;
  if (method === undefined && ('result' in message || 'error' in message)) return null;
  if (typeof method !== 'string') return rpcError(null, -32600, 'Invalid Request');
  if (id === undefined || method === 'notifications/initialized') return null;
  if (typeof id !== 'string' && !Number.isFinite(id)) return rpcError(null, -32600, 'Invalid Request');
  if (!isObject(params)) return rpcError(id, -32602, 'Invalid params');
  const reply = result => ({ jsonrpc: '2.0', id, result });
  switch (method) {
    case 'initialize':
      return reply({
        protocolVersion: PROTOCOLS.includes(params.protocolVersion) ? params.protocolVersion : DEFAULT_PROTOCOL,
        capabilities: { tools: { listChanged: false } },
        serverInfo: { name: 'dawnblade-wow-forever', version: '1.0.0' },
      });
    case 'ping':
      return reply({});
    case 'tools/list':
      return reply({ tools: [...tools].map(([name, { definition }]) => ({ name, annotations, ...definition })) });
    case 'tools/call': {
      const tool = tools.get(params.name);
      return tool ? reply(await callTool(ctx, tool, params.arguments)) : rpcError(id, -32602, 'Unknown tool');
    }
    default:
      return rpcError(id, -32601, 'Method not found');
  }
}

export async function mcpResponse(request, env, options = {}) {
  if (request.method === 'OPTIONS' || request.method === 'DELETE') return new Response(null, { status: 204, headers });
  if (request.method !== 'POST') return new Response(null, { status: 405, headers: { ...headers, Allow: ALLOW } });

  const json = (body, status = 200) => Response.json(body, { status, headers });
  let body;
  try {
    const text = await request.text();
    if (text.length > MAX_BODY) return json(rpcError(null, -32600, 'Request too large'), 413);
    body = JSON.parse(text);
  } catch {
    return json(rpcError(null, -32700, 'Parse error'), 400);
  }

  const ctx = { request, env, fetch: options.fetch ?? fetch, now: options.now ?? Date.now,
    marketUrl: options.marketUrl ?? MARKET_URL, auctionsUrl: options.auctionsUrl ?? AUCTIONS_URL };
  if (!Array.isArray(body)) {
    const reply = await answer(ctx, body);
    if (!reply) return new Response(null, { status: 202, headers });
    return json(reply, reply.error?.code === -32600 ? 400 : 200);
  }
  if (!body.length || body.length > MAX_BATCH) {
    return json(rpcError(null, -32600, `Batch must hold 1 to ${MAX_BATCH} messages`), 400);
  }
  const replies = [];
  // In turn, so later calls reuse what earlier ones cached.
  for (const message of body) {
    const reply = await answer(ctx, message);
    if (reply) replies.push(reply);
  }
  return replies.length ? json(replies) : new Response(null, { status: 202, headers });
}
