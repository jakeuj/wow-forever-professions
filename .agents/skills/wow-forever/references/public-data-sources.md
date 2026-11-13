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
| 物品名稱、品質、圖示（繁中） | [客戶端資料表](#客戶端版本與資料表)、[Wowhead](#wowhead-永恆繁中) | 官方 API 約四成物品回 404 |
| 專業配方、技能點、材料 | 客戶端資料表 | 學費與訓練師位置只在伺服器端 |
| 拍賣行情 | [官方拍賣 API](#拍賣場) | 插件掃描只看得到掛單價 |
| 角色等級、裝備、專業 | [官方角色 API](#角色與公會) | Lv10 以上且登出後才出現 |
| 公會成員 | 官方公會 roster | 中文公會名的 slug 未驗證 |
| 掉落、任務、NPC 位置 | 無官方來源；[插件群眾回報](#遊戲內插件收集) | 經典版資料只能標示為參考 |
| 伺服器人口 | 無官方來源；插件抽樣 | 只代表被看到的角色，適合看比例 |
| 官方公告 | [台灣新聞頁](#官方新聞與論壇) | 未找到 RSS／JSON |
| 藍帖、BUG 回報 | 台灣官方論壇 JSON／RSS | Discourse 標準端點 |

## Battle.net API（永恆）

可信度：社群實測，最後查核 2026-11-09。Blizzard 開發者文件只列 Retail 與 Classic（`classic`、`classic1x`），尚無永恆章節；`classic1x` 屬於 Classic Era，與永恆無關。主要來源：

- [WoW: Forever API: what works so far, plus a TS client](https://us.forums.blizzard.com/en/blizzard/t/wow-forever-api-what-works-so-far-plus-a-ts-client/60334)（2026-11-05～06）
- [World of Warcraft: Forever API Namespace?](https://us.forums.blizzard.com/en/blizzard/t/world-of-warcraft-forever-api-namespace/59774)（開服前探測，部分已過時）
- [blizzard.pinta.land/forever](https://blizzard.pinta.land/forever/)：MIT 授權的 TypeScript 函式庫 [`@pinta365/blizzard_api`](https://github.com/Pinta365/blizzard_api) 0.8.0 起支援永恆，文件標示每週以 CI 對線上 API 做煙霧測試

### 連線與驗證

- Token（官方文件）：`POST https://oauth.battle.net/token`，`grant_type=client_credentials`，以 client ID／secret 做 Basic 驗證；中國區另需中國註冊的 client。到 [Battle.net 開發者入口](https://community.developer.battle.net/) 建立 client，並遵守其 API 使用條款。
- 主機：台灣區為 `https://tw.api.blizzard.com`，加 `locale=zh_TW`。亞服角色屬於 TW 區是依 ruleset 與玩家分布推斷，首次串接時以已知角色確認。
- Namespace 可放在 `?namespace=` 或 `Battlenet-Namespace` 標頭。
- 速率（官方文件，通用）：每個 client 每小時 36,000 次、每秒 100 次。
- Client secret 只能放在伺服器端或 CI Secrets。帳號角色清單 `/profile/user/wow` 需要使用者授權碼流程（`wow.profile` scope 與回呼網址），純靜態網站做不到。

```sh
TOKEN=$(curl -s -u "$BLIZZARD_CLIENT_ID:$BLIZZARD_CLIENT_SECRET" \
  -d grant_type=client_credentials https://oauth.battle.net/token |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://tw.api.blizzard.com/data/wow/ruleset/index?namespace=dynamic-forever-tw&locale=zh_TW"
```

### Namespace

| Namespace | 用途 |
| --- | --- |
| `static-forever-{region}` | 遊戲靜態資料（職業、種族、物品等），提供目前版本 |
| `static-{版本}-forever-{region}` | 鎖定版本，例如 `static-1.60.1_70399-forever-tw` |
| `dynamic-forever-{region}` | ruleset、拍賣場 |
| `profile-forever-{region}` | 角色、公會、帳號資料 |

`us`、`eu`、`kr`、`tw` 可用。目前版本寫在任一 static 回應 `self` 連結的 `namespace` 參數。2026-11-09 的 static 版本是 `1.60.1_70399`，比當時客戶端舊；版本更新後舊版是否保留未知。

### Ruleset 取代伺服器

永恆沒有 realm：`/data/wow/realm/index` 回 404，realm search 沒有結果。改用 `dynamic` 的 `/data/wow/ruleset/index` 與 `/data/wow/ruleset/{id}`，回傳 `id`、`name`、`status`（`UP`／`DOWN`）與拍賣場連結。TW 與 KR 只有 `1` PvP、`2` Normal；US 與 EU 另有 `3` Roleplay、`15` Roleplay PvP。

### 角色與公會

- 角色名稱是「名字＋姓氏」，全區唯一，以小寫 `{name}-{surname}` 查詢，不帶 realm，例如 `/profile/wow/character/{name}-{surname}?namespace=profile-forever-tw`。
- 角色要達 Lv10 並在該等級登出後才查得到；之前所有角色端點都回 404。資料是登出當下的快照，通常數秒內更新。
- 角色資料以 `surname`、`ruleset` 取代 `realm`，沒有 `active_spec`、`active_title`。
- 可用子端點：achievements、appearance、collections、encounters、equipment、character-media、mythic-keystone-profile、professions、pvp-summary、quests、reputations、specializations、statistics、titles。`professions` 的永恆回傳內容（技能點、已學配方）尚未有公開樣本，串接前先實測。
- `character-media` 的圖片在 `render.worldofwarcraft.com/forever-{region}/`，可能比角色資料晚數小時到一天以上出現。
- 帳號角色清單（使用者 token）另有快取，可能落後角色資料數分鐘到數小時。
- 公會同樣不帶 realm：`/data/wow/guild/{slug}`，以及 `/roster`、`/activity`、`/achievements`。slug 為小寫公會名、空白換成連字號；中文公會名的 slug 尚無實例。roster 包含 Lv10 以下成員，列出 `name`、`surname`、`slug`、`level`、職業、種族與陣營；目前沒有 crest 與成就總數，activity 為空。

### 拍賣場

2026-11-06 起提供資料，路徑在 `dynamic-forever-{region}`：

| 路徑 | 內容 |
| --- | --- |
| `/data/wow/ruleset/{id}/auctions/` | 拍賣場索引；結尾斜線必要，沒有斜線回 404 |
| `/data/wow/ruleset/{id}/auctions/{houseId}` | 該拍賣場的 `auctions` |
| `/data/wow/ruleset/{id}/auctions/{houseId}/commodities` | 該拍賣場的商品類 `commodities` |

- 每個 ruleset 都列出同一組 15 間（ID 110–121、123–125）：聯盟、部落、中立黑水各 5 間。ruleset ID 必須有效但不會篩選資料，跨 ruleset 加總會重複計算。
- 欄位與 Retail 相同：auction 有 `item.id`、`buyout`、部分有 `bid`、`quantity`、`time_left`；commodity 用 `unit_price`。沒有賣家資訊，也沒有成交價。
- 部分拍賣場沒有 `auctions` 欄位（112、115、118），視為選填。最大的單間約 5～7 萬筆、9 MB。
- 舊的 `/data/wow/auctions/commodities` 回 404。
- 物品資料缺漏：某一間拍賣場的 1,515 種物品中，652 種（43%）在 `static-forever` 的 `/data/wow/item/{id}` 回 404。名稱改用客戶端資料表；Retail 物品 API 可補名稱與品質，但屬性可能與永恆不同。

### 尚不可用

realm 與 connected realm、WoW 代幣、PvP 與傳奇鑰石賽季、`/hunter-pets` 回 404。傳家寶、資料片、副本與首領（journal instances／encounters）、寵物技能的 static 索引是空的，所以副本與掉落資料要另找來源。

## 客戶端版本與資料表

可信度：本次實測（2026-11-13）。

- 版本：`http://{region}.patch.battle.net:1119/wowf/versions` 以 `|` 分隔，`VersionsName` 欄是版本號。產品代碼 `wowf` 與安裝根目錄 `.build.info` 的 Product 相同。當日各區皆為 `1.60.1.70938`。
- [wago.tools](https://wago.tools/)：`https://wago.tools/api/builds` 的 `wowf` 陣列列出歷次版本與建立時間（當日 `70938`、11/10 `70888`、11/07 `70862`）。
- 資料表 CSV：`https://wago.tools/db2/{表名}/csv?build={版本}&locale=zhTW`。例如 `ItemSparse` 的 `Display_lang` 是繁中物品名，物品 19019 為「雷霆之怒，逐風者的祝福之劍」。
- 專業相關資料表：`SkillLine`（專業）、`SkillLineAbility`（配方所屬專業，以及 `MinSkillLineRank`、`TrivialSkillLineRankLow`／`High` 技能點）、`ItemSparse`／`Item`（成品與材料）。材料與成品的對應在法術相關資料表，欄位依當版 schema 確認。
- 客戶端沒有怪物掉落表、任務內容、訓練師學費與大部分 NPC 位置；伺服器也可能修正客戶端資料。發布前依遊戲內實際結果抽查，並在網站標示資料的 build。

## Wowhead 永恆繁中

可信度：本次實測（2026-11-13）。

- 頁面：`https://www.wowhead.com/forever/tw/item={id}`，其他類型照 Wowhead 慣例，例如 `spell={id}`。
- 嵌入提示框：載入 `https://wow.zamimg.com/js/tooltips.js`，頁面上指向 `wowhead.com/forever/tw/...` 的連結會自動依網址判斷資料版本與語系，滑鼠移上就顯示繁中提示框。設定與條款以 Wowhead 的 tooltips 說明頁為準。
- 內部識別：永恆的 `dataEnv` 為 16（`classicplus`），繁中 locale 為 10。這屬於提示框腳本的內部參數，網站應使用官方腳本，不要直接呼叫。
- 伺服器端 `curl` 會被 Cloudflare 擋（403），只在瀏覽器中使用。

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

- 站內 `/api/census`、`/api/market`、`/api/news` 等是網站自用端點，沒有公開文件或使用條款，所以只連結它們的頁面，不當作資料來源。
- 阿莫比的強項是全站資料庫與群眾回報。專業議事廳的定位是跨角色專業分工與傳承規劃，增強時聚焦在與方案直接相關的資料。

## 專業議事廳增強方向

依成本由低到高。網站目前是純靜態 GitHub Pages，網站維護方式見 [profession-planner-site.md](profession-planner-site.md)。

1. **物品提示框**：在材料、成品或配方名稱加上 Wowhead 永恆繁中連結並載入 tooltips 腳本。需要在 `data.mjs` 補物品或法術 ID，不需要後端。
2. **版本與查證標示**：在頁尾顯示目前客戶端 build 與資料查證日期，可手動更新，或由排程讀 TACT。
3. **材料行情**：用排程抓官方拍賣 API，只輸出方案用到的材料（草藥、礦、布、皮、附魔材料）的中位單價、最低價與上架量。
4. **配方與里程碑**：從客戶端資料表匯出各製造專業在 150／225／300 附近的配方，對應傳承里程碑。
5. **公會工匠名冊**：以《黎明之劍》roster 加上各角色的 `professions` 列出誰會做什麼。成員要先同意才公開，只顯示同意者。
6. **公告連結**：以台灣論壇藍帖 RSS 或 BUG 回報分類，列出與專業相關的最新官方訊息。

### 靜態網站整合模式

需要 API 憑證的項目（3、5）採建置時預抓：

- GitHub Actions 排程取得 token，憑證放在 repo Secrets，產出彙總 JSON 給網站讀取。
- 每份 JSON 記錄 `fetchedAt`、build 或 namespace、來源 URL；請求失敗時保留上一份資料，並在網站顯示資料時間。
- 拍賣原始回應每間最大約 9 MB、共 15 間，只在 CI 記憶體內處理，repo 只存彙總結果。物品名稱以客戶端繁中資料為主。
- 目前 Pages 從 `main` 根目錄發布。要產生資料檔時，需在「bot 定期 commit 到 `main`」與「改由 Actions 建置部署」之間擇一，並同步更新 README 的發布說明。
- 拍賣資料更新頻率尚未實測。排程間隔先設為數小時，並以回應的 `Last-Modified` 判斷有沒有新資料（這是 Retail 的行為，永恆待確認）。

## 授權與隱私

- 物品圖示、名稱與說明文字的版權屬於 Blizzard Entertainment，網站註明來源。
- 官方 API 依 Battle.net 開發者入口的使用條款；不要把 client secret 寫進前端或 repo。
- vmangos 資料為 GPL-2.0，引用時注意授權義務，並標示為經典版參考。
- Wowhead 只透過官方提示框腳本與連結使用。
- 角色與公會資料雖可公開查詢，網站只公開彙總或已同意的成員；不提供個別角色的上線或位置追蹤。私人帳號、角色與 BattleTag 依 SKILL.md 的公開 repo 規則處理。

## 重新查證

寫進網站前依需要重跑：

1. 客戶端版本：`curl -s http://us.patch.battle.net:1119/wowf/versions`，以及 `https://wago.tools/api/builds` 的 `wowf`。
2. 有 API 憑證時，依序確認 TW 的 ruleset 索引、static 回應的 `self` namespace 版本、拍賣場索引，以及一個已知角色的 profile 與 `professions`。
3. 重讀 [blizzard.pinta.land/forever](https://blizzard.pinta.land/forever/) 各頁的 *Last checked* 日期與 [API Discussion](https://us.forums.blizzard.com/en/blizzard/c/api-discussion) 的新討論，確認有沒有官方文件或行為變更。
4. 更新本檔的查證日期、版本號與可信度標記。
