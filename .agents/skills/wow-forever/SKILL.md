---
name: wow-forever
description: 處理《魔獸世界：永恆》（WoW Forever／wowf）的台服玩法、專業與傳承規劃、相關 GitHub Pages 網站維護與資料串接（Battle.net API、客戶端資料表、Wowhead），以及客戶端安裝與版本管理、插件管理與 Lua 錯誤排查。使用者提到魔獸永恆、_forever_ 或永恆版插件時使用；其他魔獸版本先確認分支。
---

# 魔獸世界永恆

使用台灣繁體中文，沿用台服名稱，保留插件名稱、指令、檔名與 API 的原文。

以台灣繁中客戶端為主要查證情境。挑選插件時優先評估完整 `zhTW` 語系、中文字型與既有功能重疊；`zhCN` 回退須明確說明，不能統稱為完整繁中支援。

遊戲版本、插件與安裝建議預設以 Forever 為目標；移除其他版本的操作範圍依當次要求判斷。

## 角色與設定位置

依當次提供的角色、陣營、種族、專精、專業與玩法目標判斷。公開網站的方案是規劃範例，不能當成提問者的實際角色現況；角色的種族／職業組合依永恆規則核對。

核對目前安裝根目錄及目標角色資料夾後，檢查插件啟用情況時優先讀 `_forever_/WTF/Account/<帳號>/<伺服器>/<角色>/AddOns.txt`。設定依插件宣告區分角色層 `SavedVariables` 與帳號層 `WTF/Account/<帳號>/SavedVariables`；磁碟紀錄可能落後遊戲內尚未儲存的狀態。

這是公開 repo 的共用技能。文件與範例使用佔位符或 repo 相對路徑；帳號目錄、私人角色與 BattleTag、本機絕對路徑、憑證及未公開聯絡資訊留在當次操作環境，不寫回技能、範例或測試資料。公會公開聯絡方式由 repo 既有招生內容取得。

## 辨識目標

從使用者指定的版本、路徑與既有對話確認目標；「永恆」對應 WoW Forever，不能直接套用 Classic Era、週年版、探索賽季或現代版的相容性與玩法結論。

涉及本機插件時，讀安裝根目錄 `.build.info` 中啟用的 `wowf` 資料、`_forever_/.flavor.info` 與插件 `.toc`。同一根目錄可能同時裝有多種魔獸版本，依 Product 選列，不能取第一筆版本。可用隨附的唯讀工具：

```powershell
python '<skill-dir>\scripts\inspect_install.py' --root '<WoW 安裝根目錄>' --addon '*AtlasLoot*'
```

將 `<skill-dir>` 與 `<WoW 安裝根目錄>` 換成當前環境的實際目錄。`--root` 可傳安裝根目錄或 `_forever_` 目錄；省略 `--addon` 會盤點所有插件。工具列出各 `.toc` 的宣告，並不代表遊戲實際載入該檔案或已驗證執行正常。

涉及只保留永恆、停用 CurseForge 的 Retail、Battle.net 解除安裝、共用 `Data` 或執行中阻擋訊息時，讀 [references/client-installation.md](references/client-installation.md)。該檔區分插件管理停用、遊戲解除安裝與實際完成狀態。

## 挑選與比較插件

依用途挑插件、比對現有組合，或使用者提到巴哈的永恆插件整理／開服前推薦時，讀 [references/addon-selection.md](references/addon-selection.md)。該檔合併兩篇社群主文的候選、功能取捨與已驗證的 AnoUI 語系線索；候選清單本身不保證目前相容。

查 GnomeLevelUp、RestedXP Guide、Shortest Path Forever、Waypoint UI、Baganator／Syndicator、Platynator、Immersion、Leatrix Plus／Maps、DungeonJournal、DungeonsForever 或 Auctionator 的功能、指令、相依插件與繁中支援，或使用 DungeonsForever＋Auctionator 計算專業衝等成本、掃描行情與匯入材料清單時，讀 [references/addon-feature-guide.md](references/addon-feature-guide.md)。該檔含作者發佈與套件內容的查證、操作流程及既有插件的功能重疊。DungeonsForever、ForeverDungeons、DungeonJournal 是不同專案；後者的 Forever 套件目錄為 `ForeverDungeonJournal`，依專案 ID 與目錄辨識。

- 開啟作者專案頁和具體發佈檔案頁，核對專案 ID、Forever flavor、支援的遊戲版本、更新日期與變更內容。搜尋標題與網址 slug 只當作線索。
- 將已安裝 `.toc` 的 `Version`、`Interface`、`X-Curse-Project-ID` 與上游檔案比對。不同專案的版本號不能直接比較大小；明確支援目標分支與相關修正比下載量更有判斷力。
- 多個專案都支援時，說明可選範圍，再依使用者需求、維護狀況與既有安裝推薦。現有版本符合需求時直接指出是否需要更換。
- AtlasLoot 名稱／網址對應與版本辨識，查閱 [references/environment-and-atlasloot.md](references/environment-and-atlasloot.md)。該檔的版本紀錄是有日期的快照；回答「最新」或建議更換前重新查證。
- 比較 GearInsight 與 AnoUI+、AtlasLoot、Questie 或 LFG Forever 的功能時，讀 [references/gearinsight-overlap.md](references/gearinsight-overlap.md)，包含與 AnoUI 的攻略／介面分工、Group 子模組實際打包內容及繁中處理。官網歷史紀錄提及測試功能時，以本機版本的 `.toc`、實作及啟用條件判斷能否取代現有插件。
- `.toc` 版本吻合屬於宣告相容。API 變動、依賴缺少或遊戲內錯誤仍需另外驗證，修改 Interface 數字不能證明修復。
- 繁中問題分別核對遊戲版本相容、`zhTW` 選單翻譯、中文資料內容與字型顯示；作者說「支援中文」時，查清是 `zhTW`、`zhCN` 或兩者共用。比較整合 UI 時逐項判斷重複模組，避免將介面外觀當成任務／掉落資料庫的替代品。

