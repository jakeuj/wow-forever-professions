# 永恆 Battle.net API 端點實測與重新查證

核對特定端點、樣本限制或重跑涵蓋率探測時讀本檔。查詢規則見 [Battle.net API（永恆）](battlenet-api.md)。

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

## 涵蓋率探測

`scripts/forever_api_coverage.py` 讀官方入口的端點清單 JSON（不需登入），換成永恆路徑後逐一呼叫：

- 來源：`https://community.developer.battle.net/api/pages/content/documentation/{world-of-warcraft|world-of-warcraft-classic}/{game-data-apis|profile-apis}.json`，`resources[].methods[]` 的 `path` 與 `parameters[].defaultValue`；`namespace` 預設值的前綴（`static`／`dynamic`／`profile`）決定先試哪一類。另加永恆專屬的 ruleset 與拍賣路徑。
- 角色路徑換成 `{name}-{surname}`，公會換成 `{slug}`（預設試「黎明之劍」），`/profile/user/*` 標為需要使用者 token 而不呼叫。
- ID 先從索引與上層文件取得（例如 profession → skill tier → recipe、ruleset → 拍賣場 → 掛單裡的物品），取不到才用官方預設值與經典版常見 ID；最後一層最多試 3 個 ID，static 與 dynamic 都會試。
- 測試角色讀環境變數 `FOREVER_PROBE_CHARACTER`；報告與 JSON 中一律換成 `{character}`，角色端點只保留欄位結構、筆數與等級。
- 本機可執行 `forever_api_coverage.py --regions tw --out <本機報告路徑>.json`，沿用 [本機查詢工具](battlenet-local-tools.md#本機查詢工具) 的憑證來源。腳本輸出 Markdown，`--out` 另存逐端點 JSON。

在 GitHub Actions 手動執行 `api-probe.yml`（輸入 `regions`），憑證與 `FOREVER_PROBE_CHARACTER` 來自 repo Secrets，結果在 Step Summary 與 `api-probe` artifact（保留 14 天）：

```sh
gh workflow run api-probe.yml -f regions=tw
gh run download <run id> -n api-probe
```

## 重新查證

1. 官方是否已出永恆文件：抓上面四份端點 JSON 與 `.../documentation/world-of-warcraft-classic/guides/namespaces.json`，搜尋 `forever`。
2. 執行 `api-probe.yml` 或在本機跑 `forever_api_coverage.py`，把結果與[端點實測表](#端點實測表)比對。參數化端點若只測到 404，用已知可用的 ID 補測，再更新可用性和 static 版本。
3. 重讀 [blizzard.pinta.land/forever](https://blizzard.pinta.land/forever/) 各頁的 *Last checked* 日期與 [API Discussion](https://us.forums.blizzard.com/en/blizzard/c/api-discussion) 的新討論。
4. 更新本檔的實測表與 [日常查詢參考](battlenet-api.md#實測結論) 的查證日期與可信度標記；影響資料來源選擇時，同步改 [public-data-sources.md](public-data-sources.md) 的「依需求選來源」表。
