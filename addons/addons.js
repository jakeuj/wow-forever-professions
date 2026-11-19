const filters = document.querySelector('#addon-filters');
const query = document.querySelector('#addon-search');
const category = document.querySelector('#addon-category');
const status = document.querySelector('#addon-status');
const empty = document.querySelector('#addon-empty');

const normalize = (value) => value.normalize('NFKC').toLocaleLowerCase('zh-TW');
const groups = Array.from(document.querySelectorAll('[data-addon-group]'), (section) => ({
  section,
  cards: Array.from(section.querySelectorAll('.addon-card'), (card) => ({
    card,
    text: normalize(card.textContent),
  })),
}));

function updateResults() {
  const terms = normalize(query.value).trim().split(/\s+/).filter(Boolean);
  let total = 0;

  for (const { section, cards } of groups) {
    const inCategory = !category.value || category.value === section.dataset.addonGroup;
    let visible = 0;

    for (const { card, text } of cards) {
      card.hidden = !inCategory || !terms.every((term) => text.includes(term));
      if (!card.hidden) visible += 1;
    }

    section.hidden = visible === 0;
    total += visible;
  }

  status.textContent = `顯示 ${total} 項插件`;
  empty.hidden = total > 0;
}

query.addEventListener('input', updateResults);
category.addEventListener('change', updateResults);
filters.querySelector('button').addEventListener('click', () => {
  filters.reset();
  updateResults();
  query.focus();
});
filters.addEventListener('submit', (event) => event.preventDefault());
updateResults();
filters.hidden = false;
