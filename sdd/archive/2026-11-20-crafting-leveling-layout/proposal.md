# 製造練等頁版面調整

需求類型為重構。本文件依已上線的版面回溯整理。

## 為什麼做

製造練等頁把六項專業接在同一頁，每項都預先展開 1 → 150 的配方與採買明細。從鍛造 187 → 225 的預填連結進站時，使用者也要捲過其他專業的明細。參考 WOWF.IO 以單一專業呈現技能區間、配方與材料的安排。[WOWF.IO 鍛造快速升級](https://wowf.io/en/professions/blacksmithing/leveling)

## 要改什麼

- 將升級路線接在試算下方，一次顯示一項專業。初次開啟時依預填專業顯示路線，也可在路線區切換六項專業。
- 每項專業先列出 1 → 150、150 → 225、225 → 300 的費用與適用提示，展開後顯示製作及採買明細。舊階段連結可直接展開指定明細。
- 將六項預算與起手順序移到路線後方並預設收合。頁首的預算入口與起手順序連結可直接展開並定位。
- 手機版的六項專業選項排成兩列，每列三項。

## 影響範圍

- `crafting-leveling/index.html`、`scripts/crafting-leveling.html` 與 `scripts/build-crafting-leveling.py` 負責頁面結構及階段明細的產生。
- `crafting-leveling/crafting-leveling.js` 負責選擇專業與開啟錨點，`crafting-leveling/crafting-leveling.css` 負責版面及手機配置。

版面於 2026-11-20 發布至正式站。[版面調整 commit `c3866b6`](https://github.com/jakeuj/wow-forever-professions/commit/c3866b65a95eba5b2b6d04e534d5dc77fd5b3f93) · [GitHub Pages 部署紀錄](https://github.com/jakeuj/wow-forever-professions/actions/runs/44583837912)
