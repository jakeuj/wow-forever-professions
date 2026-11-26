import test from 'node:test';
import assert from 'node:assert/strict';
import reader from '../guild/worker/index.mjs';
import { mcpResponse } from '../guild/worker/mcp.mjs';
import { MARKET_LIFETIME, SNAPSHOT_LIFETIME } from '../guild/worker/snapshots.mjs';

const url = 'https://worker.example/mcp';
const now = Date.parse('2026-11-24T03:00:00Z'); // 11:00 in Taiwan
const hour = now / 3600e3;

const catalog = {
  fields: ['id', 'name', 'quality'],
  items: [
    [1, '測試草', 0], [2, '測試草', 1], [3, '測試草', 2], [4, '測試礦石', 1], [5, '測試錠', 1],
    [6, '設計圖：測試劍', 2], [7, '垃圾樣本', 0], [8, '測試布', 1], [9, '測試皮', 1], [10, '測試寶石', 1],
  ],
};

const auctions = {
  updatedAt: '2026-11-24T11:00+08:00', hourlyFrom: hour - 100,
  hours: [hour - 30, hour - 4, hour - 3, hour - 2, hour - 1, hour],
  items: {
    // Folded day, then snapshots: 900 · 100 · 100 (unchanged) · 200 · sold out · 400
    2: [5, [[hour - 200, 5], [hour - 30, 900], [hour - 4, 100], [hour - 2, 200], [hour - 1, null], [hour, 400]]],
  },
};

const depth = {
  2: [[100, 5], [150, 10], [300, 20]],
  4: [[1600, 2], [10900, 1]],
  5: [[1000, 4]],
  6: [[1250, 1]],
  8: [[1300, 50]],
  9: null,
};

function market(stamp = now - 60_000) {
  return { schema: 1, region: 'tw', ruleset: 1, house: 113, source: 'official', updatedAt: new Date(stamp).toISOString(), depth };
}

function setup({ snapshots = { 'market-depth': market() }, failing = [] } = {}) {
  const calls = [];
  const options = {
    now: () => now, marketUrl: 'https://data.example/market.json', auctionsUrl: 'https://data.example/auctions.json',
    fetch: async target => {
      calls.push(target);
      if (failing.includes(target)) return new Response(null, { status: 500 });
      return Response.json(target.endsWith('/market.json') ? catalog : auctions);
    },
  };
  const env = { SNAPSHOTS: { get: async key => snapshots[key] ?? null }, PROFILE_RATE: { limit: async () => ({ success: true }) } };
  return { env, options, calls };
}

function post(body, { env, options } = setup(), headers = {}) {
  return mcpResponse(new Request(url, { method: 'POST', headers: { 'Content-Type': 'application/json', ...headers },
    body: typeof body === 'string' ? body : JSON.stringify(body) }), env, options);
}

const rpc = (method, params, id = 1) => ({ jsonrpc: '2.0', id, method, params });

async function call(name, args, context, headers) {
  const response = await post(rpc('tools/call', { name, arguments: args }), context, headers);
  assert.equal(response.status, 200);
  const { result } = await response.json();
  const [{ type, text }] = result.content;
  assert.equal(type, 'text');
  return result.isError ? { error: text } : JSON.parse(text);
}

