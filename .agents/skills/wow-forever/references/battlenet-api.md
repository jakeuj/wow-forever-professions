# Battle.net API（永恆）

最近一次台服端點實測為 2026-11-20（台灣時間）。可信度標記沿用 [public-data-sources.md](public-data-sources.md)。

- **官方文件**：Battle.net 開發者入口寫明，但寫的是 Retail 或 Classic。
- **社群實測**：開發者論壇與第三方函式庫的探測，可能無預警變動。
- **本次實測**：查證當日以 `scripts/forever_api_coverage.py` 或 `scripts/forever_api.py` 直接請求的結果。

寫進網站或回答「目前能不能查」之前，依[重新查證](#重新查證)重跑。

## 實測結論

2026-11-20 台灣時間 01:06，使用 Windows 本機的加密憑證完成 TW 區探測。靜態 namespace 為 `static-1.60.1_70399-forever-tw`。探測範圍合併官方 Retail、Classic 端點清單與永恆專屬的 ruleset 路徑。自動探測共送出 286 次資料 API 請求，136 個端點樣板回 HTTP 200。另送出 7 次固定路徑補測，確認法術明細和法術媒體各有可用的 ID。

合併補測後，218 個端點樣板中有 **138 個至少一筆回 HTTP 200**，其中 28 個索引或搜尋沒有回傳非空清單。另外有 70 個在所測參數下回 404、9 個需要使用者 OAuth 授權、1 個缺少測試 ID。

- **專業與配方**。`profession/index` 列出 13 個繁中專業。`profession/{id}` 的 `skill_tiers` 指向技能階段，含 `minimum_skill_level`、`maximum_skill_level` 和 `categories[].recipes[]`。裁縫樣本中最大的一組有 65 筆配方。`recipe/{id}` 提供 `crafted_item`、`crafted_quantity` 和 `reagents[]`，材料項目有 `reagent` 和 `quantity`。補測的「玉蛇刀」（`1986`）有 5 種材料，產量為 1。配方沒有變黃、變綠或變灰的門檻，練等路線仍需客戶端 `SkillLineAbility` 或 wowf.io。
- **物品資料與官方圖示**。`item/{id}` 有 `quality`、`item_class`、`required_level`、`purchase_price`、`sell_price`、`is_stackable`。`media/item/{id}` 的 `assets[].value` 提供 `https://render.worldofwarcraft.com/forever-tw/icons/56/{file_data_id}.jpg` 這類網址。11 月 18 日的拍賣樣本約四成物品明細回 404，名稱與圖示需保留客戶端資料表或 Wowhead 備援。
- **搜尋可用**：`search/item`、`search/spell`、`search/creature`、`search/mount`、`search/media`、`search/item-appearance` 回結果。搜尋結果的名稱是所有語系的物件，即使帶了 `locale`；用 `name.zh_TW=` 篩選。
- **拍賣場**。台服兩種 ruleset、拍賣場索引、部落單件掛單與可堆疊商品都查得到。兩種掛單端點的清單欄位都是 `auctions`，收集腳本自 11 月 19 日起讀取商品清單。 [拍賣場欄位與樣本](#拍賣場)
- **任務與其他靜態資料**。任務子索引、聲望、坐騎、寵物、玩具、稱號、成就和部分天賦可查繁中資料。`quest/index` 只回子索引連結，`quest/{id}` 有 `requirements` 和 `rewards`。法術明細及圖示依 ID 而異。
- **角色專業**。`/profile/wow/character/{name}-{surname}/professions` 提供 `primaries[]`、`secondaries[]` 和 `tiers[].known_recipes[]`，本次樣本最大的一組有 37 筆已學配方。11 月 19 日另有樣本驗證 `tier`（如鍛造 ID `2938`）、`skill_points` 和 `max_skill_points`。該次角色回應帶 `locale=zh_TW` 時仍是英文名稱，顯示繁中時可用 ID 查靜態專業和配方。
- **公會**。`/data/wow/guild/黎明之劍` 和 `/roster` 都回 200，名單有 169 人。`/achievements` 和 `/activity` 在本次樣本只回公會標頭。
- **缺少內容的端點**。副本手冊的索引無資料，所測副本與首領明細回 404。realm、connected realm、WoW 代幣、PvP 賽季、傳奇鑰石賽季、名人堂、住宅、盟約、艾澤萊精華、傳家寶、寵物技能及 PvP／技術天賦回 404 或只有空清單。 [端點實測表](#端點實測表)

## 官方指南重點

可信度：官方文件，2026-11-18 讀取 [Using APIs](https://community.developer.battle.net/documentation/guides) 與 WoW、WoW Classic 兩組指南。

官方入口**沒有永恆章節**：WoW 與 WoW Classic 的 20 頁指南與 API 參考都沒有出現「forever」，Classic 的 namespace 表只列 Era（`classic1x`）、Mists 進度服（`classic`）、周年服（`classicann`）。以下規則是通用規則或 Retail／Classic 的寫法，永恆差異見[下一節](#永恆與官方文件的差異)。

### 帳號與 client

- 開發者帳號要綁 Battle.net 驗證器（兩步驟驗證），並同意 Blizzard Developer API 使用條款。
- 在 [API Access](https://community.developer.battle.net/access/clients) 建立 client，每人最多 50 個。client 名稱全站唯一，網站使用者可能看得到。
- 換 secret 時可設定舊 secret 的到期時間，期間新舊都能用，方便先更新 repo Secrets 再讓舊的失效。
- Client secret 只放伺服器端、CI Secrets 或本機加密憑證儲存。

### OAuth 與 token

- Token：`POST https://oauth.battle.net/token`，`grant_type=client_credentials`，以 client ID／secret 做 Basic 驗證。US、EU、APAC（取代舊的 kr／tw）共用 `oauth.battle.net`；中國用 `oauth.battlenet.com.cn`，且要中國註冊的 client。
- Token 有效 24 小時；請求失敗時重新取得，不要假設一定還有效。`/check_token?token=…` 可確認 token 是否屬於自己的 client。
- 大部分端點用 client credentials token。下列要使用者授權碼流程（authorization code，scope `wow.profile`，HTTPS redirect URI）：`/profile/user/wow`、`protected-character`、帳號 collections，以及 `/userinfo`（scope `openid`）。純靜態網站做不到，需要伺服器端接回呼。
- 速率（官方文件，通用）：每個 client 每小時 36,000 次、每秒 100 次。

```sh
TOKEN=$(curl -s -u "$BLIZZARD_CLIENT_ID:$BLIZZARD_CLIENT_SECRET" \
  -d grant_type=client_credentials https://oauth.battle.net/token |
  python3 -c 'import json,sys; print(json.load(sys.stdin)["access_token"])')
curl -s -H "Authorization: Bearer $TOKEN" \
  "https://tw.api.blizzard.com/data/wow/ruleset/index?namespace=dynamic-forever-tw&locale=zh_TW"
```

### 區域與語系

- 帳號分兩個分區：中國與其他地區，兩邊資料互不相通。
- API 主機：`https://{us|eu|kr|tw}.api.blizzard.com`，中國為 `https://gateway.battlenet.com.cn`。資料限該區，同一人在不同區是不同角色。
- 台灣主機只提供 `zh_TW`；韓國只有 `ko_KR`。
- 不帶 `locale` 時，可翻譯欄位回傳所有語系的物件（`{"en_US": …, "zh_TW": …}`）；帶 `locale=zh_TW` 才會攤平成字串。讀回應時兩種都要處理（`scripts/probe-auction-api.py` 的 `text()`）。

### Namespace

- 三類：`static`（隨版本變動的遊戲資料，如物品、成就）、`dynamic`（隨遊戲事件變動，如代幣、伺服器狀態）、`profile`（角色與帳號；角色在登出時更新，公會定期更新）。
- 每個請求都要帶 namespace，可用 `?namespace=` 或 `Battlenet-Namespace` 標頭。namespace 裡的版本號不是語意化版本，不能拿來比大小。

### 搜尋

- `/data/wow/search/{type}?namespace=…&{欄位}={值}`，每次最多 1,000 筆。巢狀欄位用點號，例如 `name.zh_TW`。
- 特殊參數：`_page`（預設 1）、`_pageSize`（1–1,000，預設 100）、`orderby=欄位:asc|desc`（可多欄以逗號分隔）、`_tag`（只用於 media）。
- 運算：多個參數是 AND；`a||b` 是 OR；`!=` 是 NOT；`[min,max]` 含端點、`(min,max)` 不含，可只寫一邊。

### 媒體與角色圖

- 物品、法術等文件帶 `media.key.href`，指向 `/data/wow/media/{type}/{id}`；媒體文件的 `assets[]` 有 `key`（如 `icon`）與圖片網址。官方建議把圖片存到自己的空間，不要直接熱連結。
- 角色圖在登出時產生，清單在 `character-media`。頭像不存在時可在網址加 `?alt=/shadow/avatar/{種族ID}-{性別ID}.jpg`（男 0、女 1）取得預設剪影。

### Known Issues

官方說明：回應中連到的子文件可能尚未發布或屬於私有 scope，會回 404、401 或其他狀態。這也解釋永恆的情況：拍賣與角色回應裡的物品連結，不保證 `/data/wow/item/{id}` 查得到。

## 永恆與官方文件的差異

可信度：社群實測與本次實測。主要來源：

- [WoW: Forever API: what works so far, plus a TS client](https://us.forums.blizzard.com/en/blizzard/t/wow-forever-api-what-works-so-far-plus-a-ts-client/60334)（2026-11-05～06）
- [World of Warcraft: Forever API Namespace?](https://us.forums.blizzard.com/en/blizzard/t/world-of-warcraft-forever-api-namespace/59774)（開服前探測，部分已過時）
- [blizzard.pinta.land/forever](https://blizzard.pinta.land/forever/)：MIT 授權的 TypeScript 函式庫 [`@pinta365/blizzard_api`](https://github.com/Pinta365/blizzard_api) 0.8.0 起支援永恆，每週以 CI 對線上 API 做煙霧測試；最後查核 2026-11-16。

### Namespace

| Namespace | 用途 |
| --- | --- |
| `static-forever-{region}` | 遊戲靜態資料（職業、種族、物品等），提供目前版本 |
| `static-{版本}-forever-{region}` | 鎖定版本，例如 `static-1.60.1_70399-forever-tw` |
| `dynamic-forever-{region}` | ruleset、拍賣場 |
| `profile-forever-{region}` | 角色、公會、帳號資料 |

`us`、`eu`、`kr`、`tw` 可用，`cn` 要中國的 client。靜態資料版本寫在回應 `self` 連結的 `namespace` 參數。2026-11-20 台服探測仍回 `1.60.1_70399`。

### Ruleset 取代伺服器

永恆沒有 realm：`/data/wow/realm/index` 回 404，realm search 沒有結果。改用 `dynamic` 的 `/data/wow/ruleset/index` 與 `/data/wow/ruleset/{id}`，回傳 `id`、`name`、`status`（`UP`／`DOWN`）與拍賣場連結。TW 與 KR 只有 `1` PvP、`2` Normal；US 與 EU 另有 `3` Roleplay、`15` Roleplay PvP。

### 角色與公會

- 角色名稱是「名字＋姓氏」，全區唯一，以小寫 `{name}-{surname}` 查詢，不帶 realm，例如 `/profile/wow/character/{name}-{surname}?namespace=profile-forever-tw`。
- 角色要達 Lv10 並在該等級登出後才查得到；之前所有角色端點都回 404。資料是登出當下的快照，通常數秒內更新。
- 角色資料以 `surname`、`ruleset` 取代 `realm`，沒有 `active_spec`、`active_title`。
- 2026-11-20 從公開公會名單取樣一位 Lv60 角色，31 個角色端點中 25 個回 200、6 個回 404。裝備、專業、任務、聲望和成就都有內容，`character-media` 回傳 4 張圖。此角色的團本與地城紀錄無資料，寵物和玩具收藏也沒有清單。房屋、住宅收藏、獵人寵物、傳奇鑰石賽季、PvP 組別與靈魂羈絆回 404。 [角色端點實測表](#端點實測表)
- 角色主文件有 `level`、`experience`、`achievement_points`、`guild`（含 `slug`）、`last_login_timestamp`、`average_item_level`、`equipped_item_level`、種族、職業、性別與陣營。
- `character-media` 的圖片在 `render.worldofwarcraft.com/forever-{region}/`，可能比角色資料晚數小時到一天以上出現。
- 帳號角色清單（使用者 token）另有快取，可能落後角色資料數分鐘到數小時。
- 公會同樣不帶 realm：`/data/wow/guild/{slug}`（`profile` namespace），以及 `/roster`、`/activity`、`/achievements`。slug 為小寫公會名、空白換成連字號；中文公會名直接用原字（網址編碼），本次實測「黎明之劍」可查。公會文件有 `member_count`、`achievement_points`、`created_timestamp`、`faction`、`ruleset`、`name_search`。roster 包含 Lv10 以下成員，列出 `name`、`surname`、`slug`、`level`、職業、種族、陣營與 `rank`。11 月中起部分公會有 crest；`achievements` 與 `activity` 只有公會標頭。

### 拍賣場

2026-11-06 起提供資料，路徑在 `dynamic-forever-{region}`：

| 路徑 | 內容 |
| --- | --- |
| `/data/wow/ruleset/{id}/auctions/` | 拍賣場索引；結尾斜線必要，沒有斜線回 404 |
| `/data/wow/ruleset/{id}/auctions/{houseId}` | 該拍賣場的 `auctions` |
| `/data/wow/ruleset/{id}/auctions/{houseId}/commodities` | 該拍賣場的商品類（能堆疊的物品），清單的 key 也是 `auctions` |

- 每個 ruleset 都列出同一組 15 間（ID 110–121、123–125）：聯盟、部落、中立黑水各 5 間。ruleset ID 必須有效但不會篩選資料，跨 ruleset 加總會重複計算。
- 欄位與 Retail 相同：auction 有 `item.id`、`buyout`、部分有 `bid`、`quantity`、`time_left`；commodity 用 `unit_price`。沒有賣家資訊，也沒有成交價。
- **`/commodities` 的清單欄位是 `auctions`**（Retail 為 `commodities`）。商品掛單有 `id`、`item.id`、`quantity`、`unit_price`、`time_left`。
- **2026-11-20 台服 Windows 補測**。`/data/wow/ruleset/1/auctions/113` 回 200，有 12,194 筆單件掛單。`/data/wow/ruleset/1/auctions/113/commodities` 也回 200，有 17,349 筆可堆疊商品掛單。兩個回應的 `Last-Modified` 都是當天台灣時間 00:26。
- 部分拍賣場沒有 `auctions` 欄位（112、115、118），視為選填。最大的單間約 5～7 萬筆、9 MB。
- 舊的 `/data/wow/auctions/commodities` 與 `connected-realm` 拍賣路徑回 404。
- 物品資料缺漏：某一間拍賣場的 1,515 種物品中，652 種（43%）在 `static-forever` 的 `/data/wow/item/{id}` 回 404。名稱改用客戶端資料表；Retail 物品 API 可補名稱與品質，但屬性可能與永恆不同。

TW 區實測（2026-11-18，`scripts/probe-auction-api.py`，在 GitHub Actions 手動執行 `auction-probe.yml`）：

- ruleset 1、2 的索引是同一組 15 間，名稱只有「聯盟拍賣場」「部落拍賣場」「黑水灣拍賣場」。單間回應的 `ruleset` 只是請求路徑裡的 ruleset 連結，每間都一樣，分不出拍賣場屬於哪個 ruleset。
- 有掛單的是 110、111（聯盟）、113、114（部落）、116、117（黑水灣），其餘 9 間是空的。
- **亞服 PvP 部落是 113**：站主在部落拍賣場用拍賣小幫手完整掃描，與 10 分鐘後的 API 資料相比，2,082 件共同物品有 97.6% 的最低一口價完全相同；其他拍賣場只有 6～12%。
- **單間端點只有不能堆疊的物品**：`auctions` 只列裝備、武器、配方、容器、棒、武器之油這類單件物品，每筆 `quantity` 都是 1，`buyout` 就是單價。同一次掃描的 343 件商品類（草藥、礦、皮、肉）只有 8 件、522 件消耗品（藥水、食物、卷軸）只有 153 件、彈藥 0 件出現在這個端點。當時以為 `/commodities` 是空的，其實是腳本讀了不存在的 `commodities` key（見上一點）。
- **能堆疊的物品在 `/commodities`**（2026-11-19 本次實測，修正後的 `probe-auction-api.py`，[run 44447472007](https://github.com/jakeuj/wow-forever-professions/actions/runs/44447472007)）：113 號有 8,050 筆單件掛單＋10,916 筆商品類，合計 2,841 種物品。與 10 小時前的拍賣小幫手完整掃描相比，商品類 342 件中 332 件、消耗品 527 件中 474 件、彈藥 16 件中 14 件出現在 API；各類別 API 最低價除以掃描價的中位數都是 1.00，所以 `unit_price` 是單價。`/commodities` 的 `Last-Modified` 與單間端點同時更新。
- 掛單欄位：`id`、`item`（`id`、`bonus_lists`、`context`、`modifiers`）、`bid`、`buyout`、`quantity`、`time_left`。113 約 8,750 筆、2,075 種物品、1.9 MB；整區 15 間各抓一次共 35 次請求，約 35 秒。
- 每小時更新一次：`Last-Modified` 從 06:06 UTC 變成 07:06 UTC，15 間同時更新。排程抓取放在每小時 :10 之後，並用 `Last-Modified` 判斷有沒有新資料。

## 端點實測表

下表使用 2026-11-20 台服探測及固定 ID 補測結果。路徑省略 `/data/wow/` 前綴，`{guild}` 使用「黎明之劍」。HTTP 200 但資料有限的回應可能只有空清單、子索引連結或標頭。404 反映本次所測參數，明細端點可用性也受 ID 影響。

| API | HTTP 200，有資料 | HTTP 200，資料有限 | HTTP 404 |
| --- | --- | --- | --- |
| Achievement API | `achievement-category/index`、`achievement-category/{achievementCategoryId}`、`achievement/index`、`achievement/{achievementId}`、`media/achievement/{achievementId}` | — | — |
| Auction House API | — | — | `auctions/commodities`、`connected-realm/{connectedRealmId}/auctions`、`connected-realm/{connectedRealmId}/auctions/index`、`connected-realm/{connectedRealmId}/auctions/{auctionHouseId}` |
| Azerite Essence API | — | `azerite-essence/index`、`search/azerite-essence` | `azerite-essence/{azeriteEssenceId}`、`media/azerite-essence/{azeriteEssenceId}` |
| Connected Realm API | — | `search/connected-realm` | `connected-realm/index`、`connected-realm/{connectedRealmId}` |
| Covenant API | — | `covenant/conduit/index`、`covenant/index`、`covenant/soulbind/index` | `covenant/conduit/{conduitId}`、`covenant/soulbind/{soulbindId}`、`covenant/{covenantId}`、`media/covenant/{covenantId}` |
| Creature API | `creature-family/index`、`creature-family/{creatureFamilyId}`、`creature-type/index`、`creature-type/{creatureTypeId}`、`creature/{creatureId}`、`media/creature-display/{creatureDisplayId}`、`media/creature-family/{creatureFamilyId}`、`search/creature` | — | — |
| Guild API | `guild/{guild}`、`guild/{guild}/roster` | `guild/{guild}/achievements`、`guild/{guild}/activity` | — |
| Guild Crest API | `guild-crest/index`、`media/guild-crest/border/{borderId}`、`media/guild-crest/emblem/{emblemId}` | — | — |
| Heirloom API | — | `heirloom/index` | `heirloom/{heirloomId}` |
| Housing Decor API | — | `search/decor`、`search/fixture`、`search/fixture-hook`、`search/room` | `decor/index`、`decor/{decorId}`、`fixture-hook/index`、`fixture-hook/{fixtureHookId}`、`fixture/index`、`room/index`、`room/{roomId}` |
| Item API | `item-class/index`、`item-class/{itemClassId}`、`item-class/{itemClassId}/item-subclass/{itemSubclassId}`、`item-set/index`、`item-set/{itemSetId}`、`item/{itemId}`、`media/item/{itemId}`、`search/item` | — | — |
| Item Appearance API | `item-appearance/set/index`、`item-appearance/set/{appearanceSetId}`、`item-appearance/slot/index`、`item-appearance/slot/{slotType}`、`item-appearance/{appearanceId}`、`search/item-appearance` | — | — |
| Journal API | — | `journal-encounter/index`、`journal-expansion/index`、`journal-instance/index`、`search/journal-encounter` | `journal-encounter/{journalEncounterId}`、`journal-expansion/{journalExpansionId}`、`journal-instance/{journalInstanceId}`、`media/journal-instance/{journalInstanceId}` |
| Media Search API | `search/media` | — | — |
| Modified Crafting API | — | `modified-crafting/category/index`、`modified-crafting/index`、`modified-crafting/reagent-slot-type/index` | `modified-crafting/category/{categoryId}`、`modified-crafting/reagent-slot-type/{slotTypeId}` |
| Mount API | `mount/index`、`mount/{mountId}`、`search/mount` | — | — |
| Mythic Keystone Affix API | — | `keystone-affix/index` | `keystone-affix/{keystoneAffixId}`、`media/keystone-affix/{keystoneAffixId}` |
| Mythic Keystone Dungeon API | — | `mythic-keystone/dungeon/index`、`mythic-keystone/index` | `mythic-keystone/dungeon/{dungeonId}`、`mythic-keystone/period/index`、`mythic-keystone/period/{periodId}`、`mythic-keystone/season/index`、`mythic-keystone/season/{seasonId}` |
| Mythic Keystone Leaderboard API | — | — | `connected-realm/{connectedRealmId}/mythic-leaderboard/index`、`connected-realm/{connectedRealmId}/mythic-leaderboard/{dungeonId}/period/{period}` |
| Mythic Raid Leaderboard API | — | — | `leaderboard/hall-of-fame/{raid}/{faction}` |
| Neighborhood API | — | — | `neighborhood-map/index`、`neighborhood-map/{neighborhoodMapId}`、`neighborhood-map/{neighborhoodMapId}/neighborhood/{neighborhoodId}` |
| Pet API | `media/pet/{petId}`、`pet/index`、`pet/{petId}` | `pet-ability/index` | `media/pet-ability/{petAbilityId}`、`pet-ability/{petAbilityId}` |
| Playable Class API | `media/playable-class/{playableClassId}`、`playable-class/index`、`playable-class/{classId}`、`playable-class/{classId}/pvp-talent-slots` | — | — |
| Playable Race API | `playable-race/index`、`playable-race/{playableRaceId}` | — | — |
| Playable Specialization API | `media/playable-specialization/{specId}`、`playable-specialization/index`、`playable-specialization/{specId}` | — | — |
| Power Type API | `power-type/index`、`power-type/{powerTypeId}` | — | — |
| Profession API | `media/profession/{professionId}`、`media/recipe/{recipeId}`、`profession/index`、`profession/{professionId}`、`profession/{professionId}/skill-tier/{skillTierId}`、`recipe/{recipeId}` | — | — |
| PvP Season API | — | — | `pvp-region/index`、`pvp-region/{pvpRegionId}/pvp-season/index`、`pvp-region/{pvpRegionId}/pvp-season/{pvpSeasonId}`、`pvp-region/{pvpRegionId}/pvp-season/{pvpSeasonId}/pvp-leaderboard/index`、`pvp-region/{pvpRegionId}/pvp-season/{pvpSeasonId}/pvp-leaderboard/{pvpBracket}`、`pvp-region/{pvpRegionId}/pvp-season/{pvpSeasonId}/pvp-reward/index`、`pvp-season/index`、`pvp-season/{pvpSeasonId}`、`pvp-season/{pvpSeasonId}/pvp-leaderboard/index`、`pvp-season/{pvpSeasonId}/pvp-leaderboard/{pvpBracket}`、`pvp-season/{pvpSeasonId}/pvp-reward/index` |
| PvP Tier API | — | `pvp-tier/index` | `media/pvp-tier/{pvpTierId}`、`pvp-tier/{pvpTierId}` |
| Quest API | `quest/area/index`、`quest/area/{questAreaId}`、`quest/category/index`、`quest/category/{questCategoryId}`、`quest/type/index`、`quest/type/{questTypeId}`、`quest/{questId}` | `quest/index` | — |
| Realm API | — | `search/realm` | `realm/index`、`realm/{realmSlug}` |
| Region API | `region/index` | — | `region/{regionId}` |
| Reputations API | `reputation-faction/index`、`reputation-faction/{reputationFactionId}`、`reputation-tiers/index`、`reputation-tiers/{reputationTiersId}` | — | — |
| Ruleset API | `ruleset/index`、`ruleset/{rulesetId}`、`ruleset/{rulesetId}/auctions/`、`ruleset/{rulesetId}/auctions/{auctionHouseId}`、`ruleset/{rulesetId}/auctions/{auctionHouseId}/commodities` | — | — |
| Spell API | `search/spell`、`spell/{spellId}`、`media/spell/{spellId}`（明細和圖示以 `17123` 補測） | — | — |
| Character Profile API | `character`、`status`、`achievements`、`achievements/statistics`、`appearance`、`collections`、`collections/{mounts\|transmogs}`、`equipment`、`character-media`、`professions`、`pvp-summary`、`quests`、`quests/completed`、`reputations`、`specializations`、`statistics` | `collections/{heirlooms\|pets\|toys}`、`encounters`、`encounters/{dungeons\|raids}`、`mythic-keystone-profile`、`titles` | `collections/decor`、`house/house-{houseNumber}`、`hunter-pets`、`mythic-keystone-profile/season/{seasonId}`、`pvp-bracket/{pvpBracket}`、`soulbinds` |
| Talent API | `talent-tree/index`、`talent/index`、`talent/{talentId}` | `pvp-talent/index` | `pvp-talent/{pvpTalentId}`、`talent-tree/{talentTreeId}`、`talent-tree/{talentTreeId}/playable-specialization/{specId}` |
| Tech Talent API | — | `tech-talent-tree/index`、`tech-talent/index` | `media/tech-talent/{techTalentId}`、`tech-talent-tree/{techTalentTreeId}`、`tech-talent/{techTalentId}` |
| Title API | `title/index`、`title/{titleId}` | — | — |
| Toy API | `toy/index`、`toy/{toyId}` | — | — |
| WoW Token API | — | — | `token/index` |

- Character Profile API 一列的路徑省略 `/profile/wow/character/{name}-{surname}/` 前綴。
- `spell/17123`（強化寧靜）及其 `media/spell/17123` 都回 200。兩種路徑的 `1308777`、`196607` 和 `133` 樣本都回 404。
- `/profile/user/wow`、帳號收藏和 `protected-character` 共 9 個端點需要使用者 OAuth 授權，本次略過。`fixture/{fixtureId}` 缺少可用的測試 ID。
- `quest/index`、`mythic-keystone/index` 和 `modified-crafting/index` 只回子索引連結。任務子索引有資料，傳奇鑰石與進階製造的子索引無清單。

## 本機查詢工具

`scripts/forever_api.py` 只用標準庫，依路徑自動選 namespace（`/profile/` 與公會用 profile，ruleset 與拍賣用 dynamic，其餘 static），`--ns` 可覆寫。預設 TW 區、`zh_TW`；`--locale all` 回傳所有語系。

`BLIZZARD_CLIENT_ID` 和 `BLIZZARD_CLIENT_SECRET` 都有設定時優先採用。否則 Windows 會讀取家目錄的 `.config/wow-forever/battlenet.xml`，macOS 會讀取鑰匙圈 service `wow-forever-battlenet`（帳號為 Client ID，密碼為 Secret）。各台電腦的設定方式記在 `local.md` 的「Battle.net API 憑證位置」，只記位置和狀態。

首次設定時，在 **API Access → Manage Client** 取得 Client ID 和 Secret。若更換 Actions 使用的同一組 Secret，同步更新 repo 的 `BLIZZARD_CLIENT_SECRET`。 [Battle.net API Access](https://community.developer.battle.net/access/clients)

**macOS**：存一次即可。提示輸入的 password 兩次都貼 client secret；第一次讀取若跳出鑰匙圈存取詢問，選「永遠允許」。

```sh
security add-generic-password -s wow-forever-battlenet -a '<client id>' -w
security find-generic-password -s wow-forever-battlenet  # 確認有這筆，不會顯示 secret
```

在 **Windows** 上已有 `battlenet.xml` 時，從 repo 根目錄直接執行 `python '.agents\skills\wow-forever\scripts\forever_api.py' get /data/wow/ruleset/index`。腳本會用 `Import-Clixml` 載入憑證，成功時會看到 `HTTP 200 dynamic-forever-tw`。同一台電腦、同一個 Windows 帳號的新對話可直接執行這個指令。 [Microsoft 的 Windows 憑證加密說明](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/export-clixml#example-3-encrypt-an-exported-credential-object-on-windows)

首次在 Windows 設定時，由使用者在 PowerShell 執行以下指令。Secret 輸入時會遮蔽，`Export-Clixml` 以 DPAPI 加密 Secret 後儲存在 repo 外。

```powershell
$credentialPath = Join-Path $env:USERPROFILE '.config\wow-forever\battlenet.xml'
$clientId = (Read-Host 'Client ID').Trim()
$clientSecret = Read-Host 'Client Secret' -AsSecureString
$credential = [pscredential]::new($clientId, $clientSecret)
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $credentialPath) | Out-Null
$credential | Export-Clixml -LiteralPath $credentialPath -NoClobber
```

- Windows 出現 `No Battle.net credentials` 時，檢查 `battlenet.xml` 是否存在。若出現 `Could not load the Windows Battle.net credential`，確認目前使用建立該檔的 Windows 帳號及電腦。
- 中文角色名在 PowerShell 直接輸入即可。輸出是 UTF-8；導向檔案或管線時中文變亂碼，先執行 `[Console]::OutputEncoding = [Text.Encoding]::UTF8`。

查詢範例中的 `<skill-dir>` 是 `.agents/skills/wow-forever`。Windows 可用 `python` 或 `py` 執行。

```sh
python3 '<skill-dir>/scripts/forever_api.py' get /data/wow/ruleset/index
python3 '<skill-dir>/scripts/forever_api.py' get /data/wow/search/item --param name.zh_TW=亞麻布 --param _pageSize=5
python3 '<skill-dir>/scripts/forever_api.py' character '<name>-<surname>' --part professions
```

- 狀態行（HTTP、namespace、`Last-Modified`）印到 stderr，JSON 印到 stdout；預設去掉 `_links`，`--links` 保留。非 200 時結束碼為 1。
- Token 只在記憶體與標頭中，不寫檔、不印出。
- 角色資料只輸出到終端機回答當次問題，不寫進 repo、技能或測試資料（見 SKILL.md 的公開 repo 規則）。

## 涵蓋率探測

`scripts/forever_api_coverage.py` 讀官方入口的端點清單 JSON（不需登入），換成永恆路徑後逐一呼叫：

- 來源：`https://community.developer.battle.net/api/pages/content/documentation/{world-of-warcraft|world-of-warcraft-classic}/{game-data-apis|profile-apis}.json`，`resources[].methods[]` 的 `path` 與 `parameters[].defaultValue`；`namespace` 預設值的前綴（`static`／`dynamic`／`profile`）決定先試哪一類。另加永恆專屬的 ruleset 與拍賣路徑。
- 角色路徑換成 `{name}-{surname}`，公會換成 `{slug}`（預設試「黎明之劍」），`/profile/user/*` 標為需要使用者 token 而不呼叫。
- ID 先從索引與上層文件取得（例如 profession → skill tier → recipe、ruleset → 拍賣場 → 掛單裡的物品），取不到才用官方預設值與經典版常見 ID；最後一層最多試 3 個 ID，static 與 dynamic 都會試。
- 測試角色讀環境變數 `FOREVER_PROBE_CHARACTER`；報告與 JSON 中一律換成 `{character}`，角色端點只保留欄位結構、筆數與等級。
- 本機可執行 `forever_api_coverage.py --regions tw --out <本機報告路徑>.json`，沿用 [本機查詢工具](#本機查詢工具) 的憑證來源。腳本輸出 Markdown，`--out` 另存逐端點 JSON。

在 GitHub Actions 手動執行 `api-probe.yml`（輸入 `regions`），憑證與 `FOREVER_PROBE_CHARACTER` 來自 repo Secrets，結果在 Step Summary 與 `api-probe` artifact（保留 14 天）：

```sh
gh workflow run api-probe.yml -f regions=tw
gh run download <run id> -n api-probe
```

## 重新查證

1. 官方是否已出永恆文件：抓上面四份端點 JSON 與 `.../documentation/world-of-warcraft-classic/guides/namespaces.json`，搜尋 `forever`。
2. 執行 `api-probe.yml` 或在本機跑 `forever_api_coverage.py`，把結果與[端點實測表](#端點實測表)比對。參數化端點若只測到 404，用已知可用的 ID 補測，再更新可用性和 static 版本。
3. 重讀 [blizzard.pinta.land/forever](https://blizzard.pinta.land/forever/) 各頁的 *Last checked* 日期與 [API Discussion](https://us.forums.blizzard.com/en/blizzard/c/api-discussion) 的新討論。
4. 更新本檔的查證日期與可信度標記；影響資料來源選擇時，同步改 [public-data-sources.md](public-data-sources.md) 的「依需求選來源」表。