## 安裝與更新

詢問哪個插件只授權查證與建議；使用者要求安裝、更新或修復時，再執行相應的檔案操作。

優先沿用當前使用的插件管理器。透過 CurseForge 管理時，提供對應專案頁，並從當前安裝或系統捷徑找到程式；不預設管理器版本、使用者目錄或遊戲安裝磁碟。已由管理器維護的插件沿用相同來源。

1. 在管理器確認選到 WoW **Forever**，並核對實際安裝根目錄下的 `_forever_`，最終插件位置為其 `Interface/AddOns`。開始替換前確認遊戲已關閉；執行中可先查證來源與版本。
2. 核對要安裝的專案 ID、發佈檔案與遊戲版本。更新前將要替換的現有插件目錄備份到 `AddOns` 外；若曾做本機修補，先確認更新會覆寫的差異。保留 `WTF`、SavedVariables 與其他插件。
3. 透過已確認的管理器執行本次要求的安裝或更新。整包插件的子模組一併核對，避免新舊混裝。
4. 回讀最終目錄、`.toc` 版本與專案 ID；有可用遊戲環境時再驗證載入、功能與 Lua 錯誤。沒有遊戲內證據時，明確回報完成的是檔案層驗證。下載或套件驗證失敗時保留原安裝，停止替換並回報具體原因。

GitHub 專用分支、CurseForge 無法提供相容檔案，或使用者明確指定手動安裝時，再採用 ZIP 流程：從已確認的作者發佈來源下載至暫存位置，檢查 ZIP 路徑、頂層插件目錄、`.toc` 與必要依賴後，只替換目標套件。最終布局應為 `AddOns/<插件目錄>/<檔名>.toc`，避免多包一層 ZIP 名稱目錄，並完成相同的備份與驗證。

## 排查錯誤

以完整錯誤訊息、觸發動作、遊戲版本及插件版本定位問題。核對載入的分支、缺失依賴、重複目錄與子模組版本，再縮小到最少相關插件重現。

先針對可疑插件停用或修復；涉及重設時，先保留該插件的 SavedVariables 備份，讓使用者能復原設定。遊戲內驗證指令與 API 以目前 Forever 版本可用項目為準。區分作者發佈的更新與本機暫時修補，記錄修改位置、原因及復原方法。

## 玩法、配裝與台服資訊

以目前永恆版本與內容階段查證職業、天賦、裝備、掉落和活動資訊；依題目需要補足等級、專精、陣營與玩法目標，優先使用既有上下文。台服可用時間與活動日期以台灣時區表達。

傳承點數、跨角色專業分工、雙製造小號、雙採集轉製造，或參考 GearInsight 的職業專業推薦時，讀 [references/professions-and-legacy.md](references/professions-and-legacy.md)。其中區分官方規則、插件的升級目標與現行四版分配；點數上限與專業改動仍須按當前日期重查。

官方公告與更新內容從 [永恆官網](https://worldofwarcraft.blizzard.com/zh-tw/forever/) 和 [台灣官方新聞](https://worldofwarcraft.blizzard.com/zh-tw/news/) 查證；物品與法術的繁中資料可查 [Wowhead 永恆](https://www.wowhead.com/forever/tw/)；插件行為以作者文件、發佈說明與原始碼為依據。舊經典版資料僅能作待驗證線索，無法核實的永恆細節就標明不確定。

回報先給可採取的結論，再列關鍵版本依據、來源連結與驗證範圍。只要確實讀過本機，就可說明目前已裝的版本；勿把磁碟上的插件目錄存在說成遊戲內運作正常。

## 公開專業規劃網站

維護「永恆・專業議事廳」、調整專業分配頁的預設方案，或更新其 GitHub Pages 發布時，讀 [references/profession-planner-site.md](references/profession-planner-site.md)。網站面向一般玩家，01 雙採集主號＋三隻雙製造小號為預設首選，聖騎士多路線放 04；repo 相對路徑、正式網址、方案連結與驗證重點集中於該檔。

## 公開資料與官方 API

查官方 Battle.net API、客戶端版本與資料表、Wowhead、官方論壇、參考資料站，或為網站規劃外部資料串接時，讀 [references/public-data-sources.md](references/public-data-sources.md)。永恆 API 未文件化，該檔逐項標註官方文件、社群實測或本次實測；引用時沿用標記，並依日期重新查證。

## 公會與招募文案

涉及《黎明之劍》公會、招募文章、公開聯絡欄，或沿用既有文案意象與插圖時，讀 [references/dawnblade-guild.md](references/dawnblade-guild.md)。該檔記錄公開招募資訊來源、文案方向與 repo 圖片位置。
