import { professions, crafting, plans, paladinRoutes, getPaladinRoute, getRows, summarize, normalizeProgress, countPoints } from './data.mjs?v=20261111-guild';

const $ = selector => document.querySelector(selector);
const storageKey = 'wow-forever-professions:milestones:v1';
const byId = Object.fromEntries(professions.map(p => [p.id, p]));
const tabs = [...document.querySelectorAll('[data-plan]')];
let selectedPlan = 'crafting';
let selectedStage = 'start';
let selectedPaladinRoute = 'keep';
let progress = normalizeProgress(null);
let storageAvailable = true;
let toastTimer;

function notify(message) {
  const toast = $('#toast');
  toast.textContent = message;
  toast.classList.add('visible');
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => toast.classList.remove('visible'), 3200);
}

function readHash() {
  const params = new URLSearchParams(location.hash.slice(1));
  if (Object.hasOwn(plans, params.get('plan'))) selectedPlan = params.get('plan');
  if (params.get('stage') === 'start' || params.get('stage') === 'final') selectedStage = params.get('stage');
  if (Object.hasOwn(paladinRoutes, params.get('route'))) selectedPaladinRoute = params.get('route');
  else if (params.get('plan') === 'paladin') selectedPaladinRoute = 'keep';
}

function writeHash() {
  const params = new URLSearchParams({ plan: selectedPlan });
  if (selectedPlan === 'gathering') params.set('stage', selectedStage);
  if (selectedPlan === 'paladin') params.set('route', selectedPaladinRoute);
  history.replaceState(null, '', `${location.pathname}${location.search}#${params}`);
}

