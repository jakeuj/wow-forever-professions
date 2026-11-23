# auction-data

《魔獸世界：永恆》亞服 PvP 部落拍賣場（Battle.net API TW 區 113 號）的官方拍賣快照。`main` 分支的 `.github/workflows/auction-collect.yml` 每小時自動寫入，請勿手動修改。

- `auctions.json`：每件物品的最低一口價（能堆疊的物品記單價）與目前件數，供[部落拍賣行情頁](https://jakeuj.com/wow-forever-professions/market/)讀取。2026-11-19 起也包含 `/commodities` 的材料、藥水等能堆疊物品。
- `hourly/<台灣日期>.jsonl`：2026-11-23 起每次快照寫一行，記錄能堆疊物品的最低單價、上架件數與最便宜 20 件的平均單價。這些資料用來比較不同時段與星期幾的價格（技能的 `auction_hours.py`），行情頁不讀取。

格式說明見 `main` 分支 `scripts/collect-auctions.py` 的開頭。
