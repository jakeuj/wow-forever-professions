import { formatTaipei, loadGuildSnapshot, watchGuildSnapshot } from './data-source.mjs?v=1';

const section = document.querySelector('#overview');
const status = section.querySelector('[data-overview-status]');
const content = section.querySelector('[data-overview-content]');

function fillDistribution(selector, rows) {
  const max = Math.max(1, ...rows.map(row => row.count));
  const items = rows.map(({ name, count }) => {
    const item = document.createElement('li');
    const label = document.createElement('span');
    label.textContent = name;
    const track = document.createElement('span');
    track.className = 'guild-distribution-track';
    track.setAttribute('aria-hidden', 'true');
    const bar = document.createElement('span');
    bar.style.width = `${count / max * 100}%`;
    track.append(bar);
    const amount = document.createElement('strong');
    amount.textContent = count.toLocaleString('zh-TW');
    item.append(label, track, amount);
    return item;
  });
  section.querySelector(selector).replaceChildren(...items);
}

function updateTime(selector, value, withTime) {
  const node = section.querySelector(selector);
  node.dateTime = value;
  node.textContent = formatTaipei(value, withTime);
}

function showUnavailable() {
  content.hidden = true;
  status.hidden = false;
  status.textContent = '公會概況暫無資料，請稍後再查看。';
}

status.hidden = false;
try {
  const overview = await loadGuildSnapshot('overview');
  section.querySelector('[data-overview-count]').textContent = overview.characterCount.toLocaleString('zh-TW');
  updateTime('[data-overview-created]', overview.createdAt, false);
  updateTime('[data-overview-updated]', overview.rosterUpdatedAt, true);
  fillDistribution('[data-overview-levels]', overview.levels.map((count, index) => ({
    name: `${index * 10 + 1}–${index * 10 + 10} 級`, count,
  })));
  fillDistribution('[data-overview-classes]', overview.classes);
  content.hidden = false;
  status.hidden = true;
  watchGuildSnapshot(overview, () => {
    status.hidden = false;
    status.textContent = '公會概況待更新，以下為上一份可用資料。';
  }, showUnavailable);
} catch {
  showUnavailable();
}