test('MCP 傳輸層：CORS、405、204、批次與 JSON-RPC 錯誤碼', async () => {
  const { env, options } = setup();
  const send = method => mcpResponse(new Request(url, { method }), env, options);
  const preflight = await send('OPTIONS');
  assert.equal(preflight.status, 204);
  assert.equal(preflight.headers.get('Access-Control-Allow-Origin'), '*');
  assert.equal(preflight.headers.get('Access-Control-Allow-Methods'), 'POST, GET, DELETE, OPTIONS');
  assert.equal(preflight.headers.get('Access-Control-Allow-Headers'), 'Content-Type, Accept, Mcp-Session-Id, MCP-Protocol-Version');
  assert.equal(preflight.headers.get('Access-Control-Expose-Headers'), 'Mcp-Session-Id');
  const get = await send('GET');
  assert.equal(get.status, 405);
  assert.equal(get.headers.get('Allow'), 'POST, DELETE, OPTIONS');
  assert.equal((await send('DELETE')).status, 204);

  const broken = await post('{');
  assert.equal(broken.status, 400);
  assert.equal(broken.headers.get('Access-Control-Allow-Origin'), '*');
  assert.equal(broken.headers.get('Cache-Control'), 'no-store');
  assert.equal(broken.headers.get('X-Robots-Tag'), 'noindex');
  assert.deepEqual(await broken.json(), { jsonrpc: '2.0', id: null, error: { code: -32700, message: 'Parse error' } });

  const unknown = await (await post(rpc('resources/list', {}, 'a'))).json();
  assert.deepEqual([unknown.id, unknown.error.code], ['a', -32601]);
  for (const name of ['nope', 'constructor', undefined]) {
    assert.equal((await (await post(rpc('tools/call', { name }))).json()).error.code, -32602);
  }
  for (const body of [[], 'null', '1', { id: 1, method: 'ping' }, { jsonrpc: '2.0', id: null, method: 'ping' },
    Array(21).fill(rpc('ping'))]) {
    const invalid = await post(body);
    assert.equal(invalid.status, 400);
    assert.equal((await invalid.json()).error.code, -32600);
  }
  assert.equal((await post(' '.repeat(256 * 1024 + 1))).status, 413);

  const batch = await post([rpc('ping', {}, 1), { jsonrpc: '2.0', method: 'notifications/cancelled' }, 5, rpc('none', {}, 2)]);
  assert.deepEqual((await batch.json()).map(({ id, result, error }) => [id, result ?? error.code]), [[1, {}], [null, -32600], [2, -32601]]);
  const quiet = await post([{ jsonrpc: '2.0', method: 'notifications/cancelled' }]);
  assert.deepEqual([quiet.status, await quiet.text()], [202, '']);
});

test('MCP 生命週期：initialize、initialized、ping、tools/list', async () => {
  for (const [asked, given] of [['2025-06-18', '2025-06-18'], ['2025-03-26', '2025-03-26'], ['2024-11-05', '2024-11-05'],
    ['2099-01-01', '2025-03-26'], [undefined, '2025-03-26']]) {
    const { result } = await (await post(rpc('initialize', { protocolVersion: asked }))).json();
    assert.deepEqual(result, { protocolVersion: given, capabilities: { tools: { listChanged: false } },
      serverInfo: { name: 'dawnblade-wow-forever', version: '1.0.0' } });
  }
  const ready = await post({ jsonrpc: '2.0', method: 'notifications/initialized' });
  assert.deepEqual([ready.status, await ready.text()], [202, '']);
  assert.equal(ready.headers.get('Access-Control-Allow-Origin'), '*');
  assert.deepEqual(await (await post(rpc('ping', undefined, 0))).json(), { jsonrpc: '2.0', id: 0, result: {} });
  const { result } = await (await post(rpc('tools/list'))).json();
  assert.deepEqual(result.tools.map(tool => tool.name),
    ['get_item_prices', 'get_item_trend', 'check_buy_list', 'check_price_alerts', 'get_character_professions']);
  for (const tool of result.tools) {
    assert.equal(tool.inputSchema.type, 'object');
    assert.ok(tool.inputSchema.required.every(field => Object.hasOwn(tool.inputSchema.properties, field)));
    assert.match(tool.description, /\p{Script=Han}/u);
    assert.equal('run' in tool, false);
  }
});

