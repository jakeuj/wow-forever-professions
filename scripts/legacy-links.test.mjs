import test from 'node:test';
import assert from 'node:assert/strict';
import { legacyPlannerUrl } from '../guild/legacy-links.mjs';

const base = 'https://jakeuj.com/wow-forever-professions/';

test('舊方案轉址保留階段、路線及原始查詢字串', () => {
  for (const hash of ['#plan=crafting', '#plan=gathering&stage=final', '#plan=paladin&route=warlock']) {
    const suffix = `?ref=%2F&source=bahamut${hash}`;
    assert.equal(legacyPlannerUrl(`${base}${suffix}`), `${base}professions/${suffix}`);
  }
});

test('舊專業區段轉到相同錨點，index.html 與本機根目錄也可使用', () => {
  for (const anchor of ['plans', 'legacy', 'principles', 'sources']) {
    assert.equal(legacyPlannerUrl(`${base}index.html#${anchor}`), `${base}professions/#${anchor}`);
  }
  assert.equal(legacyPlannerUrl('http://localhost:8765/#plan=balanced'), 'http://localhost:8765/professions/#plan=balanced');
});

test('公會首頁、招募與工具區段維持原路徑', () => {
  for (const suffix of ['', '?source=bahamut', '#guild', '#tools', '#join', '#top', '#unknown', '#notplan=crafting']) {
    assert.equal(legacyPlannerUrl(`${base}${suffix}`), null);
  }
});
