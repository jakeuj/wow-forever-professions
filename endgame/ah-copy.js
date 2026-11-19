// Click an item name to copy the exact in-game name for the auction house search box.
// Markup: <span data-ah="配方：貓鼬藥劑">貓鼬藥劑</span>; without JavaScript it stays plain text.
// Containers marked data-ah-list="清單名稱" also become Auctionator shopping lists
// ("清單^\"名稱\"^..." per line); data-ah-prefix keeps a set prefix unquoted, and rows
// marked .is-skip are left out. Items starred on the market page join the full export as
// one more list, and window.wfpShoppingLists shares these helpers with market/market.js.
(() => {
  const PAGES = ['endgame', 'leveling', 'alchemy', 'alchemy-leveling', 'speculation'];
  const FAV_KEY = 'wfp.market.favorites'; // written by market/market.js
  const FAV_LIST = '行情-收藏';
  const ADDON_URL = 'https://www.curseforge.com/wow/addons/auctionator';

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

  const selectText = node => {
    const range = document.createRange();
    range.selectNodeContents(node);
    const selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
  };

  const collectLists = root => {
    const lists = new Map();
    root.querySelectorAll('[data-ah-list]').forEach(box => {
      const name = box.dataset.ahList;
      const terms = lists.get(name) || [];
      box.querySelectorAll('[data-ah]').forEach(node => {
        if (node.closest('.is-skip')) return;
        const term = node.hasAttribute('data-ah-prefix') ? node.dataset.ah : `"${node.dataset.ah}"`;
        if (!terms.includes(term)) terms.push(term);
      });
      if (terms.length) lists.set(name, terms);
    });
    return lists;
  };
  const listsText = lists => [...lists].map(([name, terms]) => [name, ...terms].join('^')).join('\n');
  const exactTerms = names => [...new Set(names)].map(name => `"${name}"`);

  // Read the lists before the spans below turn into buttons.
  const pageLists = collectLists(document);
  const currentPage = (location.pathname.match(/\/(endgame|leveling|alchemy|alchemy-leveling|speculation)\/(?:index\.html)?$/) || [])[1];

  // Names of the items starred on the market page (ids in localStorage, names in its data.json).
  const favoriteNames = async () => {
    let ids = [];
    try {
      ids = JSON.parse(localStorage.getItem(FAV_KEY) || '[]');
    } catch {
      return [];
    }
    if (!Array.isArray(ids) || !ids.length) return [];
    const response = await fetch(new URL('../market/data.json', location.href));
    if (!response.ok) return [];
    const data = await response.json();
    const id = data.fields.indexOf('id'), name = data.fields.indexOf('name');
    const names = new Map(data.items.map(row => [row[id], row[name]]));
    return ids.map(item => names.get(item)).filter(Boolean).sort((a, b) => a.localeCompare(b, 'zh-Hant-TW'));
  };

  // Every page's lists plus the starred items; pass favoriteTerms to use ones already in hand.
  const allLists = async favoriteTerms => {
    const merged = new Map();
    for (const page of PAGES) {
      let lists = pageLists;
      if (page !== currentPage) {
        const response = await fetch(new URL(`../${page}/`, location.href));
        if (!response.ok) throw new Error(`${page}: ${response.status}`);
        lists = collectLists(new DOMParser().parseFromString(await response.text(), 'text/html'));
      }
      lists.forEach((terms, name) => merged.set(name, terms));
    }
    const favorites = favoriteTerms || exactTerms(await favoriteNames().catch(() => []));
    if (favorites.length) merged.set(FAV_LIST, favorites);
    return merged;
  };

  window.wfpShoppingLists = { FAV_LIST, ADDON_URL, listsText, exactTerms, allLists };

  const items = document.querySelectorAll('[data-ah]');
  if (!items.length) return;

  items.forEach(item => {
    const name = item.dataset.ah;
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'ah-copy';
    button.dataset.ah = name;
    button.title = `複製「${name}」`;
    button.setAttribute('aria-label', `${item.textContent.trim()}：複製「${name}」到拍賣場搜尋`);
    const label = document.createElement('span');
    label.className = 'ah-copy-label';
    label.append(...item.childNodes);
    const icon = document.createElement('span');
    icon.className = 'ah-copy-icon';
    icon.setAttribute('aria-hidden', 'true');
    icon.textContent = '⧉';
    button.append(label, icon);
    item.replaceWith(button);

    let resetTimer;
    button.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(name);
        clearTimeout(resetTimer);
        button.classList.add('is-copied');
        resetTimer = setTimeout(() => button.classList.remove('is-copied'), 2000);
        notify(`已複製「${name}」，到拍賣場搜尋欄貼上`);
      } catch {
        const hidden = document.createElement('span');
        hidden.className = 'ah-copy-fallback';
        hidden.textContent = name;
        button.after(hidden);
        selectText(hidden);
        notify(`無法自動複製，已選取「${name}」，請按 Ctrl+C 或 ⌘C`);
        setTimeout(() => hidden.remove(), 8000);
      }
    });
  });

  const hint = document.querySelector('[data-ah-hint]');
  document.querySelectorAll('[data-ah-hint]').forEach(node => { node.hidden = false; });
  if (!pageLists.size || !hint) return;

  const panel = document.createElement('div');
  panel.className = 'eg-lists';
  const title = document.createElement('p');
  title.className = 'eg-lists-title';
  title.textContent = '拍賣小幫手購物清單：' + [...pageLists].map(([name, terms]) => `${name}（${terms.length}）`).join('、');
  const actions = document.createElement('div');
  actions.className = 'eg-lists-actions';
  const makeButton = text => {
    const button = document.createElement('button');
    button.type = 'button';
    button.className = 'button-compact';
    button.textContent = text;
    actions.append(button);
    return button;
  };
  const copyPage = makeButton('複製這頁清單');
  const copyAll = makeButton('複製全部頁面');
  const download = makeButton('下載全部 .txt');
  const howto = document.createElement('p');
  howto.className = 'eg-lists-note';
  howto.textContent = `在拍賣場打開「拍賣小幫手」的「購買」分頁，按左下「匯入」，貼上後再按「匯入」。同名清單會整份換成新的，你自己建的其他清單不受影響；搜尋全部就能看到沒貨的項目。「全部頁面」也會帶上在部落行情頁收藏的物品（清單「${FAV_LIST}」）。`;
  const addon = document.createElement('p');
  addon.className = 'eg-lists-note';
  const addonLink = Object.assign(document.createElement('a'), { href: ADDON_URL, target: '_blank', rel: 'noopener noreferrer', textContent: 'CurseForge 下載 ↗' });
  addon.append('還沒裝的話：拍賣小幫手（Auctionator）是免費的拍賣場插件，可以完整掃描整間拍賣場、記錄每天的最低價，並用購物清單一次搜尋多樣物品；', addonLink, '，用 CurseForge App 安裝時遊戲選 World of Warcraft 的永恆（Forever）版本。');
  const details = document.createElement('details');
  const summary = document.createElement('summary');
  summary.textContent = '顯示這頁的匯入文字';
  const textarea = document.createElement('textarea');
  textarea.className = 'eg-lists-text';
  textarea.readOnly = true;
  textarea.rows = Math.min(pageLists.size + 1, 6);
  textarea.value = listsText(pageLists);
  textarea.setAttribute('aria-label', '這頁的拍賣小幫手匯入文字');
  details.append(summary, textarea);
  panel.append(title, actions, howto, addon, details);
  hint.after(panel);

  const copyText = async (text, label) => {
    try {
      await navigator.clipboard.writeText(text);
      notify(`已複製${label}，到拍賣小幫手「購買」分頁按「匯入」貼上`);
    } catch {
      textarea.value = text;
      details.open = true;
      textarea.focus();
      textarea.select();
      notify('無法自動複製，已選取匯入文字，請按 Ctrl+C 或 ⌘C');
    }
  };

  copyPage.addEventListener('click', () => copyText(listsText(pageLists), `這頁的 ${pageLists.size} 份清單`));
  copyAll.addEventListener('click', async () => {
    try {
      const lists = await allLists();
      await copyText(listsText(lists), `全部頁面共 ${lists.size} 份清單`);
    } catch {
      notify('讀不到其他頁面，先改複製這頁的清單');
      await copyText(listsText(pageLists), `這頁的 ${pageLists.size} 份清單`);
    }
  });
  download.addEventListener('click', async () => {
    let lists;
    try {
      lists = await allLists();
    } catch {
      lists = pageLists;
      notify('讀不到其他頁面，只下載這頁的清單');
    }
    const url = URL.createObjectURL(new Blob([listsText(lists) + '\n'], { type: 'text/plain;charset=utf-8' }));
    const link = Object.assign(document.createElement('a'), { href: url, download: 'auctionator-shopping-lists.txt' });
    document.body.append(link);
    link.click();
    link.remove();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  });
})();