test('get_item_prices：同名排除垃圾品質，逐階買滿並回報缺貨', async () => {
  const context = setup();
  const data = await call('get_item_prices', { items: [{ query: '測試草', quantity: 12 }, '4', 5, { query: '測試草', quantity: 50 },
    '測試寶石', '設計圖', '測試', '垃圾樣本', '不存在', '測試皮', 999] }, context);
  assert.equal(data.updatedAtTaipei, '2026-11-24 10:59');
  const [herb, ore, bar, many, gem, partial, vague, junk, none, odd, unnamed] = data.items;
  assert.deepEqual([herb.id, herb.name, herb.totalAvailable, herb.minPriceCopper, herb.minPriceText], [2, '測試草', 35, 100, '1.00s']);
  assert.deepEqual(herb.sameNameIds, [3]);
  assert.deepEqual(herb.tiers[1], { priceCopper: 150, priceText: '1.50s', quantity: 10 });
  assert.deepEqual(herb.buyFill, { requested: 12, fillable: 12, shortfall: 0, totalCopper: 1550, totalText: '15.50s',
    avgCopper: 129.17, avgText: '1.29s' });
  assert.deepEqual([ore.id, ore.minPriceText, ore.tiers[1].priceText, 'buyFill' in ore], [4, '16.00s', '1.09g', false]);
  assert.equal(bar.name, '測試錠');
  assert.deepEqual([many.buyFill.fillable, many.buyFill.shortfall, many.buyFill.totalCopper], [35, 15, 8000]);
  assert.deepEqual([gem.totalAvailable, gem.minPriceCopper, gem.minPriceText, gem.tiers], [0, null, null, []]);
  assert.deepEqual([partial.id, partial.matchedBy], [6, 'partial']);
  assert.match(vague.error, /名稱包含/u);
  assert.ok(vague.candidates.length > 1 && vague.candidates.every(item => item.id !== 1));
  assert.deepEqual(junk.candidates, [{ id: 7, name: '垃圾樣本' }]);
  assert.match(none.error, /找不到/u);
  assert.match(odd.warning, /異常/u);
  assert.deepEqual([unnamed.id, unnamed.name], [999, null]);

  const gone = await call('get_item_prices', { items: [{ query: 10, quantity: 2 }] }, context);
  assert.deepEqual(gone.items[0].buyFill, { requested: 2, fillable: 0, shortfall: 2, totalCopper: 0, totalText: '0c', avgCopper: null, avgText: null });
  assert.equal(context.calls.length, 1); // the catalog is cached
  const tall = setup({ snapshots: { 'market-depth': { ...market(), depth: { 2: Array.from({ length: 12 }, (_, i) => [i + 1, 1]) } } } });
  assert.equal((await call('get_item_prices', { items: [2] }, tall)).items[0].tiers.length, 8);
});

test('get_item_prices：過期價階、目錄失效與參數錯誤都回可讀訊息', async () => {
  for (const snapshot of [null, market(now - MARKET_LIFETIME), { ...market(), house: 114 }]) {
    const { error } = await call('get_item_prices', { items: ['測試草'] }, setup({ snapshots: { 'market-depth': snapshot } }));
    assert.match(error, /三小時/u);
  }
  const offline = setup({ failing: ['https://data.example/market.json'] });
  assert.match((await call('get_item_prices', { items: ['測試草'] }, offline)).error, /目錄/u);
  const byId = await call('get_item_prices', { items: [2] }, offline);
  assert.deepEqual([byId.items[0].minPriceCopper, byId.items[0].name], [100, null]);
  assert.match(byId.warning, /目錄/u);
  for (const args of [undefined, [], {}, { items: [] }, { items: '測試草' }, { items: Array(51).fill(1) }, { items: [0] },
    { items: [1.5] }, { items: [' '] }, { items: [null] }, { items: [{ query: 1, quantity: -1 }] }, { items: [{ query: 1, quantity: '3' }] }]) {
    assert.match((await call('get_item_prices', args)).error, /必須|最多/u);
  }
  const crash = setup();
  crash.env.SNAPSHOTS.get = async () => { throw new Error('internal detail'); };
  assert.equal((await call('get_item_prices', { items: [2] }, crash)).error, '工具執行失敗，請稍後再試。');
});

