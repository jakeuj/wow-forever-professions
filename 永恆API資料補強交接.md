# 永恆 API 資料補強：進度與待辦

2026-11-18 開始。目標：把 Battle.net 官方 API 指南與「永恆實際能用哪些端點」補進 wow-forever 技能，並提供本機查詢工具。完成後刪掉這份交接檔。

## 已完成

- 官方開發者入口（WoW、WoW Classic 共 20 頁指南與 API 參考）沒有任何永恆章節。指南重點整理在技能的 [references/battlenet-api.md](.agents/skills/wow-forever/references/battlenet-api.md)「官方指南重點」。
- 新工具（都在 `.agents/skills/wow-forever/scripts/`）：
  - `forever_api.py`：本機查任何 API 路徑，自動選 namespace。憑證讀環境變數，macOS 另可讀鑰匙圈 `wow-forever-battlenet`。
  - `forever_api_coverage.py`：讀官方 Retail＋Classic 端點清單（218 個），換成永恆路徑逐一呼叫，輸出 Markdown 與 JSON。
- `.github/workflows/api-probe.yml`：手動觸發，用 repo Secrets 跑涵蓋率探測。結果在 Step Summary 與 `api-probe` artifact。
- 已在 Actions 跑過（沒有測試角色）：
  - [run 44290066755](https://github.com/jakeuj/wow-forever-professions/actions/runs/44290066755)
  - [run 44290944141](https://github.com/jakeuj/wow-forever-professions/actions/runs/44290944141)，這次多記錄每個清單第一筆的欄位
  - 結果寫進 battlenet-api.md 的「實測結論」與「端點實測表」。
- 技能文件：
  - `SKILL.md` 指到新檔。
  - `public-data-sources.md` 的 API 段落縮成摘要，「依需求選來源」表已依實測更新。
  - README 補上 `api-probe.yml` 與本機工具。

## 待辦（回家在 Windows 繼續）

### 1. 測角色與專業端點（2026-11-19 完成）

已設 `FOREVER_PROBE_CHARACTER`，[run 44447493169](https://github.com/jakeuj/wow-forever-professions/actions/runs/44447493169) 測了角色端點：31 個中 25 個回 200，結果已寫進 battlenet-api.md。報告與 artifact 裡沒有角色名。

還沒確認：`professions` 的 `tiers[]` 中技能點欄位的實際名稱。探測只記三層欄位，要用本機 `forever_api.py character … --part professions` 看一次再補進文件。

### 2. Windows 本機查詢

PowerShell 設定本次視窗的憑證（client ID／secret 在 Battle.net 開發者入口的 API Access）：

```powershell
$env:BLIZZARD_CLIENT_ID = '<client id>'
$env:BLIZZARD_CLIENT_SECRET = Read-Host 'client secret' -MaskInput
python .agents\skills\wow-forever\scripts\forever_api.py get /data/wow/ruleset/index
python .agents\skills\wow-forever\scripts\forever_api.py character '<名字-姓氏>' --part professions
```

`Read-Host -MaskInput` 要 PowerShell 7；Windows PowerShell 5.1 改用 `-AsSecureString` 再轉回字串，或直接在終端機貼上（貼上的值會留在歷史）。Mac 上改用鑰匙圈：`security add-generic-password -s wow-forever-battlenet -a '<client id>' -w`。

### 3. 拍賣 commodities 被漏抓：已修正（2026-11-19）

收集與探測腳本改成兩種 key 都讀，每小時資料從 2026-11-19 起包含材料與藥水，行情頁的「官方已沒貨」也套用到所有類別。之後幾天留意 `auctions.json` 的大小：能堆疊的物品每小時價格變動較多，7 天逐小時的資料可能長到 1 MB 左右；太大時可縮短 `--hourly-days`。

### 4. 可以接著做的網站改進（依實測結果）

- `media/item` 有官方物品圖示（render.worldofwarcraft.com），`search/item` 可用繁中名稱搜尋。`scripts/build-market-data.py` 目前用 Wowhead 補圖示與名稱，可評估改用官方 API；官方建議把圖片存到自己的空間，不要熱連結。
- profession → skill tier → recipe 有配方、材料與成品（zh_TW），可以替代或交叉檢查阿莫比與客戶端資料表；但 recipe 沒有技能點顏色，練等點數仍要用客戶端資料表或 wowf.io。
