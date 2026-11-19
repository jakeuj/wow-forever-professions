import { crafting, normalizeProgress, countPoints } from './data.mjs?v=20261119-guild';

const storageKey = 'wow-forever-professions:milestones:v1';

export function initMilestones(notify) {
  const $ = selector => document.querySelector(selector);
  const originalStorageNote = $('#storage-note').textContent;
  let progress = normalizeProgress(null);
  let storageAvailable = true;

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
    $('#storage-note').textContent = storageAvailable ? originalStorageNote : '此瀏覽器無法儲存本機資料；進度會保留在目前頁面，重新開啟後需重新設定。';
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

  renderProgress();
}
