# 公開資料來源與官方 API

查證日期：2026-11-13（Asia/Taipei）。以下是當日快照，用來規劃網站資料整合與回答「哪裡查得到」。每項標註可信度：

- **官方文件**：Blizzard 開發者入口或官方頁面寫明。
- **社群實測**：Blizzard 未文件化，來自開發者論壇與第三方函式庫的探測，可能無預警變動。
- **本次實測**：查證當日直接請求取得的結果。

寫進網站或回答「目前」狀態前，先依[重新查證](#重新查證)重跑對應項目，並在網站資料中保留來源與日期。

## 依需求選來源

| 需要的資料 | 首選來源 | 備援與限制 |
| --- | --- | --- |
| 目前客戶端版本 | [TACT 版本伺服器](#客戶端版本與資料表) | wago.tools builds |
| 物品名稱、品質、圖示（繁中） | [客戶端資料表](#客戶端版本與資料表)、[官方物品 API](battlenet-api.md#實測結論)、[Wowhead](#wowhead-永恆繁中) | 客戶端 `ItemSparse` 只有約六成物品；官方 `item`／`media/item` 有 zh_TW 名稱與圖示，但約四成拍賣物品回 404，Wowhead 補剩下的 |
| 專業配方、技能點、材料 | [官方專業 API](battlenet-api.md#實測結論)、客戶端資料表 | API 有配方、材料與成品，沒有變色點數；點數用客戶端資料表。學費與訓練師位置只在伺服器端 |
| 拍賣行情 | [官方拍賣 API](battlenet-api.md#拍賣場) | 插件掃描只看得到掛單價；回答玩家當下的行情問題用阿莫比，見 [market-recipe-value.md](market-recipe-value.md) |
| 角色等級、裝備、專業 | [官方角色 API](battlenet-api.md#角色與公會) | Lv10 以上且登出後才出現 |
| 公會成員 | 官方公會 roster | 中文公會名直接當 slug 可查（2026-11-18 實測「黎明之劍」） |
| 任務內容與獎勵 | [官方任務 API](battlenet-api.md#端點實測表) | 有 zh_TW 標題、需求與獎勵；沒有 NPC 位置 |
| 掉落、NPC 位置 | 無官方來源（副本手冊 API 為空）；[插件群眾回報](#遊戲內插件收集) | 經典版資料只能標示為參考 |
| 伺服器人口 | 無官方來源；插件抽樣 | 只代表被看到的角色，適合看比例 |
| 官方公告 | [台灣新聞頁](#官方新聞與論壇) | 未找到 RSS／JSON |
| 藍帖、BUG 回報 | 台灣官方論壇 JSON／RSS | Discourse 標準端點 |

## Battle.net API（永恆）

官方開發者入口到 2026-11-18 仍只有 Retail 與 Classic 的文件，永恆的 namespace、ruleset、角色、公會、拍賣與逐端點可用性都整理在 [battlenet-api.md](battlenet-api.md)。該檔另含官方指南重點（OAuth、區域與語系、搜尋語法、媒體）、本機查詢工具 `scripts/forever_api.py` 與涵蓋率探測 `api-probe.yml`。

速記：

- Token 用 client credentials，主機 `https://tw.api.blizzard.com`、`locale=zh_TW`；namespace 是 `static-forever-tw`、`dynamic-forever-tw`、`profile-forever-tw`。
- 永恆沒有 realm，改用 ruleset；角色以 `{name}-{surname}` 查詢，要 Lv10 以上且登出後才有資料。
- 拍賣在 `/data/wow/ruleset/{id}/auctions/{houseId}`，亞服 PvP 部落是 113；單間端點只有不能堆疊的物品，能堆疊的在 `/commodities`，清單 key 是 `auctions`。
- 專業、配方、物品、物品圖示、搜尋、任務都有 zh_TW 資料；副本手冊是空的。

## 客戶端版本與資料表

可信度：本次實測（2026-11-13）。

- 版本：`http://{region}.patch.battle.net:1119/wowf/versions` 以 `|` 分隔，`VersionsName` 欄是版本號。產品代碼 `wowf` 與安裝根目錄 `.build.info` 的 Product 相同。當日各區皆為 `1.60.1.70938`。
- [wago.tools](https://wago.tools/)：`https://wago.tools/api/builds` 的 `wowf` 陣列列出歷次版本與建立時間（當日 `70938`、11/10 `70888`、11/07 `70862`）。
- 資料表 CSV：`https://wago.tools/db2/{表名}/csv?build={版本}&locale=zhTW`。例如 `ItemSparse` 的 `Display_lang` 是繁中物品名，物品 19019 為「雷霆之怒，逐風者的祝福之劍」。
- 專業相關資料表：`SkillLine`（專業）、`SkillLineAbility`（配方所屬專業，以及 `MinSkillLineRank`、`TrivialSkillLineRankLow`／`High` 技能點）、`ItemSparse`／`Item`（成品與材料）。材料與成品的對應在法術相關資料表，欄位依當版 schema 確認。
- 物品覆蓋率（2026-11-18，build `70938`）：`ItemSparse` 19,325 列，`Item` 32,008 列。部落拍賣場完整掃描的 2,803 件物品只有 1,633 件在 `ItemSparse`，其餘的名稱由伺服器下發，要用 Wowhead 補；`Item` 涵蓋全部，可取 `ClassID`／`SubclassID`，再用 `ItemClass`、`ItemSubClass` 的繁中名稱當分類。另有少數名稱仍是「[英文]」未翻譯。
- 各區版本可能不同步：2026-11-18 美服已是 `70959`，台服、韓服仍是 `70938`。查名稱用安裝目錄 `.build.info` 的 wowf 版本。
- 客戶端沒有怪物掉落表、任務內容、訓練師學費與大部分 NPC 位置；伺服器也可能修正客戶端資料。發布前依遊戲內實際結果抽查，並在網站標示資料的 build。

## Wowhead 永恆繁中

可信度：本次實測（2026-11-13）。

- 頁面：`https://www.wowhead.com/forever/tw/item={id}`，其他類型照 Wowhead 慣例，例如 `spell={id}`。
- 嵌入提示框：載入 `https://wow.zamimg.com/js/tooltips.js`，頁面上指向 `wowhead.com/forever/tw/...` 的連結會自動依網址判斷資料版本與語系，滑鼠移上就顯示繁中提示框。設定與條款以 Wowhead 的 tooltips 說明頁為準。
- 內部識別：永恆的 `dataEnv` 為 16（`classicplus`），繁中 locale 為 10。這屬於提示框腳本的內部參數，網站應使用官方腳本，不要直接呼叫。
- 網站頁面會被 Cloudflare 擋伺服器端 `curl`（403），只在瀏覽器中使用。
- 建置時查名稱與圖示（本次實測，2026-11-18）：`https://nether.wowhead.com/forever/tw/tooltip/item/{id}` 可用 `curl` 取得 JSON，含 `name`、`quality`、`icon` 與提示框 HTML；圖示網址為 `https://wow.zamimg.com/images/wow/icons/medium/{icon}.jpg`。永恆資料仍是「[英文]」的經典版物品，改查 `classic/tw` 會有繁中名稱（例：647 命運）；永恆新增物品查不到時回 404。只在建置腳本低頻查詢並快取（`scripts/build-market-data.py`），網站前端仍用官方 tooltips 腳本或連結。

## 官方新聞與論壇

可信度：本次實測（2026-11-13）。

- 新聞：[news.blizzard.com/zh-tw](https://news.blizzard.com/zh-tw/)，文章網址為 `/zh-tw/article/{id}/{slug}`。試過的 RSS 與列表 JSON 路徑都回 404，網站以連結為主；要自動整理時解析列表頁 HTML，並保留原文連結。永恆專頁見 SKILL.md 列出的官網。
- 台灣官方論壇 [tw.forums.blizzard.com/zh/wow](https://tw.forums.blizzard.com/zh/wow/) 是 Discourse，網址加 `.json` 或 `.rss` 即可讀：
  - 最新主題：`/zh/wow/latest.json`
  - 藍帖：`/zh/wow/groups/blizzard-tracker/posts.rss`
  - 分類：15 BUG回報（永恆問題多在這裡）、12 伺服器狀況、55 公會專區；完整清單看 `/zh/wow/site.json` 的 `categories`
- API 異動消息：[美服論壇 API Discussion](https://us.forums.blizzard.com/en/blizzard/c/api-discussion)。

## 遊戲內插件收集

API 與客戶端都缺的資料（掉落、任務、NPC 位置、人口、行情掃描）只能靠玩家安裝的插件記錄：

- 插件把資料寫進 SavedVariables，遊戲登出或重載時才落盤，再由外部程式解析上傳。
- 插件訊息不能跨陣營，收資料角色要聯盟、部落各一隻。
- 拍賣場插件看得到掛單，看不到成交價。
- 只公開彙總數字；不公開角色名，也不提供個別角色的位置或上線時間查詢。

這需要自製插件、上傳程式與後端，工程量遠大於靜態網站。專業議事廳若需要這類資料，優先連結既有資料站。

## 參考站：阿莫比 wowamobi.com

可信度：本次實測（2026-11-13），依頁面說明與瀏覽器網路請求整理。

[阿莫比](https://wowamobi.com/) 是台灣玩家的永恆資料站，提供天賦與傳承樹模擬器、職業、種族、任務、專業配方、遭攔截的物資、坐騎、物品、副本、世界地圖、拍賣場物價與物價指數、PvP 擊殺榜、人口普查、新聞，以及 Discord 頻道同步與自製插件「阿莫比小幫手」。

| 內容 | 資料方法 |
| --- | --- |
| 物品 19,078 件、配方 2,178 筆（永恆新增 930）、副本、地圖 | 解析客戶端 `1.60.1.70532`（配方用封測 `70450`），另加人工「伺服器修正」 |
| 首領掉落 | AmobiLoot 插件回報，至少兩人回報才列；尚無資料時列經典版參考並標示 |
| 任務 3,260 個 | 小幫手在玩家看任務、交任務時記錄 |
| NPC 位置 | 小幫手記錄優先；其餘取自 [vmangos](https://github.com/vmangos/core)（GPL-2.0），標「經典版參考」 |
| 拍賣行情 | 插件在遊戲內掃描掛單，三陣營拍賣場合併計算；物價指數用 41 件材料與藥水的幾何平均 |
| 人口普查 | 小幫手記錄身邊同陣營玩家，以插件訊息傳給站長收資料角色，去重後只上傳彙總；主數字用 7 天內看到的角色 |
| 新聞 | 每 15 分鐘整理台灣新聞與官方論壇藍帖，附中文重點與原文連結 |

- 站內 `/api/census`、`/api/market`、`/api/news` 等是網站自用端點，沒有公開文件或使用條款，所以專業議事廳只連結它們的頁面，不當作網站的資料來源。回答玩家的行情或配方利潤問題時可低頻讀取，格式與流程見 [market-recipe-value.md](market-recipe-value.md)。
- 阿莫比的強項是全站資料庫與群眾回報。專業議事廳的定位是跨角色專業分工與傳承規劃，增強時聚焦在與方案直接相關的資料。

## 專業議事廳增強方向

依成本由低到高。網站目前是純靜態 GitHub Pages，網站維護方式見 [profession-planner-site.md](profession-planner-site.md)。

1. **物品提示框**：在材料、成品或配方名稱加上 Wowhead 永恆繁中連結並載入 tooltips 腳本。需要在 `data.mjs` 補物品或法術 ID，不需要後端。
2. **版本與查證標示**：在頁尾顯示目前客戶端 build 與資料查證日期，可手動更新，或由排程讀 TACT。
3. **材料行情**：每小時排程 2026-11-19 起也收 `/commodities`（清單 key 是 `auctions`，見[拍賣場](battlenet-api.md#拍賣場)），部落材料的最低單價與上架量已在 `auctions.json`。專業分配頁可再挑方案用到的材料（草藥、礦、布、皮、附魔材料）顯示中位單價與上架量。
4. **配方與里程碑**：從官方專業 API（skill tier → recipe）取配方、材料與成品，點數仍從客戶端資料表補，對應 150／225／300 附近的傳承里程碑。
5. **公會工匠名冊**：以《黎明之劍》roster 加上各角色的 `professions` 列出誰會做什麼。成員要先同意才公開，只顯示同意者。
6. **公告連結**：以台灣論壇藍帖 RSS 或 BUG 回報分類，列出與專業相關的最新官方訊息。

### 靜態網站整合模式

需要 API 憑證的項目（3、5）採建置時預抓：

- GitHub Actions 排程取得 token，憑證放在 repo Secrets，產出彙總 JSON 給網站讀取。
- 每份 JSON 記錄 `fetchedAt`、build 或 namespace、來源 URL；請求失敗時保留上一份資料，並在網站顯示資料時間。
- 拍賣原始回應每間最大約 9 MB、共 15 間，只在 CI 記憶體內處理，repo 只存彙總結果。物品名稱以客戶端繁中資料為主。
- Pages 仍從 `main` 根目錄發布。拍賣資料採第三種做法：排程把彙總結果 commit 到獨立的 `auction-data` 分支，網站從 `raw.githubusercontent.com` 讀（回應帶 `Access-Control-Allow-Origin: *`、快取 5 分鐘、支援 gzip），`main` 的歷史與 Pages 建置都不受影響。實作是 `scripts/collect-auctions.py` 與 `.github/workflows/auction-collect.yml`，API 共用 `scripts/blizzard_api.py`；README 有發布說明。
- 永恆的拍賣資料每小時更新（見[拍賣場](battlenet-api.md#拍賣場)），以回應的 `Last-Modified` 判斷有沒有新資料。

## 授權與隱私

- 物品圖示、名稱與說明文字的版權屬於 Blizzard Entertainment，網站註明來源。
- 官方 API 依 Battle.net 開發者入口的使用條款；不要把 client secret 寫進前端或 repo。
- vmangos 資料為 GPL-2.0，引用時注意授權義務，並標示為經典版參考。
- Wowhead 只透過官方提示框腳本與連結使用。
- 角色與公會資料雖可公開查詢，網站只公開彙總或已同意的成員；不提供個別角色的上線或位置追蹤。私人帳號、角色與 BattleTag 依 SKILL.md 的公開 repo 規則處理。

## 重新查證

寫進網站前依需要重跑：

1. 客戶端版本：`curl -s http://us.patch.battle.net:1119/wowf/versions`，以及 `https://wago.tools/api/builds` 的 `wowf`。
2. 官方 API：照 [battlenet-api.md 的重新查證](battlenet-api.md#重新查證)執行 `api-probe.yml`，確認官方文件、static 版本與各端點狀態有沒有變。
3. 更新本檔的查證日期、版本號與可信度標記。
