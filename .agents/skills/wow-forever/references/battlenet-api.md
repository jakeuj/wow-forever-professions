# Battle.net API（永恆）

查證日期：2026-11-18（Asia/Taipei）。每項沿用 [public-data-sources.md](public-data-sources.md) 的可信度標記：

- **官方文件**：Battle.net 開發者入口寫明，但寫的是 Retail 或 Classic。
- **社群實測**：開發者論壇與第三方函式庫的探測，可能無預警變動。
- **本次實測**：查證當日以 `scripts/forever_api_coverage.py` 或 `scripts/forever_api.py` 直接請求的結果。

寫進網站或回答「目前能不能查」之前，依[重新查證](#重新查證)重跑。

## 實測結論

可信度：本次實測，2026-11-18 在 GitHub Actions 執行 `api-probe.yml`（[run 44290066755](https://github.com/jakeuj/wow-forever-professions/actions/runs/44290066755)、[run 44290944141](https://github.com/jakeuj/wow-forever-professions/actions/runs/44290944141)），TW 區、static 版本 `1.60.1_70399`。官方 Retail＋Classic 文件的 218 個端點中，113 個回 200（其中約 30 個是空索引）、64 個回 404、9 個需要使用者 token。2026-11-19 再帶測試角色（Lv33 部落）跑一次（[run 44447493169](https://github.com/jakeuj/wow-forever-professions/actions/runs/44447493169)），角色的 31 個端點 25 個回 200、6 個回 404。

對專業網站與回答玩家問題有用的結論：

- **專業與配方可直接查**：`profession/index` 列出 13 個專業（zh_TW）；`profession/{id}` 的 `skill_tiers` 指向 `profession/{id}/skill-tier/{tierId}`，內含 `minimum_skill_level`／`maximum_skill_level` 與 `categories[].recipes[]`（裁縫一個 tier 65 筆）；`recipe/{id}` 有 `crafted_item`、`crafted_quantity` 與 `reagents[]`（`reagent`＋`quantity`）。配方沒有變黃／變綠／變灰點數，練等路線仍要客戶端 `SkillLineAbility` 或 wowf.io。
- **物品資料與官方圖示**：`item/{id}` 有 `quality`、`item_class`、`required_level`、`purchase_price`、`sell_price`、`is_stackable`；`media/item/{id}` 的 `assets[].value` 是 `https://render.worldofwarcraft.com/forever-tw/icons/56/{file_data_id}.jpg`。但拍賣場上仍有約四成物品在 `item/{id}` 回 404，名稱與圖示要保留客戶端資料表與 Wowhead 備援。
- **搜尋可用**：`search/item`、`search/spell`、`search/creature`、`search/mount`、`search/media`、`search/item-appearance` 回結果。搜尋結果的名稱是所有語系的物件，即使帶了 `locale`；用 `name.zh_TW=` 篩選。
- **拍賣商品類有資料**：`/commodities` 回 200，清單的 key 是 `auctions`（不是 `commodities`），每筆 `id`、`item.id`、`quantity`、`unit_price`、`time_left`；聯盟 110 號在 10:06 UTC 有 11,725 筆。repo 的收集與探測腳本原本只讀 `commodities` key 而漏掉，2026-11-19 已修正，每小時資料現在包含材料與藥水，見[拍賣場](#拍賣場)。
- **任務、聲望、法術、坐騎、寵物、玩具、稱號、成就、天賦**的索引與明細都有 zh_TW 資料；`quest/{id}` 有 `requirements`、`rewards`。
- **角色專業可查**：`/profile/wow/character/{name}-{surname}/professions` 回 `primaries[]`（主專業，測試角色 2 個）與 `secondaries[]`（副專業 3 個），每項是 `profession` 加 `tiers[]`，已學配方在 `tiers[].known_recipes[]`（測試角色一個 tier 40 筆）。每個 tier 有 `tier`（`name`、`id`，例如鍛造 2938）、`skill_points`、`max_skill_points`（尚未學下一階時是 225）與 `known_recipes[]`（`name`、`id`，連到鎖版本的 `static-1.60.1_70399-forever-tw`）（本次實測，2026-11-19 以 `forever_api.py` 查詢）。**角色端點的名稱一律是英文**，帶 `locale=zh_TW` 或不帶都一樣是字串；要顯示繁中，用 `id` 查 static 的 `profession/{id}`、`recipe/{id}`（例：recipe 1986 為「玉蛇刀」）。中文角色名直接當 slug（`名字-姓氏`）可查。
- **公會用中文名當 slug 可查**：`/data/wow/guild/黎明之劍`（`profile` namespace）回 200，roster 166 人（含 `rank`）；`achievements` 與 `activity` 只有公會標頭，沒有內容。
- **仍然沒有**：副本手冊（journal 索引全空，明細 404），所以首領掉落仍無官方來源；realm、connected realm、WoW 代幣、PvP 賽季、傳奇鑰石賽季、名人堂、住宅、盟約、艾澤萊精華、傳家寶、寵物技能、pvp／tech 天賦皆為 404 或空索引。

## 官方指南重點

可信度：官方文件，2026-11-18 讀取 [Using APIs](https://community.developer.battle.net/documentation/guides) 與 WoW、WoW Classic 兩組指南。

官方入口**沒有永恆章節**：WoW 與 WoW Classic 的 20 頁指南與 API 參考都沒有出現「forever」，Classic 的 namespace 表只列 Era（`classic1x`）、Mists 進度服（`classic`）、周年服（`classicann`）。以下規則是通用規則或 Retail／Classic 的寫法，永恆差異見[下一節](#永恆與官方文件的差異)。

### 帳號與 client

- 開發者帳號要綁 Battle.net 驗證器（兩步驟驗證），並同意 Blizzard Developer API 使用條款。
- 在 [API Access](https://community.developer.battle.net/access/clients) 建立 client，每人最多 50 個。client 名稱全站唯一，網站使用者可能看得到。
- 換 secret 時可設定舊 secret 的到期時間，期間新舊都能用，方便先更新 repo Secrets 再讓舊的失效。
- Client secret 只放伺服器端、CI Secrets 或本機鑰匙圈，不寫進前端或 repo。

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

`us`、`eu`、`kr`、`tw` 可用；`cn` 要中國的 client。目前版本寫在任一 static 回應 `self` 連結的 `namespace` 參數。到 2026-11-16 只出現過 `1.60.1_70399`，比客戶端舊；版本更新後舊版是否保留未知。

### Ruleset 取代伺服器

永恆沒有 realm：`/data/wow/realm/index` 回 404，realm search 沒有結果。改用 `dynamic` 的 `/data/wow/ruleset/index` 與 `/data/wow/ruleset/{id}`，回傳 `id`、`name`、`status`（`UP`／`DOWN`）與拍賣場連結。TW 與 KR 只有 `1` PvP、`2` Normal；US 與 EU 另有 `3` Roleplay、`15` Roleplay PvP。

### 角色與公會

- 角色名稱是「名字＋姓氏」，全區唯一，以小寫 `{name}-{surname}` 查詢，不帶 realm，例如 `/profile/wow/character/{name}-{surname}?namespace=profile-forever-tw`。
- 角色要達 Lv10 並在該等級登出後才查得到；之前所有角色端點都回 404。資料是登出當下的快照，通常數秒內更新。
- 角色資料以 `surname`、`ruleset` 取代 `realm`，沒有 `active_spec`、`active_title`。
- 子端點（本次實測，2026-11-19，Lv33 角色）：achievements（含 statistics）、appearance、collections（mounts、pets、toys、transmogs；heirlooms 為空）、encounters、equipment（含 `equipped_item_sets`）、character-media（4 張圖）、mythic-keystone-profile（只有 `current_period`）、professions、pvp-summary（`honorable_kills`、`pvp_rank`）、quests（進行中與 `completed`）、reputations、specializations、statistics、status、titles 都回 200。collections/decor、house、hunter-pets、mythic-keystone 賽季、pvp-bracket、soulbinds 回 404。`encounters` 的團本與地城是空的，60 級角色也一樣（pinta，2026-11-16）。
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
- **`/commodities` 的清單 key 是 `auctions`**（Retail 是 `commodities`）。2026-11-18 本次實測：聯盟 110 號 11,725 筆，每筆 `id`、`item.id`、`quantity`、`unit_price`、`time_left`。讀取時兩個 key 都要接受。
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

可信度：本次實測，2026-11-18（TW、`static-1.60.1_70399-forever-tw`）；角色端點為 2026-11-19 [run 44447493169](https://github.com/jakeuj/wow-forever-professions/actions/runs/44447493169)。路徑省略 `/data/wow/` 前綴；「空」表示 200 但列表沒有內容。`{guild}` 用「黎明之劍」測試。

| API | 可用（200，有資料） | 200 但清單是空的 | 404 |
| --- | --- | --- | --- |
| Achievement API | `achievement-category/index`、`achievement-category/{achievementCategoryId}`、`achievement/index`、`achievement/{achievementId}`、`media/achievement/{achievementId}` | — | — |
| Auction House API | — | — | `auctions/commodities`、`connected-realm/{connectedRealmId}/auctions`、`connected-realm/{connectedRealmId}/auctions/index`、`connected-realm/{connectedRealmId}/auctions/{auctionHouseId}` |
| Azerite Essence API | — | `azerite-essence/index`、`search/azerite-essence` | `azerite-essence/{azeriteEssenceId}`、`media/azerite-essence/{azeriteEssenceId}` |
| Connected Realm API | — | `search/connected-realm` | `connected-realm/index`、`connected-realm/{connectedRealmId}` |
| Covenant API | — | `covenant/conduit/index`、`covenant/index`、`covenant/soulbind/index` | `covenant/conduit/{conduitId}`、`covenant/soulbind/{soulbindId}`、`covenant/{covenantId}`、`media/covenant/{covenantId}` |
| Creature API | `creature-family/index`、`creature-family/{creatureFamilyId}`、`creature-type/index`、`creature-type/{creatureTypeId}`、`creature/{creatureId}`、`media/creature-display/{creatureDisplayId}`、`media/creature-family/{creatureFamilyId}`、`search/creature` | — | — |
| Guild API | `guild/{guild}`、`guild/{guild}/achievements`、`guild/{guild}/activity`、`guild/{guild}/roster` | — | — |
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
| Quest API | `quest/index`、`quest/area/index`、`quest/area/{questAreaId}`、`quest/category/index`、`quest/category/{questCategoryId}`、`quest/type/index`、`quest/type/{questTypeId}`、`quest/{questId}` | — | — |
| Realm API | — | `search/realm` | `realm/index`、`realm/{realmSlug}` |
| Region API | `region/index` | — | `region/{regionId}` |
| Reputations API | `reputation-faction/index`、`reputation-faction/{reputationFactionId}`、`reputation-tiers/index`、`reputation-tiers/{reputationTiersId}` | — | — |
| Ruleset API | `ruleset/index`、`ruleset/{rulesetId}`、`ruleset/{rulesetId}/auctions/`、`ruleset/{rulesetId}/auctions/{auctionHouseId}`、`ruleset/{rulesetId}/auctions/{auctionHouseId}/commodities` | — | — |
| Spell API | `media/spell/{spellId}`、`search/spell`、`spell/{spellId}`（不是每個 ID 都有） | — | — |
| Character Profile API | `character`、`status`、`achievements`、`achievements/statistics`、`appearance`、`collections`、`collections/{mounts\|pets\|toys\|transmogs}`、`equipment`、`character-media`、`professions`、`pvp-summary`、`quests`、`quests/completed`、`reputations`、`specializations`、`statistics` | `collections/heirlooms`、`encounters`、`encounters/{dungeons\|raids}`、`mythic-keystone-profile`、`titles` | `collections/decor`、`house/house-{houseNumber}`、`hunter-pets`、`mythic-keystone-profile/season/{seasonId}`、`pvp-bracket/{pvpBracket}`、`soulbinds` |
| Talent API | `talent-tree/index`、`talent/index`、`talent/{talentId}` | `pvp-talent/index` | `pvp-talent/{pvpTalentId}`、`talent-tree/{talentTreeId}`、`talent-tree/{talentTreeId}/playable-specialization/{specId}` |
| Tech Talent API | — | `tech-talent-tree/index`、`tech-talent/index` | `media/tech-talent/{techTalentId}`、`tech-talent-tree/{techTalentTreeId}`、`tech-talent/{techTalentId}` |
| Title API | `title/index`、`title/{titleId}` | — | — |
| Toy API | `toy/index`、`toy/{toyId}` | — | — |
| WoW Token API | — | — | `token/index` |

未列入表格：

- Character Profile API 一列的路徑省略 `/profile/wow/character/{name}-{surname}/` 前綴。
- `spell/{id}` 與 `media/spell/{id}`：17123 回 200，但測試角色天賦裡的法術 ID（如 1292222、196607）與經典版 133 回 404，不是每個法術都有發布。
- `/profile/user/wow` 與帳號 collections、`protected-character`（9 個）：需要使用者授權碼 token，探測不呼叫。
- `quest/index`、`mythic-keystone/index`、`modified-crafting/index` 只有子索引連結；前者的子索引有資料，後兩者是空的。
- 每個端點的 HTTP 狀態、namespace、欄位與第一筆的欄位結構在 `api-probe` artifact 的 JSON。

## 本機查詢工具

`scripts/forever_api.py` 只用標準庫，依路徑自動選 namespace（`/profile/` 與公會用 profile，ruleset 與拍賣用 dynamic，其餘 static），`--ns` 可覆寫。預設 TW 區、`zh_TW`；`--locale all` 回傳所有語系。

憑證先讀環境變數 `BLIZZARD_CLIENT_ID`／`BLIZZARD_CLIENT_SECRET`，沒設時（只限 macOS）讀鑰匙圈 service `wow-forever-battlenet`（帳號＝client ID、密碼＝secret）。Client ID 與 secret 到 [API Access](https://community.developer.battle.net/access/clients) 的 Manage Client 複製；repo Secrets 存了讀不回來。在入口重新產生 secret 時，要同步更新 repo 的 `BLIZZARD_CLIENT_SECRET`，否則每小時排程會失敗。各台電腦設了哪種方式，記在 `local.md` 的「Battle.net API 憑證位置」。

**macOS**：存一次即可。提示輸入的 password 兩次都貼 client secret；第一次讀取若跳出鑰匙圈存取詢問，選「永遠允許」。

```sh
security add-generic-password -s wow-forever-battlenet -a '<client id>' -w
security find-generic-password -s wow-forever-battlenet  # 確認有這筆，不會顯示 secret
```

**Windows**：工具不讀認證管理員，每開一個 PowerShell 視窗設一次環境變數，關掉視窗就消失。下面的寫法在 Windows PowerShell 5.1 與 PowerShell 7 都能用，secret 遮罩輸入、不留在指令歷史：

```powershell
$env:BLIZZARD_CLIENT_ID = '<client id>'
$env:BLIZZARD_CLIENT_SECRET = [Net.NetworkCredential]::new('', (Read-Host 'client secret' -AsSecureString)).Password
python '<skill-dir>\scripts\forever_api.py' get /data/wow/ruleset/index
```

- 在 repo 根目錄時 `<skill-dir>` 是 `.agents\skills\wow-forever`。Windows 的 Python 指令通常是 `python` 或 `py`，macOS 是 `python3`。
- 不要用 `setx` 或系統設定把 secret 存成永久的使用者環境變數：會以明文留在登錄檔，之後開的每個程式都讀得到。
- 中文角色名在 PowerShell 直接輸入即可。輸出是 UTF-8；導向檔案或管線時中文變亂碼，先執行 `[Console]::OutputEncoding = [Text.Encoding]::UTF8`。
- 成功時 stderr 第一行是 `HTTP 200 dynamic-forever-tw`；出現 `No Battle.net credentials` 表示這個視窗的環境變數沒設好（macOS 則是鑰匙圈沒有那筆）。

查詢範例（Windows 把 `python3` 換成 `python`、路徑分隔改成 `\`）：

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
- 輸出 Markdown 表格（在 Actions 中寫進 Step Summary），`--out` 另存 JSON。一次約 350 次請求。

在 GitHub Actions 手動執行 `api-probe.yml`（輸入 `regions`），憑證與 `FOREVER_PROBE_CHARACTER` 來自 repo Secrets，結果在 Step Summary 與 `api-probe` artifact（保留 14 天）：

```sh
gh workflow run api-probe.yml -f regions=tw
gh run download <run id> -n api-probe
```

## 重新查證

1. 官方是否已出永恆文件：抓上面四份端點 JSON 與 `.../documentation/world-of-warcraft-classic/guides/namespaces.json`，搜尋 `forever`。
2. 執行 `api-probe.yml`（或本機跑 `forever_api_coverage.py`），把結果與[端點實測表](#端點實測表)比對；static 版本變了就更新本檔。
3. 重讀 [blizzard.pinta.land/forever](https://blizzard.pinta.land/forever/) 各頁的 *Last checked* 日期與 [API Discussion](https://us.forums.blizzard.com/en/blizzard/c/api-discussion) 的新討論。
4. 更新本檔的查證日期與可信度標記；影響資料來源選擇時，同步改 [public-data-sources.md](public-data-sources.md) 的「依需求選來源」表。
