(() => {
  const scan = document.getElementById('cl-scan');
  const stale = document.getElementById('cl-stale');
  const checkAge = () => {
    stale.hidden = Date.now() - Date.parse(scan.dateTime) <= 48 * 60 * 60 * 1000;
  };

  const links = [...document.querySelectorAll('#routes .cl-jump a')];
  const professions = links.map(link => document.getElementById(link.hash.slice(1)));
  const select = document.querySelector('#leveling-form select[name="profession"]');
  const preset = new URLSearchParams(location.search).get('profession');

  const showProfession = id => {
    const selected = professions.find(profession => profession.id === id) ?? professions[0];
    professions.forEach((profession, index) => {
      profession.hidden = profession !== selected;
      if (profession === selected) links[index].setAttribute('aria-current', 'true');
      else links[index].removeAttribute('aria-current');
    });
  };

  const revealLocation = () => {
    const target = document.getElementById(location.hash.slice(1));
    const profession = target?.closest('.cl-profession');
    showProfession(profession?.id || select.value || preset);
    const details = target?.closest('details');
    if (details) details.open = true;
    if (profession || details) target.scrollIntoView();
  };

  for (const link of links) {
    link.addEventListener('click', event => {
      if (event.button !== 0 || event.metaKey || event.ctrlKey || event.shiftKey || event.altKey) return;
      event.preventDefault();
      if (location.hash !== link.hash) history.pushState(null, '', link.hash);
      showProfession(link.hash.slice(1));
    });
  }
  select.addEventListener('change', () => showProfession(select.value));
  document.addEventListener('click', event => {
    if (event.defaultPrevented || !location.hash) return;
    if (event.target.closest('a[href^="#"]')?.hash === location.hash) revealLocation();
  });
  checkAge();
  window.addEventListener('pageshow', checkAge);
  window.addEventListener('hashchange', revealLocation);
  revealLocation();
})();