test('名稱目錄到期後重抓，來源失效時沿用上一份', async () => {
  const context = setup();
  let time = now;
  context.options.now = () => time;
  context.env.SNAPSHOTS.get = async () => market(time);
  const prices = () => call('get_item_prices', { items: ['測試草'] }, context);
  await prices();
  time += 14 * 60_000;
  await prices();
  assert.equal(context.calls.length, 1);
  time += 60_000;
  await prices();
  assert.equal(context.calls.length, 2);
  time += 15 * 60_000;
  const working = context.options.fetch;
  let broken = false;
  // Same function identity keeps the same cache.
  const flaky = setup();
  flaky.options.now = () => time;
  flaky.env.SNAPSHOTS.get = async () => market(time);
  flaky.options.fetch = async target => { if (broken) throw new Error('offline'); return working(target); };
  await call('get_item_prices', { items: ['測試草'] }, flaky);
  broken = true;
  time += 15 * 60_000;
  assert.equal((await call('get_item_prices', { items: ['測試草'] }, flaky)).items[0].id, 2);
});

test('get_item_trend：依快照時間展開四分位，變動點用台灣時間', async () => {
  const context = setup();
  const day = await call('get_item_trend', { items: ['測試草'], days: 1 }, context);
  assert.deepEqual([day.days, day.windowSnapshots, day.windowFrom, day.windowTo], [1, 5, '11/24 07:00', '11/24 11:00']);
  assert.equal(day.updatedAtTaipei, '2026-11-24 11:00');
  assert.equal('coverageNote' in day, false);
  // Valid prices: 100, 100, 200, 400
  const [herb] = day.items;
  assert.equal(herb.snapshots, 4);
  assert.deepEqual([herb.min, herb.q1, herb.median, herb.q3, herb.max].map(({ copper }) => copper), [100, 100, 150, 250, 400]);
  assert.equal(herb.median.text, '1.50s');
  assert.deepEqual(herb.recentChanges, [
    { time: '11/24 07:00', priceCopper: 100, priceText: '1.00s' },
    { time: '11/24 09:00', priceCopper: 200, priceText: '2.00s' },
    { time: '11/24 10:00', priceCopper: null, priceText: '沒貨' },
    { time: '11/24 11:00', priceCopper: 400, priceText: '4.00s' },
  ]);
  assert.deepEqual(herb.liveTiers.map(tier => tier.priceCopper), [100, 150, 300]);

  const week = await call('get_item_trend', { items: ['測試草', '測試錠', '不存在'] }, context);
  assert.equal(week.days, 7);
  assert.match(week.coverageNote, /逐小時紀錄從 11\/20 07:00 起/u);
  assert.equal(week.items[0].max.copper, 900);
  assert.equal(week.items[0].recentChanges[0].time, '11/23 05:00'); // the folded day is left out
  assert.deepEqual([week.items[1].snapshots, week.items[1].median, week.items[1].recentChanges], [0, null, []]);
  assert.match(week.items[1].note, /沒有/u);
  assert.match(week.items[2].error, /找不到/u);

  const stale = await call('get_item_trend', { items: [2] }, setup({ snapshots: {} }));
  assert.equal(stale.liveUpdatedAt, null);
  assert.equal('liveTiers' in stale.items[0], false);
  assert.match((await call('get_item_trend', { items: [2] }, setup({ failing: ['https://data.example/auctions.json'] }))).error, /每小時/u);
  for (const days of [0, 31, 1.5, '7']) assert.match((await call('get_item_trend', { items: [2], days })).error, /days/u);
  assert.match((await call('get_item_trend', { items: Array(21).fill(2) })).error, /最多 20/u);
});

test('get_item_trend：最多列最近 12 筆變動', async () => {
  const context = setup();
  const hours = Array.from({ length: 20 }, (_, index) => hour - 19 + index);
  context.options.fetch = async target => Response.json(target.endsWith('/market.json') ? catalog
    : { ...auctions, hours, items: { 2: [1, hours.map((at, index) => [at, index + 1])] } });
  const { items: [item] } = await call('get_item_trend', { items: [2] }, context);
  assert.deepEqual(item.recentChanges.map(point => point.priceCopper), [9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20]);
});

