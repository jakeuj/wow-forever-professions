---
name: wow-forever
description: 查證《魔獸世界：永恆》（WoW Forever／wowf）台服玩法、插件與客戶端、專業傳承與練等、拍賣與配方利潤，並維護本 repo 的公會官網、GitHub Pages 玩家工具與 Battle.net API 資料串接。
---

# 魔獸世界永恆

使用台灣繁體中文和台服遊戲名稱，保留插件、指令、檔名與 API 原文。台服日期與時刻用台灣時間。

依指定版本、路徑或對話確認目標。永恆是 WoW Forever（`wowf`、`_forever_`）。玩法與相容性以當前 Forever 版本和內容階段查證。公告查[永恆官網](https://worldofwarcraft.blizzard.com/zh-tw/forever/)和[台灣官方新聞](https://worldofwarcraft.blizzard.com/zh-tw/news/)，繁中物品與法術查 [Wowhead 永恆](https://www.wowhead.com/forever/tw/)。以舊經典版資料提供線索時，標明永恆的驗證狀態。

需要個人角色、陣營、安裝目錄或 API slug 時，讀家目錄的 `.config/wow-forever/local.md`（Windows 用 `%USERPROFILE%\.config\wow-forever\local.md`）。要查個人進度時優先用指定角色，未指定時用檔內主角色。按題目重查角色等級、專業點數、已學配方或庫存，並標明資料時間。角色 API 可能落後一兩天，Syndicator 存檔在 `/reload` 或登出時更新。

使用者提供或更正的私人設定寫入 repo 外的 [local.md](references/local.example.md)，需要時依對話確認欄位後建立。公開文件、範例與測試資料使用佔位符或相對路徑。帳號目錄、私人角色、BattleTag、未公開聯絡資訊與本機絕對路徑留在操作環境。憑證依本機工具說明管理，local.md 只記位置。公開公會聯絡資訊以現有招募內容為準。

## 依任務讀取

| 任務 | 參考 |
| --- | --- |
| 選插件、比較功能重疊或繁中支援 | [插件挑選](references/addon-selection.md)、[插件功能與指令](references/addon-feature-guide.md)。比較 GearInsight 和整合 UI、AtlasLoot、Questie 或 LFG Forever 時讀 [GearInsight 分工](references/gearinsight-overlap.md)。 |
| 插件版本、啟用狀態、安裝、更新或 Lua 錯誤 | [插件維護](references/addon-maintenance.md)。分辨同名套件時讀 [AtlasLoot 專案與版本](references/environment-and-atlasloot.md)。 |
| 客戶端安裝、只留永恆、停用 CurseForge Retail 或 Battle.net 卡在解除安裝 | [客戶端版本管理](references/client-installation.md) |
| 背包、銀行、信箱或跨角色庫存 | [Syndicator 庫存](references/syndicator-inventory.md) |
| 傳承點數、雙採集、雙製造小號或跨角色分工 | [專業與傳承](references/professions-and-legacy.md)。個人規劃依當前角色職業、種族和專業，公開網站方案可作範例。 |
| 依技能門檻與庫存算練等路線、材料或成本 | [專業練等試算](references/leveling-route.md) |
| 遊戲內自動選路、完整掃描與缺料清單 | [DungeonsForever＋Auctionator 專業衝等](references/profession-addon-workflow.md) |
| 現價、期間漲跌、跨陣營價差、時段分析、購物清單或掃描截圖 | 選讀 [拍賣行情](references/auction-market.md)的對應章節。問現在該買或賣什麼時，直接讀[行情快訊](references/auction-market.md#行情快訊現在該買賣什麼)。 |
| 配方毛利、NPC／任務來源、囤配方或回本 | [配方毛利與採買](references/market-recipe-value.md)。找遊戲內排序工具時讀 [配方利潤插件](references/addon-selection.md#配方利潤排序候選)。 |
| 遭攔截的木箱、商人貢獻點：哪種箱子便宜、購物清單、算進自己的箱子或遊戲內掃描 | [遭攔截的木箱](references/waylaid-crates.md) |
| 60 級製造、團本消耗品與配方取得優先序 | [後期製造需求](references/endgame-crafting.md) |
| Battle.net 端點、OAuth、namespace、HTTP 429 或核對配方材料與產量 | [官方 API](references/battlenet-api.md) |
| 使用 `forever_api.py` 或設定 DPAPI、macOS 鑰匙圈、環境變數 | [本機查詢與憑證](references/battlenet-local-tools.md) |
| 端點可用性、參數與涵蓋率 | [實測與重新探測](references/battlenet-api-coverage.md) |
| 客戶端資料表、Wowhead、論壇或外部資料整合 | [公開資料來源](references/public-data-sources.md) |
| 公會官網、專業議事廳、個人整理頁、GitHub Pages、拍賣排程或 Cloudflare | [網站維護](references/profession-planner-site.md)。網站程式、來源與產物從 [README 維護地圖](../../../README.md#維護地圖)找。 |
| 《黎明之劍》招募、公開聯絡、文案或插圖 | [公會招募素材](references/dawnblade-guild.md) |