function renderPlan() {
  const plan = plans[selectedPlan];
  const route = selectedPlan === 'paladin' ? getPaladinRoute(selectedPaladinRoute) : null;
  const rows = getRows(selectedPlan, selectedStage, selectedPaladinRoute);
  const summary = summarize(rows);
  tabs.forEach(tab => {
    const active = tab.dataset.plan === selectedPlan;
    tab.setAttribute('aria-selected', String(active));
    tab.tabIndex = active ? 0 : -1;
  });
  $('#plan-panel').setAttribute('aria-labelledby', `tab-${selectedPlan}`);
  $('#plan-tag').textContent = route ? `${plan.tag} / 路線 ${route.letter}` : plan.tag;
  $('#plan-title').textContent = route?.title || plan.title;
  $('#plan-description').textContent = route?.description || plan.description;
  $('#stage-switch').hidden = selectedPlan !== 'gathering';
  $('#paladin-routes').hidden = selectedPlan !== 'paladin';
  document.querySelectorAll('[data-paladin-route]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.paladinRoute === selectedPaladinRoute)));
  if (route) {
    $('#route-change').textContent = route.change;
    $('#route-flow').textContent = route.flow;
    $('#route-fit').textContent = route.fit;
  }
  document.querySelectorAll('[data-stage]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.stage === selectedStage)));
  $('#roster').innerHTML = rows.map(row => {
    const points = row.profs.filter(id => byId[id].kind === 'craft').length * 3;
    const pair = [...row.profs.map(id => `<span class="profession-chip ${byId[id].kind === 'craft' ? 'crafting' : ''}">${byId[id].name}</span>`), ...(row.flexibleSlot ? ['<span class="profession-chip flexible">彈性一格</span>'] : [])].join('<i aria-hidden="true">＋</i>');
    return `<article class="character-row" data-class="${row.classId}"><span class="row-order">${row.order}</span><div class="class-cell"><span class="class-seal ${row.classId}" aria-hidden="true">${row.seal}</span><div><h4>${row.name}</h4><small>${row.role}</small></div></div><div class="profession-pair">${pair}</div><p class="row-reason">${row.reason}</p><span class="row-points">＋${points}<small>傳承上限</small></span></article>`;
  }).join('');
  $('#plan-note').textContent = route?.note || (selectedPlan === 'gathering' && selectedStage === 'start' ? plan.startNote : plan.note);
  $('#coverage-summary').textContent = `${summary.covered} / 9 專業覆蓋 · ${summary.craftCharacters} 位製造工匠 · ${summary.points} 點上限`;
  $('#coverage-grid').innerHTML = professions.map(p => `<div class="coverage-item ${summary.ids.has(p.id) ? '' : 'missing'}"><span class="sr-only">${summary.ids.has(p.id) ? '已涵蓋：' : '尚缺：'}</span>${p.name}</div>`).join('');
}

$('#paladin-route-options').innerHTML = Object.entries(paladinRoutes).map(([id, route]) => {
  const count = summarize(route.rows).craftCharacters;
  return `<button type="button" class="route-option" data-paladin-route="${id}" aria-pressed="${id === selectedPaladinRoute}"><span class="route-letter">${route.letter}${route.recommended ? '<em>優先考慮</em>' : ''}</span><strong>${route.label}</strong><span class="route-pair">${route.pair}</span><small>${route.short} · ${count} 位製造角色</small></button>`;
}).join('');
document.querySelectorAll('[data-paladin-route]').forEach(button => button.addEventListener('click', () => {
  selectedPaladinRoute = button.dataset.paladinRoute;
  renderPlan();
  writeHash();
}));

tabs.forEach((tab, index) => {
  tab.addEventListener('click', () => { selectedPlan = tab.dataset.plan; renderPlan(); writeHash(); });
  tab.addEventListener('keydown', event => {
    let next;
    if (event.key === 'ArrowRight') next = (index + 1) % tabs.length;
    if (event.key === 'ArrowLeft') next = (index + tabs.length - 1) % tabs.length;
    if (event.key === 'Home') next = 0;
    if (event.key === 'End') next = tabs.length - 1;
    if (next === undefined) return;
    event.preventDefault();
    tabs[next].click();
    tabs[next].focus();
  });
});

document.querySelectorAll('[data-stage]').forEach(button => button.addEventListener('click', () => {
  selectedStage = button.dataset.stage;
  renderPlan();
  writeHash();
}));

window.addEventListener('hashchange', () => { readHash(); renderPlan(); });

// Guild navigation keeps the active profession route in the share URL.
document.querySelectorAll('[data-guild-link]').forEach(link => link.addEventListener('click', event => {
  if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
  event.preventDefault();
  $('#guild-title').focus({ preventScroll: true });
  $('#guild').scrollIntoView({ block: 'start' });
}));

document.querySelectorAll('[data-copy-target]').forEach(button => {
  button.hidden = false;
  button.addEventListener('click', async () => {
    const text = document.getElementById(button.dataset.copyTarget).textContent.trim();
    const status = $('#guild-copy-status');
    status.textContent = '';
    try {
      await navigator.clipboard.writeText(text);
      status.textContent = `已複製「${text}」`;
    } catch {
      status.textContent = '無法自動複製，請選取上方文字手動複製。';
    }
  });
});

$('#copy-plan').addEventListener('click', async () => {
  const rows = getRows(selectedPlan, selectedStage, selectedPaladinRoute);
  const summary = summarize(rows);
  const route = selectedPlan === 'paladin' ? getPaladinRoute(selectedPaladinRoute) : null;
  const phase = route ? `（路線 ${route.letter}：${route.label}）` : selectedPlan === 'gathering' ? `（${selectedStage === 'start' ? '開局階段' : '長期配置'}）` : '';
  const shareUrl = new URL(location.href);
  shareUrl.hash = new URLSearchParams({ plan: selectedPlan, ...(selectedPlan === 'gathering' ? { stage: selectedStage } : {}), ...(route ? { route: selectedPaladinRoute } : {}) }).toString();
  const text = [`魔獸世界：永恆｜${plans[selectedPlan].label}${phase}`, ...rows.map(row => `${row.name}：${[...row.profs.map(id => byId[id].name), ...(row.flexibleSlot ? ['彈性一格'] : [])].join('／')}`), ...(route ? ['', `聖騎士調整：${route.change}`, `材料流向：${route.flow}`] : []), '', `${summary.covered}/9 專業覆蓋，${summary.craftCharacters} 位製造工匠，${summary.points} 點製造傳承上限（非已取得點數）。`, '技能 150／225／300，帳號首次里程碑各 1 點。', shareUrl.href].join('\n');
  try {
    await navigator.clipboard.writeText(text);
    notify('已複製分配表與方案連結');
  } catch {
    const dialog = document.createElement('dialog');
    dialog.className = 'copy-dialog';
    dialog.innerHTML = '<h2>複製分配表</h2><p>選取以下文字，即可手動複製。</p><textarea aria-label="分配表文字" readonly></textarea><form method="dialog"><button class="button button-gold">關閉</button></form>';
    dialog.querySelector('textarea').value = text;
    document.body.append(dialog);
    dialog.addEventListener('close', () => dialog.remove());
    dialog.showModal();
    dialog.querySelector('textarea').select();
  }
});

try {
  progress = normalizeProgress(JSON.parse(localStorage.getItem(storageKey)));
} catch {
  progress = normalizeProgress(null);
  try { localStorage.getItem(storageKey); } catch { storageAvailable = false; }
}

$('#milestone-rows').innerHTML = crafting.map(p => `<div class="milestone-row"><span class="milestone-name"><span class="profession-mark" aria-hidden="true">${p.mark}</span>${p.name}</span>${[1, 2, 3].map(rank => `<span class="milestone-dot" data-milestone="${p.id}-${rank}" role="img" aria-label="${p.name} ${[150, 225, 300][rank - 1]} 尚未達成"></span>`).join('')}<select data-progress="${p.id}" aria-label="${p.name}目前階段"><option value="0">未達 150</option><option value="1">已達 150</option><option value="2">已達 225</option><option value="3">已達 300</option></select></div>`).join('');

function renderProgress() {
  const points = countPoints(progress);
  $('#earned-points').textContent = points;
  $('#legacy-progress').setAttribute('aria-valuenow', String(points));
  $('#legacy-progress>span').style.width = `${points / 18 * 100}%`;
  crafting.forEach(p => {
    const rank = progress[p.id];
    $(`[data-progress="${p.id}"]`).value = String(rank);
    [1, 2, 3].forEach(step => {
      const dot = $(`[data-milestone="${p.id}-${step}"]`);
      dot.classList.toggle('complete', rank >= step);
      dot.setAttribute('aria-label', `${p.name} ${[150, 225, 300][step - 1]} ${rank >= step ? '已達成' : '尚未達成'}`);
    });
  });
  $('#progress-description').textContent = points === 18 ? '六項製造里程碑全數完成。18 點製造傳承，已全部記錄！' : points >= 16 ? '製造點數已達首發每角色可投入的 16 點；仍可繼續完成其餘里程碑。' : points >= 12 ? '已累積 12 點以上，繼續往各專業的 300 點里程碑推進。' : points >= 6 ? '已累積 6 點以上，下一步可把各項製造推到 225。' : '先讓六項製造各到 150，累積第一輪 6 點。';
  if (!storageAvailable) $('#storage-note').textContent = '此瀏覽器無法儲存本機資料；進度會保留在目前頁面，重新開啟後需重新設定。';
}

function saveProgress() {
  try { localStorage.setItem(storageKey, JSON.stringify(progress)); storageAvailable = true; }
  catch { storageAvailable = false; }
  renderProgress();
}

document.querySelectorAll('[data-progress]').forEach(select => select.addEventListener('change', () => {
  progress[select.dataset.progress] = Number(select.value);
  saveProgress();
}));

$('#reset-progress').addEventListener('click', () => {
  progress = normalizeProgress(null);
  saveProgress();
  notify('已清除這個瀏覽器的製造進度');
});

window.addEventListener('storage', event => {
  if (event.key !== storageKey && event.key !== null) return;
  try { progress = normalizeProgress(JSON.parse(event.newValue)); } catch { progress = normalizeProgress(null); }
  renderProgress();
});

readHash();
renderPlan();
renderProgress();