test('check_buy_list：分類每種狀態並產生 14 欄匯入字串', async () => {
  const data = await call('check_buy_list', { listName: '測試^清單', items: [
    { query: '設計圖：測試劍', quantity: 1, buyBelowCopper: 1250, note: '備註' },
    { query: '測試草', quantity: 12, buyBelowGold: 0.015 },
    { query: '測試錠', quantity: 4, buyBelowCopper: 800 },
    { query: '測試布', plannedCopper: 1000 },
    { query: '測試礦石', quantity: 2, plannedGold: 0.16 },
    { query: '測試寶石', quantity: 3 },
    { query: '測試皮' },
    { query: '不存在' },
    { query: 999 },
  ] });
  assert.deepEqual(data.items.map(item => item.status),
    ['buy_now', 'at_trigger_plenty', 'near_trigger', 'above_planned', 'ok_to_buy', 'out_of_stock', 'out_of_stock', undefined, 'out_of_stock']);
  assert.equal(data.items[0].note, '備註');
  assert.equal(data.items[0].unitsAtOrBelowTrigger, 1);
  assert.equal(data.items[1].buyBelowCopper, 150);
  assert.match(data.items[6].warning, /異常/u);
  assert.match(data.items[7].error, /找不到/u);
  assert.deepEqual(data.importSkippedIds, [999]);
  const term = (name, quantity) => `"${name}";;;;;;;;;;;#;;${quantity}`;
  assert.equal(term('測試草', 12).split(';').length, 14);
  assert.equal(data.auctionatorImport, ['測試 清單', term('設計圖：測試劍', 1), term('測試草', 12), term('測試錠', 4), '"測試布"',
    term('測試礦石', 2), term('測試寶石', 3), '"測試皮"'].join('^'));
  assert.equal(data.auctionatorImportActionable, ['測試 清單', term('設計圖：測試劍', 1), term('測試草', 12), term('測試錠', 4),
    term('測試礦石', 2)].join('^'));
});

test('check_buy_list：觸發與估價的邊界、預設清單名稱與參數錯誤', async () => {
  const status = async item => (await call('check_buy_list', { items: [item] })).items[0];
  assert.equal((await status({ query: '測試布', buyBelowCopper: 1000 })).status, 'near_trigger'); // exactly 30 %
  const far = await status({ query: '測試布', buyBelowCopper: 999 });
  assert.deepEqual([far.status, far.aboveTriggerPercent], ['ok_to_buy', 30]);
  assert.equal((await status({ query: '測試礦石', buyBelowCopper: 1600, buyBelowGold: 0.0001 })).status, 'buy_now'); // copper wins
  assert.equal((await status({ query: '設計圖：測試劍', plannedCopper: 1250 / 1.25 })).status, 'above_planned');
  assert.equal((await status({ query: '測試錠', plannedCopper: 1000 })).status, 'ok_to_buy');
  // The cheapest unit is on plan, but the quantity wanted costs more on average.
  assert.equal((await status({ query: '測試礦石', plannedCopper: 1600 })).status, 'ok_to_buy');
  assert.equal((await status({ query: '測試礦石', plannedCopper: 1600, quantity: 3 })).status, 'above_planned');

  const single = await call('check_buy_list', { items: [{ query: '測試布', plannedCopper: 1 }] });
  assert.equal(single.auctionatorImport, 'MCP採買清單^"測試布"');
  assert.equal(single.auctionatorImportActionable, '');
  assert.equal((await call('check_buy_list', { items: [{ query: '測試布' }], listName: ' ^ ' })).listName, 'MCP採買清單');
  for (const args of [{ items: [{ query: 2, buyBelowCopper: 0 }] }, { items: [{ query: 2, plannedGold: '1' }] },
    { items: [{ query: 2 }], listName: 5 }, { items: Array(51).fill({ query: 2 }) }, { items: [{}] }]) {
    assert.match((await call('check_buy_list', args)).error, /必須|最多/u);
  }
  assert.match((await call('check_buy_list', { items: [{ query: 2 }] }, setup({ snapshots: {} }))).error, /三小時/u);
});

