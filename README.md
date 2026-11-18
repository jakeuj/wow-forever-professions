# auction-data

《魔獸世界：永恆》亞服 PvP 部落拍賣場（Battle.net API TW 區 113 號）的每小時最低一口價，由 `main` 分支的 `.github/workflows/auction-collect.yml` 自動寫入 `auctions.json`，給[部落拍賣行情頁](https://jakeuj.com/wow-forever-professions/market/)讀取。

請勿手動修改。格式見 `main` 分支的 `scripts/collect-auctions.py`。官方 API 只有不能堆疊的物品（裝備、武器、配方），材料與藥水不在其中。
