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

### 1. 測角色與專業端點

角色端點（含 `/professions`）需要一隻 Lv10 以上、登出過的角色，這次沒有測。

1. 設 repo Secret。會提示輸入 `名字-姓氏`，不會留在歷史紀錄：

   ```powershell
   gh secret set FOREVER_PROBE_CHARACTER
   ```

2. 跑探測並下載結果：

   ```powershell
   gh workflow run api-probe.yml -f regions=tw
   gh run list --workflow api-probe.yml -L 1
   gh run download <run id> -n api-probe
   ```

3. 把角色端點的結果（哪些 200、`professions` 的欄位結構：技能點、已學配方）補進 battlenet-api.md 的端點實測表。報告只留欄位與筆數，不會有角色名，也不要手動寫進去。

### 2. Windows 本機查詢

PowerShell 設定本次視窗的憑證（client ID／secret 在 Battle.net 開發者入口的 API Access）：

```powershell
$env:BLIZZARD_CLIENT_ID = '<client id>'
$env:BLIZZARD_CLIENT_SECRET = Read-Host 'client secret' -MaskInput
python .agents\skills\wow-forever\scripts\forever_api.py get /data/wow/ruleset/index
python .agents\skills\wow-forever\scripts\forever_api.py character '<名字-姓氏>' --part professions
```

`Read-Host -MaskInput` 要 PowerShell 7；Windows PowerShell 5.1 改用 `-AsSecureString` 再轉回字串，或直接在終端機貼上（貼上的值會留在歷史）。Mac 上改用鑰匙圈：`security add-generic-password -s wow-forever-battlenet -a '<client id>' -w`。

### 3. 拍賣 commodities 被漏抓（重要）

探測發現 `/data/wow/ruleset/{id}/auctions/{houseId}/commodities` 有資料，但清單的 key 是 `auctions`，不是 `commodities`。聯盟 110 號有 11,725 筆。

`scripts/collect-auctions.py` 第 117 行與 `scripts/probe-auction-api.py` 第 150 行讀的是 `payload["commodities"]`，所以一直當成空的。技能裡「API 只有不能堆疊的物品、材料行情只能靠拍賣小幫手」的結論可能是這個 bug 造成的。

1. 欄位已在 run 44290944141 確認：每筆有 `id`、`item.id`、`quantity`、`unit_price`、`time_left`。`scripts/blizzard_api.py` 的 `lowest_prices()` 本來就會處理 `unit_price`。
2. 修這兩支腳本：改讀 `auctions` key，並保留讀 `commodities` 的相容寫法。最小改法是 `payload.get("commodities") or payload.get("auctions")`。
3. 手動跑 `auction-probe.yml`，重新比對部落 113 的材料價與拍賣小幫手掃描。
4. 確認後更新：
   - 技能的 battlenet-api.md「拍賣場」與 market-recipe-value.md
   - public-data-sources.md 的增強方向第 3 點
   - README 的官方拍賣價說明
   - 行情頁是否改用 API 的材料價（`market/market.js` 的價格來源規則）

### 4. 可以接著做的網站改進（依實測結果）

- `media/item` 有官方物品圖示（render.worldofwarcraft.com），`search/item` 可用繁中名稱搜尋。`scripts/build-market-data.py` 目前用 Wowhead 補圖示與名稱，可評估改用官方 API；官方建議把圖片存到自己的空間，不要熱連結。
- profession → skill tier → recipe 有配方、材料與成品（zh_TW），可以替代或交叉檢查阿莫比與客戶端資料表；但 recipe 沒有技能點顏色，練等點數仍要用客戶端資料表或 wowf.io。