test('check_price_alerts：一次讀取整批，比對含等於門檻，只回最低三檔', async () => {
  const data = market(now);
  data.depth = { ...depth, 2: [[100, 5], [150, 10], [300, 20], [400, 30]] };
  const context = setup({ snapshots: { 'market-depth': data } });
  const reads = [];
  context.env.SNAPSHOTS.get = async (...args) => { reads.push(args); return data; };
  const items = [{ itemId: 4, maxUnitPriceCopper: 1600 }, { itemId: 2, maxUnitPriceCopper: 400 },
    { itemId: 5, maxUnitPriceCopper: 999 }, { itemId: 10, maxUnitPriceCopper: 500 },
    { itemId: 9, maxUnitPriceCopper: 500 }];
  const result = await call('check_price_alerts', { items }, context);
  assert.deepEqual(result, { status: 'match', updatedAtTaipei: '2026-11-24 11:00', alerts: [
    { itemId: 4, minPriceText: '16.00s', maxUnitPriceText: '16.00s', unitsAtOrBelowTrigger: 2,
      tiers: [['16.00s', 2], ['1.0900g', 1]] },
    { itemId: 2, minPriceText: '1.00s', maxUnitPriceText: '4.00s', unitsAtOrBelowTrigger: 65,
      tiers: [['1.00s', 5], ['1.50s', 10], ['3.00s', 20]] },
  ], unreadableItemIds: [9] });
  assert.deepEqual(reads, [['market-depth', 'json']]);
  assert.deepEqual(context.calls, []);
  const extra = await call('check_price_alerts', { items, includeNonMatches: true }, context);
  assert.deepEqual(extra.nonMatches, [{ itemId: 5, minPriceText: '10.00s' }, { itemId: 10, minPriceText: null }]);
  assert.deepEqual(extra.unreadableItemIds, [9]);
});

test('check_price_alerts：超價時回短結果，區分舊資料與缺快照', async () => {
  const items = [{ itemId: 4, maxUnitPriceCopper: 1599 }];
  const context = setup({ snapshots: { 'market-depth': market(now) } });
  const response = await post(rpc('tools/call', { name: 'check_price_alerts', arguments: { items } }), context);
  const previousTool = await post(rpc('tools/call', { name: 'check_buy_list', arguments: {
    items: [{ query: 4, buyBelowCopper: 1599 }],
  } }), context);
  const text = (await response.json()).result.content[0].text;
  assert.equal(text, '{"status":"no_match","updatedAtTaipei":"2026-11-24 11:00"}');
  assert.ok(text.length < (await previousTool.json()).result.content[0].text.length / 2);
  assert.deepEqual(await call('check_price_alerts', { items }), { status: 'stale', updatedAtTaipei: '2026-11-24 10:59' });
  assert.deepEqual(await call('check_price_alerts', { items, snapshotHour: 'previous' }),
    { status: 'no_match', updatedAtTaipei: '2026-11-24 10:59' });
  for (const snapshots of [{}, { 'market-depth': market(now - MARKET_LIFETIME) }]) {
    assert.deepEqual(await call('check_price_alerts', { items }, setup({ snapshots })), { status: 'unavailable' });
  }
  for (const args of [{ items: [] }, { items: Array(51).fill(items[0]) }, { items: [{ itemId: '4' }] },
    { items: [{ itemId: 4, maxUnitPriceCopper: 1.6 }] }, { items, snapshotHour: 'tomorrow' }, { items, includeNonMatches: 'true' }]) {
    assert.match((await call('check_price_alerts', args, context)).error, /必須/u);
  }
});

