// Personal market page: renders market/data.json (built by scripts/build-market-data.py
// from the owner's Auctionator scan) as a searchable, sortable price list. Items the
// official auction API carries (gear, weapons, recipes: things that do not stack) use
// its hourly prices from auctions.json on the auction-data branch, written by
// scripts/collect-auctions.py, with a 24-hour change and a 7-day trend line.
// Starred items are kept in this browser's localStorage; #fav=<id.id...> shares a list.
(() => {
  const PAGE = 120;
  const QUALITY = ['粗糙', '普通', '優秀', '精良', '史詩', '傳說', '神器', '傳家寶'];
  const ICON = 'https://wow.zamimg.com/images/wow/icons/medium/';
  const AUCTIONS = 'https://raw.githubusercontent.com/jakeuj/wow-forever-professions/auction-data/auctions.json';
  const TREND_HOURS = 7 * 24;
  const $ = selector => document.querySelector(selector);
  const form = $('[data-market-form]');
  const list = $('[data-market-list]');
  const summary = $('[data-market-summary]');
  const more = $('[data-market-more]');
  if (!form || !list) return;
  const favbar = $('[data-market-favbar]');
  const favCount = $('[data-fav-count]');
  const favHint = $('[data-fav-hint]');
  const favShare = $('[data-fav-share]');
  const favField = $('[data-fav-field]');
  const favUrl = $('[data-fav-url]');
  const sharedBox = $('[data-market-shared]');
  const sharedText = $('[data-shared-text]');
  const sharedAdd = $('[data-shared-add]');
  const sharedExit = $('[data-shared-exit]');
  const ahBox = $('[data-market-ah]');
  const ahFav = $('[data-ah-fav]');
  const ahAll = $('[data-ah-all]');
  const ahDownload = $('[data-ah-download]');
  const ahField = $('[data-ah-field]');
  const ahText = $('[data-ah-text]');
  const ahImportText = $('[data-ah-import-text]');
  const ahImport = $('[data-ah-import]');
  const ahImportResult = $('[data-ah-import-result]');

  const toast = document.createElement('div');
  toast.className = 'toast';
  toast.setAttribute('role', 'status');
  toast.setAttribute('aria-live', 'polite');
  document.body.append(toast);
  let toastTimer;
  const notify = message => {
    toast.textContent = message;
    toast.classList.add('visible');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => toast.classList.remove('visible'), 3200);
  };

  const shortDay = iso => iso ? `${Number(iso.slice(5, 7))}/${Number(iso.slice(8, 10))}` : '';
  // API hours are hours since the Unix epoch (UTC); show them in Taiwan time.
  const hourDate = hour => new Date((hour + 8) * 3600e3);
  const hourDay = hour => { const d = hourDate(hour); return `${d.getUTCMonth() + 1}/${d.getUTCDate()}`; };
  const hourLabel = hour => `${hourDay(hour)} ${hourDate(hour).getUTCHours()} 時`;
  const money = copper => {
    if (copper == null) return [['—', '', 'none']];
    const g = Math.floor(copper / 10000), s = Math.floor(copper / 100) % 100, c = copper % 100;
    const parts = [];
    if (g) parts.push([g.toLocaleString('zh-TW'), '金', 'g']);
    if (s) parts.push([s, '銀', 's']);
    if (c && g < 100) parts.push([c, '銅', 'c']);
    if (!parts.length) parts.push([0, '銅', 'c']);
    return parts;
  };
  const moneyText = copper => money(copper).map(([amount, unit]) => `${amount}${unit}`).join(' ');

  let items = [];
  let latestDay = '';
  let classes = {};
  let subclasses = {};
  let shown = 0;
  let filtered = [];
  let apiHour = null;
  let itemIds = new Set();

  // Favorites: item ids in localStorage, which can be missing or blocked (private windows),
  // so every access is guarded and the page works without it.
  const FAV_KEY = 'wfp.market.favorites'; // endgame/ah-copy.js reads it for the full list export
  const parseIds = text => [...new Set(String(text ?? '').split(/[.,\s]+/).map(Number)
    .filter(id => Number.isInteger(id) && id > 0))].slice(0, 500);
  const loadFavorites = () => {
    try {
      const stored = JSON.parse(localStorage.getItem(FAV_KEY) || '[]');
      return Array.isArray(stored) ? parseIds(stored.join('.')) : [];
    } catch {
      return [];
    }
  };
  let favorites = new Set(loadFavorites());
  let favStored = true;
  const saveFavorites = () => {
    try {
      localStorage.setItem(FAV_KEY, JSON.stringify([...favorites].sort((a, b) => a - b)));
      favStored = true;
    } catch {
      favStored = false;
    }
  };
  let shared = null; // ids from a #fav= link, in the order they were shared

  const readHash = () => {
    const params = new URLSearchParams(location.hash.slice(1));
    const defaults = { q: '', cat: '', quality: '', sort: 'quality' };
    for (const [field, value] of Object.entries(defaults)) form.elements[field].value = params.get(field) ?? value;
    if (!form.elements.sort.value) form.elements.sort.value = 'quality';
    form.elements.latest.checked = params.get('latest') === '1';
    form.elements.mine.checked = params.get('mine') === '1';
    shared = params.has('fav') ? parseIds(params.get('fav')) : null;
  };
  const writeHash = () => {
    const params = new URLSearchParams();
    for (const field of ['q', 'cat', 'quality', 'sort']) {
      const value = form.elements[field].value;
      if (value && !(field === 'sort' && value === 'quality')) params.set(field, value);
    }
    if (form.elements.latest.checked) params.set('latest', '1');
    if (form.elements.mine.checked) params.set('mine', '1');
    if (shared) params.set('fav', shared.join('.'));
    const hash = params.toString();
    history.replaceState(null, '', hash ? `#${hash}` : location.pathname + location.search);
  };

  // Price in effect at `hour` in a change-point series: undefined before its first point.
  const priceAt = (series, hour) => {
    let value;
    for (const [t, price] of series) {
      if (t > hour) break;
      value = price;
    }
    return value;
  };

  // Containers, weapons, armor, recipes and quivers never stack, so the API lists every one
  // on sale; if a newer API snapshot lacks one the scan saw, it has sold or expired since.
  const API_CLASSES = new Set([1, 2, 4, 9, 11]);

  // Give each scanned item the fields the list shows, from the API when it carries the item.
  const merge = (auctions, apiNewer) => {
    for (const item of items) {
      const entry = auctions && auctions.items[item.id];
      if (!entry) {
        const goneSinceScan = apiNewer && API_CLASSES.has(item.class);
        item.now = item.price;
        item.listed = item.day === latestDay && !goneSinceScan;
        item.base = item.prev;
        item.baseLabel = shortDay(item.prevDay);
        item.units = item.listed ? item.count : null;
        item.when = goneSinceScan ? `${shortDay(item.day)} 掃描看到，官方已沒貨`
          : item.listed ? `${shortDay(item.day)} 掃描` : `${shortDay(item.day)} 掃描看到`;
        continue;
      }
      const [count, series] = entry;
      const last = series[series.length - 1];
      const lastPrice = [...series].reverse().find(([, price]) => price != null);
      item.series = series;
      item.listed = last[1] != null;
      item.now = item.listed ? last[1] : lastPrice && lastPrice[1];
      item.units = item.listed ? count : null;
      item.when = item.listed ? `官方 ${auctions.updatedAt.slice(11, 16)}` : `${hourLabel(last[0])}起沒貨`;
      item.base = item.listed ? priceAt(series, apiHour - 24) : null;
      item.baseLabel = '24 小時前';
    }
  };

  const change = item => (item.base && item.now != null) ? (item.now - item.base) / item.base : null;
  const sorters = {
    quality: (a, b) => (b.quality ?? -1) - (a.quality ?? -1) || (b.now ?? 0) - (a.now ?? 0),
    'price-desc': (a, b) => (b.now ?? 0) - (a.now ?? 0),
    'price-asc': (a, b) => (a.now ?? Infinity) - (b.now ?? Infinity),
    drop: (a, b) => (change(a) ?? Infinity) - (change(b) ?? Infinity),
    count: (a, b) => (b.units ?? 0) - (a.units ?? 0),
    name: (a, b) => a.name.localeCompare(b.name, 'zh-Hant-TW'),
  };

  const apply = () => {
    const q = form.elements.q.value.trim();
    const cat = form.elements.cat.value;
    const quality = form.elements.quality.value;
    const listedOnly = form.elements.latest.checked;
    const mineOnly = form.elements.mine.checked;
    const sharedSet = shared && new Set(shared);
    filtered = items.filter(item => {
      if (sharedSet && !sharedSet.has(item.id)) return false;
      if (mineOnly && !favorites.has(item.id)) return false;
      if (q && !item.name.includes(q) && String(item.id) !== q) return false;
      if (cat.startsWith('c') && String(item.class) !== cat.slice(1)) return false;
      if (cat.startsWith('s') && `${item.class}.${item.subclass}` !== cat.slice(1)) return false;
      if (quality !== '' && String(item.quality) !== quality) return false;
      if (listedOnly && !item.listed) return false;
      return true;
    });
    filtered.sort(sorters[form.elements.sort.value] || sorters.quality);
    list.replaceChildren();
    shown = 0;
    renderMore();
    writeHash();
    updateFavorites();
  };

  const updateFavorites = () => {
    const count = favorites.size;
    favCount.textContent = count ? `（${count}）` : '';
    favbar.hidden = false;
    favShare.disabled = !count;
    ahBox.hidden = false;
    ahFav.disabled = !count;
    favHint.textContent = !count
      ? '點物品名稱旁的 ☆ 收藏；收藏存在這個瀏覽器，也可以複製連結分享給朋友。'
      : favStored
        ? `已收藏 ${count} 件，存在這個瀏覽器。`
        : `已收藏 ${count} 件，但這個瀏覽器不允許儲存，關掉頁面就會消失；請先複製分享連結保存。`;
    sharedBox.hidden = !shared;
    if (!shared) return;
    const known = shared.filter(id => itemIds.has(id)).length;
    const missing = shared.length - known;
    const added = shared.every(id => favorites.has(id) || !itemIds.has(id));
    sharedText.textContent = `這是分享的收藏清單，共 ${known} 件${missing ? `（另有 ${missing} 件目前沒有行情資料）` : ''}。`
      + (added ? '都已經在你的收藏裡。' : '想留著的話按「加到我的收藏」，會存在這個瀏覽器。');
    sharedAdd.disabled = added;
  };

  // A small step chart of the last 7 days of lowest prices; gaps where the item was gone.
  const SVG = 'http://www.w3.org/2000/svg';
  const sparkline = (series, name) => {
    const from = apiHour - TREND_HOURS;
    const points = [[from, priceAt(series, from)], ...series.filter(([t]) => t > from), [apiHour + 1, undefined]];
    const values = points.map(([, price]) => price).filter(price => price != null);
    if (values.length < 1) return null;
    const low = Math.min(...values), high = Math.max(...values);
    const w = 84, h = 20, x = t => ((t - from) / (apiHour + 1 - from)) * w;
    const y = price => high === low ? h / 2 : 2 + (1 - (price - low) / (high - low)) * (h - 4);
    let d = '';
    for (let i = 0; i < points.length - 1; i += 1) {
      const [t, price] = points[i];
      if (price == null) continue;
      const end = points[i + 1][0];
      d += `M${x(t).toFixed(1)} ${y(price).toFixed(1)}H${x(end).toFixed(1)}`;
      const next = points[i + 1][1];
      if (next != null) d += `V${y(next).toFixed(1)}`;
    }
    const svg = document.createElementNS(SVG, 'svg');
    svg.setAttribute('class', 'mk-spark');
    svg.setAttribute('viewBox', `0 0 ${w} ${h}`);
    svg.setAttribute('width', w);
    svg.setAttribute('height', h);
    svg.setAttribute('role', 'img');
    const label = high === low
      ? `${name} 近 7 天最低價都是 ${moneyText(low)}`
      : `${name} 近 7 天最低價在 ${moneyText(low)} 到 ${moneyText(high)} 之間`;
    svg.setAttribute('aria-label', label);
    const title = document.createElementNS(SVG, 'title');
    title.textContent = label;
    const path = document.createElementNS(SVG, 'path');
    path.setAttribute('d', d);
    svg.append(title, path);
    return svg;
  };

  const renderRow = item => {
    const li = document.createElement('li');
    li.className = 'mk-row';
    if (!item.listed) li.classList.add('is-stale');

    const iconLink = document.createElement('a');
    iconLink.className = 'mk-icon';
    iconLink.href = `https://www.wowhead.com/forever/tw/item=${item.id}`;
    iconLink.target = '_blank';
    iconLink.rel = 'noopener noreferrer';
    iconLink.setAttribute('aria-label', `${item.name}：在 Wowhead 查看`);
    if (item.icon) {
      const img = document.createElement('img');
      img.src = `${ICON}${item.icon}.jpg`;
      img.alt = '';
      img.width = 36;
      img.height = 36;
      img.loading = 'lazy';
      img.decoding = 'async';
      iconLink.append(img);
    }

    const main = document.createElement('div');
    main.className = 'mk-main';
    const head = document.createElement('div');
    head.className = 'mk-head';
    const star = document.createElement('button');
    star.type = 'button';
    star.className = 'mk-star';
    const syncStar = () => {
      const on = favorites.has(item.id);
      star.textContent = on ? '★' : '☆';
      star.setAttribute('aria-pressed', String(on));
      star.setAttribute('aria-label', `收藏「${item.name}」`);
      star.title = on ? '取消收藏' : '收藏';
    };
    syncStar();
    star.addEventListener('click', () => {
      const on = !favorites.has(item.id);
      if (on) favorites.add(item.id); else favorites.delete(item.id);
      saveFavorites();
      syncStar();
      updateFavorites();
      notify(on ? `已收藏「${item.name}」` : `已取消收藏「${item.name}」`);
    });
    const name = document.createElement('button');
    name.type = 'button';
    name.className = `mk-name q${item.quality ?? 1}`;
    name.textContent = item.name;
    name.title = `複製「${item.name}」`;
    name.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(item.name);
        notify(`已複製「${item.name}」，到拍賣場搜尋欄貼上`);
      } catch {
        notify(`無法自動複製，請手動選取「${item.name}」`);
      }
    });
    const meta = document.createElement('p');
    meta.className = 'mk-meta';
    const labels = [classes[item.class], subclasses[`${item.class}.${item.subclass}`]].filter((v, i, all) => v && all.indexOf(v) === i);
    if (item.level) labels.push(`${item.level} 級`);
    meta.append(labels.join('・'));
    const amobi = document.createElement('a');
    amobi.href = `https://wowamobi.com/items/${item.id}`;
    amobi.target = '_blank';
    amobi.rel = 'noopener noreferrer';
    amobi.textContent = '阿莫比';
    amobi.setAttribute('aria-label', `${item.name}：在阿莫比看三間拍賣場行情`);
    meta.append(labels.length ? '・' : '', amobi);
    head.append(name, star);
    main.append(head, meta);

    const price = document.createElement('div');
    price.className = 'mk-price';
    const value = document.createElement('strong');
    for (const [amount, unit, cls] of money(item.now)) {
      const span = document.createElement('span');
      span.className = `mk-coin mk-${cls}`;
      span.append(String(amount), document.createElement('small'));
      span.lastChild.textContent = unit;
      value.append(span);
    }
    const detail = document.createElement('span');
    detail.className = 'mk-detail';
    const parts = [];
    if (item.units != null) parts.push(`${item.units} 個`);
    parts.push(item.when);
    detail.append(parts.join('・'));
    const delta = change(item);
    if (delta != null && Math.abs(delta) >= 0.005) {
      const tag = document.createElement('span');
      tag.className = delta < 0 ? 'mk-down' : 'mk-up';
      tag.textContent = ` 比 ${item.baseLabel} ${delta < 0 ? '▼' : '▲'}${Math.round(Math.abs(delta) * 100)}%`;
      detail.append(tag);
    }
    price.append(value, detail);
    const spark = item.series && sparkline(item.series, item.name);
    if (spark) price.append(spark);

    li.append(iconLink, main, price);
    return li;
  };

  const renderMore = () => {
    const slice = filtered.slice(shown, shown + PAGE);
    const fragment = document.createDocumentFragment();
    slice.forEach(item => fragment.append(renderRow(item)));
    list.append(fragment);
    shown += slice.length;
    const rest = filtered.length - shown;
    more.hidden = rest <= 0;
    more.textContent = `顯示更多（還有 ${rest.toLocaleString('zh-TW')} 件）`;
    summary.textContent = filtered.length
      ? `共 ${filtered.length.toLocaleString('zh-TW')} 件，顯示 ${shown.toLocaleString('zh-TW')} 件`
      : '沒有符合的物品；可以換個名稱，或把類型、品質改回「全部」。';
  };

  const fillCategories = () => {
    const select = form.elements.cat;
    const byClass = {};
    for (const key of Object.keys(subclasses)) (byClass[key.split('.')[0]] ||= []).push(key);
    for (const [classId, label] of Object.entries(classes)) {
      const group = document.createElement('optgroup');
      group.label = label;
      group.append(new Option(`${label}（全部）`, `c${classId}`));
      for (const key of byClass[classId] || []) {
        if (subclasses[key] && subclasses[key] !== label) group.append(new Option(`${label}・${subclasses[key]}`, `s${key}`));
      }
      select.append(group);
    }
  };

  let timer;
  form.addEventListener('input', () => { clearTimeout(timer); timer = setTimeout(apply, 150); });
  form.addEventListener('submit', event => { event.preventDefault(); apply(); });
  more.addEventListener('click', renderMore);

  favShare.addEventListener('click', async () => {
    const ids = [...favorites].sort((a, b) => a - b);
    const url = `${location.origin}${location.pathname}#fav=${ids.join('.')}`;
    try {
      await navigator.clipboard.writeText(url);
      favField.hidden = true;
      notify(`已複製分享連結（${ids.length} 件），貼給朋友就能看到這些物品`);
    } catch {
      favUrl.value = url;
      favField.hidden = false;
      favUrl.focus();
      favUrl.select();
      notify('無法自動複製，請手動複製下方的連結');
    }
  });
  sharedAdd.addEventListener('click', () => {
    const before = favorites.size;
    shared.filter(id => itemIds.has(id)).forEach(id => favorites.add(id));
    saveFavorites();
    const added = favorites.size - before;
    shared = null;
    form.elements.mine.checked = true;
    apply();
    notify(`已加入 ${added} 件到你的收藏`);
  });
  sharedExit.addEventListener('click', () => {
    shared = null;
    apply();
  });
  // Auctionator shopping lists: the starred items as one exact-match list, alone or with the
  // lists of the other personal pages (helpers from endgame/ah-copy.js).
  const shopping = window.wfpShoppingLists;
  const favoriteList = () => {
    const names = items.filter(item => favorites.has(item.id)).map(item => item.name)
      .sort((a, b) => a.localeCompare(b, 'zh-Hant-TW'));
    const terms = shopping ? shopping.exactTerms(names) : [...new Set(names)].map(name => `"${name}"`);
    return new Map(terms.length ? [[shopping ? shopping.FAV_LIST : '行情-收藏', terms]] : []);
  };
  const listText = lists => [...lists].map(([name, terms]) => [name, ...terms].join('^')).join('\n');
  const everyList = async () => {
    if (!shopping) return favoriteList();
    try {
      return await shopping.allLists([...favoriteList().values()][0] || []);
    } catch {
      notify('讀不到其他頁面，只用這頁的收藏');
      return favoriteList();
    }
  };
  const copyLists = async (lists, label) => {
    const text = listText(lists);
    try {
      await navigator.clipboard.writeText(text);
      ahField.hidden = true;
      notify(`已複製${label}，到拍賣小幫手「購買」分頁按「匯入」貼上`);
    } catch {
      ahText.value = text;
      ahField.hidden = false;
      ahText.focus();
      ahText.select();
      notify('無法自動複製，已選取匯入文字，請按 Ctrl+C 或 ⌘C');
    }
  };
  ahFav.addEventListener('click', () => copyLists(favoriteList(), `收藏清單（${favorites.size} 件）`));
  ahAll.addEventListener('click', async () => {
    const lists = await everyList();
    copyLists(lists, `全部 ${lists.size} 份清單`);
  });
  ahDownload.addEventListener('click', async () => {
    const lists = await everyList();
    const url = URL.createObjectURL(new Blob([listText(lists) + '\n'], { type: 'text/plain;charset=utf-8' }));
    const link = Object.assign(document.createElement('a'), { href: url, download: 'auctionator-shopping-lists.txt' });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });

  // Import: Auctionator's export ("清單^\"名稱\"^名稱;進階條件…" per line) or one name per line.
  // Quoted names must match exactly; bare ones also star every item whose name contains them.
  const importTerms = text => text.split(/\r?\n/).flatMap(line => {
    const parts = line.split('^');
    return (parts.length > 1 ? parts.slice(1) : parts).map(part => {
      const term = part.split(';')[0].trim();
      const exact = term.length > 1 && term.startsWith('"') && term.endsWith('"');
      return { text: exact ? term.slice(1, -1).trim() : term, exact };
    });
  }).filter(term => term.text);
  ahImport.addEventListener('click', () => {
    const byName = new Map();
    items.forEach(item => byName.set(item.name, [...(byName.get(item.name) || []), item.id]));
    const matched = new Set();
    const missed = [];
    for (const { text, exact } of importTerms(ahImportText.value)) {
      let ids = byName.get(text) || [];
      if (!ids.length && !exact) ids = items.filter(item => item.name.includes(text)).map(item => item.id);
      if (ids.length) ids.forEach(id => matched.add(id)); else if (!missed.includes(text)) missed.push(text);
    }
    if (!matched.size && !missed.length) {
      ahImportResult.textContent = '沒有讀到物品名稱，請貼上拍賣小幫手匯出的文字，或一行一個名稱。';
      return;
    }
    const before = favorites.size;
    matched.forEach(id => favorites.add(id));
    saveFavorites();
    const added = favorites.size - before;
    ahImportResult.textContent = `對到 ${matched.size} 件，新收藏 ${added} 件。`
      + (missed.length ? `${missed.length} 個名稱在行情資料裡找不到（多半是掃描時沒貨）：${missed.slice(0, 8).join('、')}${missed.length > 8 ? '…' : ''}` : '');
    if (added) {
      shared = null;
      form.elements.mine.checked = true;
      apply();
      notify(`已加入 ${added} 件到收藏`);
    } else {
      updateFavorites();
    }
  });

  // A pasted #fav= or filter link on an open page changes only the hash.
  // In-page anchors such as #sources also change the hash; only filter links carry "=".
  window.addEventListener('hashchange', () => {
    if (!items.length || !location.hash.includes('=')) return;
    readHash();
    apply();
  });

  const getJson = url => fetch(url, { cache: 'no-cache' }).then(response => {
    if (!response.ok) throw new Error(response.status);
    return response.json();
  });
  // On a local preview, ?auctions=<url> points the page at a test file.
  const local = ['localhost', '127.0.0.1'].includes(location.hostname);
  const auctionsUrl = (local && new URLSearchParams(location.search).get('auctions')) || AUCTIONS;
  const auctionsRequest = getJson(auctionsUrl).catch(() => null);

  getJson('./data.json')
    .then(async data => {
      latestDay = data.latestDay;
      classes = data.classes;
      subclasses = data.subclasses;
      items = data.items.map(row => Object.fromEntries(data.fields.map((field, i) => [field, row[i]])));
      itemIds = new Set(items.map(item => item.id));
      // ISO strings carry the owner's +08:00 offset; show them as written, not in the viewer's zone.
      const stamp = iso => iso ? `${iso.slice(0, 10).replaceAll('-', '.')} ${iso.slice(11, 16)}` : '';
      const scan = data.scanStartedAt ? stamp(data.scanStartedAt) : data.latestDay.replaceAll('-', '.');
      const saved = data.savedAt ? stamp(data.savedAt) : '';
      const savedShort = saved.slice(0, 10) === scan.slice(0, 10) ? saved.slice(11) : saved;

      // Use the API only when it is not older than the scan; a stalled collector should not hide a new scan.
      let auctions = await auctionsRequest;
      const scanTime = Date.parse(data.savedAt || data.scanStartedAt || data.latestDay);
      if (auctions && !(Date.parse(auctions.updatedAt) >= scanTime - 3 * 3600e3 && auctions.hours?.length)) auctions = null;
      apiHour = auctions ? auctions.hours[auctions.hours.length - 1] : null;
      merge(auctions, auctions && Date.parse(auctions.updatedAt) > scanTime);

      $('[data-market-scan]').textContent = `完整掃描 ${scan}`;
      $('[data-market-total]').textContent = `${items.length.toLocaleString('zh-TW')} 件物品`;
      const apiChip = $('[data-market-api]');
      if (apiChip && auctions) {
        apiChip.textContent = `官方 API ${stamp(auctions.updatedAt).slice(5)}`;
        apiChip.hidden = false;
      }
      $('[data-market-generated]').textContent = `完整掃描 / ${scan}${saved ? `・存檔 ${savedShort}` : ''}`
        + `${auctions ? `・官方 API ${stamp(auctions.updatedAt)}` : ''}・客戶端 ${data.build}`;
      fillCategories();
      readHash();
      form.hidden = false;
      apply();
    })
    .catch(() => {
      summary.textContent = '行情資料讀取失敗，請重新整理頁面。';
    });
})();