test('get_character_professions：沿用軍械庫的排除名單、限流與錯誤', async t => {
  const snapshots = { 'character-exclusions': [], 'battle-net-token': 'synthetic' };
  const context = setup({ snapshots });
  const keys = [];
  context.env.PROFILE_RATE.limit = async ({ key }) => { keys.push(key); return { success: key !== '198.51.100.9' }; };
  let professionsUp = true;
  t.mock.method(globalThis, 'fetch', async target => {
    const path = decodeURIComponent(new URL(target).pathname);
    if (path.endsWith('/測試-角色') || path.endsWith('/測試-殘缺')) {
      return Response.json({ id: 321, name: '測試', surname: '角色', level: 60, character_class: { id: 1 }, guild: { name: '測試公會' } });
    }
    if (path.endsWith('/professions')) {
      return professionsUp ? Response.json({ primaries: [{ profession: { id: 164, name: '鍛造' },
        tiers: [{ skill_points: 250, max_skill_points: 300, known_recipes: [{ id: 11, name: '測試劍' }, { id: 12, name: '測試盾' }] }] }] })
        : new Response(null, { status: 500 });
    }
    if (/\/(equipment|specializations)$/u.test(path)) return Response.json({});
    return new Response(null, { status: 404 });
  });
  const ask = (args, headers) => call('get_character_professions', args, context, headers);

  const data = await ask({ slug: '測試 角色' }, { 'CF-Connecting-IP': '203.0.113.5' });
  assert.equal(keys.at(-1), '203.0.113.5');
  assert.deepEqual([data.name, data.slug, data.level, data.className, data.guild], ['測試 角色', '測試-角色', 60, '戰士', '測試公會']);
  assert.deepEqual(data.professions, [{ id: 164, name: '鍛造', skill: 250, maxSkill: 300, recipeCount: 2 }]);
  assert.equal(JSON.stringify(data).includes('321'), false);
  assert.equal('equipment' in data, false);
  const full = await ask({ slug: '測試-角色', includeRecipes: true });
  assert.equal(keys.at(-1), 'local');
  assert.deepEqual(full.professions[0].recipes, [{ id: 11, name: '測試劍' }, { id: 12, name: '測試盾' }]);

  snapshots['character-exclusions'] = [321];
  assert.match((await ask({ slug: '測試-角色' })).error, /找不到/u);
  snapshots['character-exclusions'] = null;
  assert.match((await ask({ slug: '測試-角色' })).error, /暫時無法/u);
  snapshots['character-exclusions'] = [];
  assert.match((await ask({ slug: '測試-不在' })).error, /找不到/u);
  assert.match((await ask({ slug: '測試-角色' }, { 'CF-Connecting-IP': '198.51.100.9' })).error, /太頻繁/u);
  for (const slug of [undefined, '', '只有名字', '../測試', '\ud800-測試', 5]) assert.match((await ask({ slug })).error, /格式不正確/u);
  assert.match((await ask({ slug: '測試-角色', includeRecipes: 'yes' })).error, /includeRecipes/u);
  professionsUp = false;
  assert.match((await ask({ slug: '測試-殘缺' })).error, /專業資料/u);
});

test('Worker 預設匯出：/mcp 與既有資料路徑並存', async () => {
  const start = Date.now();
  const artisans = { schema: 1, fetchedAt: new Date(start).toISOString(), expiresAt: new Date(start + SNAPSHOT_LIFETIME).toISOString(),
    artisans: [{ characterId: 123, name: '測試 工匠', professions: [] }], recipes: {} };
  const env = { SNAPSHOTS: { get: async key => key === 'artisans' ? artisans : null } };
  const at = (path, init) => reader.fetch(new Request(`https://worker.example${path}`, init), env);
  const ping = await at('/mcp', { method: 'POST', body: JSON.stringify(rpc('ping')) });
  assert.deepEqual(await ping.json(), { jsonrpc: '2.0', id: 1, result: {} });
  assert.equal(ping.headers.get('Access-Control-Allow-Origin'), '*');
  assert.equal((await at('/mcp')).status, 405);
  assert.equal((await at('/mcp', { method: 'OPTIONS' })).status, 204);
  assert.equal((await at('/mcp/')).status, 404);
  const list = await at('/artisans.json');
  assert.equal(list.status, 200);
  assert.equal(list.headers.get('Access-Control-Allow-Origin'), 'https://jakeuj.com');
  assert.equal(list.headers.get('Access-Control-Allow-Methods'), null);
  assert.deepEqual((await list.json()).artisans.map(person => person.name), ['測試 工匠']);
  const denied = await at('/artisans.json', { method: 'POST' });
  assert.deepEqual([denied.status, denied.headers.get('Allow')], [405, 'GET']);
});
