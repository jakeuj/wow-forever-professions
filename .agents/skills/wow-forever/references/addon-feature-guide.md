# 12 款永恆插件功能指南

查證日：2026-11-11（台灣）。依 [CurseForge WoW](https://www.curseforge.com/wow) 入口，核對作者專案、具體發佈檔及套件內容。以下版本是查證快照，安裝／更新時重新核對 Forever 檔案。

查證範圍為套件 `.toc`、語系及必要實作；首輪 12 款以 DungeonJournal 同版本原始碼與其餘 11 款的發佈 ZIP 查證。後續補充的 CraftProfit Forever 和 Syndicator 各有查證日期。這些證據支持「宣告相容／具有語系資料」，不代表已安裝或在遊戲內測試，也不保證每段翻譯完整或符合台服用語。

DungeonsForever 與 Auctionator 的補充線索來自夏一可的 [〈只需2個插件，專業沖點不費腦，也不浪費一分錢！〉](https://www.youtube.com/watch?v=HmOf69erYRw)。以下操作依作者發佈套件查證，不作影片逐字轉述；遊戲版本與插件自身版本分開辨識。

## 專案與發佈快照

以下各檔案頁均列出 **Forever、1.60.1、Release**。多分支共用 ZIP 仍須核對 Forever；首頁的 Main File 可能是 Retail。

| 插件／作者專案 | 專案 ID | 已核對檔案 | 上傳日期 |
| --- | --- | --- | --- |
| [GnomeLevelUp](https://www.curseforge.com/wow/addons/gnomelevelup)／Captain_British | `1723473` | [v1.6.1，9532877](https://www.curseforge.com/wow/addons/gnomelevelup/files/9532877) | 2026-11-09 |
| [RestedXP Guide](https://www.curseforge.com/wow/addons/restedxp-guide)／RestedXP | `486246` | [v4.11.35，9514096](https://www.curseforge.com/wow/addons/restedxp-guide/files/9514096) | 2026-11-08 |
| [Shortest Path Forever](https://www.curseforge.com/wow/addons/shortest-path-forever)／cjber | `1708599` | [v1.30.2-forever，9556421](https://www.curseforge.com/wow/addons/shortest-path-forever/files/9556421) | 2026-11-11 |
| [Waypoint UI](https://www.curseforge.com/wow/addons/waypointui)／AdaptiveX | `1275146` | [1.7.5，9449968](https://www.curseforge.com/wow/addons/waypointui/files/9449968) | 2026-11-05 |
| [Baganator](https://www.curseforge.com/wow/addons/baganator)／plusmouse | `914482` | [846，9512960](https://www.curseforge.com/wow/addons/baganator/files/9512960) | 2026-11-08 |
| [Platynator](https://www.curseforge.com/wow/addons/platynator)／plusmouse | `1361299` | [544，9551652](https://www.curseforge.com/wow/addons/platynator/files/9551652) | 2026-11-11 |
| [Immersion](https://www.curseforge.com/wow/addons/immersion)／MunkDev | `257550` | [1.4.61，8961775](https://www.curseforge.com/wow/addons/immersion/files/8961775) | 2026-09-24 |
| [Leatrix Plus](https://www.curseforge.com/wow/addons/leatrix-plus)／Leatrix | `94855` | [1.60.29-forever，9471872](https://www.curseforge.com/wow/addons/leatrix-plus/files/9471872) | 2026-11-06 |
| [Leatrix Maps](https://www.curseforge.com/wow/addons/leatrix-maps)／Leatrix | `298842` | [1.60.28-forever，9467345](https://www.curseforge.com/wow/addons/leatrix-maps/files/9467345) | 2026-11-06 |
| [DungeonJournal](https://www.curseforge.com/wow/addons/dungeonjournal)／ExehnTV | `1707971` | [ForeverDungeonJournal 2.0.1，9547760](https://www.curseforge.com/wow/addons/dungeonjournal/files/9547760) | 2026-11-10 |
| [DungeonsForever 無限副本手冊](https://www.curseforge.com/wow/addons/dungeonsforever)／yuanyuande（圓圓） | `1709577` | [DungeonsForever2.1.87.zip，9550141](https://www.curseforge.com/wow/addons/dungeonsforever/files/9550141) | 2026-11-10 |
| [Auctionator](https://www.curseforge.com/wow/addons/auctionator)／plusmouse | `6124` | [345，9548985](https://www.curseforge.com/wow/addons/auctionator/files/9548985) | 2026-11-10 |
| [CraftProfit Forever](https://www.curseforge.com/wow/addons/craftprofit-forever)／vystery | `1739431` | [CraftProfit 0.5.14，9764132](https://www.curseforge.com/wow/addons/craftprofit-forever/files/9764132) | 2026-11-23 |

`.toc` 細節：Shortest Path 的版本字串為 `v1.30.2`，發佈檔另有 `-forever` 後綴；Leatrix 兩款同理，`.toc` 版本沒有分支後綴。Waypoint UI 的 `WaypointUI.toc` 列 Retail Interface，包內 **`WaypointUI_Camelot.toc` 才列 `16001`**，因此只讀預設 `.toc` 會誤判。以上其餘目標 `.toc` 均列有 `16001`。

## 1. GnomeLevelUp：升級提示與可學技能

- 顯示升級前後的屬性數值、尚未向訓練師學習的技能圖示／提示／價格，以及未學武器熟練。另有單級耗時、歷史紀錄、主題與動畫；Classic Mode 可減少華麗效果。這是技能學習提醒與升級回饋，沒有提供任務路線或自動學技能。
- `/glu test` 預覽；`/glu options` 設定。1.4.0 起內附 Forever 職業技能目錄，基本功能不再要求逐一掃描訓練師。技能資料異常時才依作者流程使用 `/glu cleartraining`，再拜訪訓練師重建快取。
- `Locals.lua` 具有 `RegisterLocaleBuilder("zhTW", ...)` 與台服字型路徑。作者說明除法文／西班牙文外採機器翻譯；發佈紀錄在 1.5.7 修正聖騎士技能快取、1.6 修正中文方框與語系偵測，查聖騎士技能提醒問題時有參考價值。

## 2. RestedXP Guide：依步驟練等的任務指南

- 按指南安排接任務、完成與回報順序，配合目標箭頭、步驟視窗、目標選取／標記巨集及練等時間統計。可選自動接交任務，也可製作／匯入指南。`/rxp` 或 `/rxpg` 開啟介面。
- **免費插件引擎與完整指南內容分開判斷。** 本次 ZIP 含 Forever 起始區與約 20 級前後的章節，例如部落 `Horde-01-14_Undead.lua`、`Horde-12-22_Barrens.lua`，另有 dungeon 路線；這些檔名不保證所有角色都會剛好在相同等級結束。完整路線有付費方案；[作者 11/3 公告](https://community.restedxp.com/forever-guides-update-major-update/) 提供已購指南下載與商店入口。本次商店停在候位頁，未查證即時價格與完整付費涵蓋範圍。
- `RXPGuides.toc` 將 Questie、RXPGuides_Themes 列為 OptionalDeps。Questie 可補任務位置資料，並非此版宣告的必要前置。選指南時核對 **Forever／陣營／種族／職業及已完成任務**；角色種族／職業組合依永恆規則確認。
- 有 `locale/zhTW.lua` 與本地化 NPC 名稱資料；介面翻譯和每套指南步驟的翻譯覆蓋率分別查證。與 Polestar 同屬任務路線候選，通常擇一跟隨；和 Leatrix Plus 的自動接交重疊。

## 3. Shortest Path Forever：交通與步行路線規劃

- 從地圖目的地或任務規劃行程，綜合步行、已知飛行點、船、飛船、升降梯、地鐵、傳送門與可用傳送能力；步行路線會繞障礙並隨移動重算。顯示分段指示、時間／距離、地圖路線及交通班次。副本內目的地會導向入口，不能視為副本內攻略。
- `/path` 開設定，`/spfnear` 查附近商人／訓練師等服務；Shift 點世界地圖或小地圖設定目的地，任務選單可選 Plan journey。支援 RestedXP／Guidelime 的目前目標，不必為這項整合另裝 TomTom。
- **必要依賴為 cjber 的 [ForeverCore，專案 `1796337`](https://www.curseforge.com/wow/addons/forevercore)**；包內 `Dependencies: ForeverCore` 與作者說明一致。[1.30.1 發佈說明](https://www.curseforge.com/wow/addons/shortest-path-forever/files/9555733) 記錄已改由 CurseForge 隨同安裝核心。名稱相近的 [Forever Core UI，專案 `1743753`](https://www.curseforge.com/wow/addons/forever-core) 屬 Patzlinger 的另一套 UI，不能拿來代替這個依賴。
- `OptionalDeps: QuestieDB, TweaksForever, RXPGuides, Guidelime`；附近 NPC／商人物品查詢使用已安裝的 QuestieDB，不能把這項資料需求說成所有導航功能都必須裝 Questie。
- 有 `Locales/zhTW.lua`；[1.19.0 語系公告](https://www.curseforge.com/wow/addons/shortest-path-forever/files/9209169) 明列繁中，主要為機器翻譯。已自帶方向箭頭與地圖路線；是否再加 Waypoint UI 依想要的世界空間標記決定。

## 4. Waypoint UI：世界空間的目標標記

- 將任務、地圖釘與 POI 顯示為畫面內的 Waypoint／Pinpoint，Navigator 提供即時方向提示；可調顏色、大小、透明度與文字。定位重點是「目標在哪裡與往哪個方向」，交通規劃則搭配路線提供者。
- [1.7.2](https://www.curseforge.com/wow/addons/waypointui/files/8928030) 起加入 Forever；[1.7.4](https://www.curseforge.com/wow/addons/waypointui/files/9264236) 加入 RestedXP 整合，1.7.5 加入更多地圖釘與追蹤設定。不要依搜尋引擎殘留的舊 Retail 摘要誤判無 Forever 支援。
- 包內 `Locales/zhTW.lua` 有繁中翻譯。此版 `.toc` 未宣告額外必要插件；和 Shortest Path、RestedXP 的箭頭可能在視覺上重疊，依目前整合設定保留需要的顯示。

## 5. Baganator：背包分類、整理與搜尋

- 背包／銀行可選整合單一視窗或分類版面，支援排序、忽略指定格、物品名稱／類型等搜尋條件，以及物品圖示角落資訊。另可查已記錄的其他角色庫存；這部分與 BagSync／Account Overview 有交集。
- **必須搭配 [Syndicator，專案 `988370`](https://www.curseforge.com/wow/addons/syndicator)**，作者說明 CurseForge 會自動安裝。即使 846 的 `.toc` 寫 `OptionalDeps: Syndicator, Masque`，`Core/Initialize.lua` 在缺少 Syndicator 時仍提示安裝並中止；因此不能僅靠 OptionalDeps 誤稱 Syndicator 可省略。Masque 是可選外觀整合。
- `/baganator` 或 `/bgr`；`Locales.lua` 具有繁中詞條。Syndicator 是庫存資料層，不是另一套背包外觀。共用專案頁列出的虛空倉庫、帳號銀行等功能，依遊戲分支實際提供的系統判斷，不能全套套用 Forever。
- 與 AnoUI 等整合 UI 的背包模組擇一接管外觀；跨角色查庫存表示檢視快取，不代表能遠端取出物品。846 發佈有 Forever 銀行排序修正。

### Syndicator：讓 agent 讀得到背包

讀取、刷新和核對角色背包、銀行與信箱，見 [Syndicator 跨角色庫存](syndicator-inventory.md)。

## 6. Platynator：可直接套用樣式的姓名板

- 內建多套樣式並可匯入配置；設計器支援拖曳元素與即時預覽。提供血條、施法條、可打斷提示、仇恨／單位狀態顏色及任務目標標示。`/platy` 開啟，Designer 分頁調整版面；此版無額外必要插件宣告。
- `Locales.lua` 含繁中詞條，包內有 `Display/CastBar.lua` 實作。作者的效能比較屬作者測試，不直接轉述成所有電腦都最快。
- 它與 Plater 是不同專案，不共用配置。和 Plater、Threat Plates 或整合 UI 姓名板擇一作主要顯示；「開箱即用」指有預設樣式，不等於適合每種坦／補／輸出需求。

## 7. Immersion：任務與 NPC 對話介面

- 取代任務／閒聊視窗，以角色頭像與分段對話呈現文字。可按鍵繼續、接任務、選對話，並自訂快捷鍵或用數字鍵選選項；不提供練等路線或任務位置資料庫。
- `/immersion` 開啟設定；1.4.61 已改用原生設定面板。`OptionalDeps: ConsolePort` 只表示可選控制器整合，沒有宣告 ConsolePort 為必要前置。
- 有 `Locale/zhTW.lua`；任務正文仍取自遊戲或相關內容來源。閱讀劇情時，先檢查 RestedXP、Polestar、Leatrix Plus 或整合 UI 的自動接交設定，以免對話在讀完前被推進。

## 8. Leatrix Plus：可分項啟用的便利功能

- 自動賣灰色垃圾、修理、接交任務；另有聊天複製／過濾、音效管理、小地圖與提示框等工具。依需求勾選，先與整合 UI 已有模組比較；`/ltp` 開設定。
- 使用本表的 **1.60.x-forever** 檔案。作者共用說明混合多版本功能，不能將 Retail 的每個選項視為 Forever 都有。
- `Leatrix_Plus_Locale.lua` 的 `GameLocale == "zhTW"` 區段包含繁中翻譯；`.toc` 僅列 ElvUI 為 OptionalDeps，基本功能不需要 Leatrix Maps。與 RestedXP／Polestar 的接交任務、其他插件的賣垃圾／修理挑一套負責。

## 9. Leatrix Maps：世界地圖與副本地圖

- 顯示未探索區域、角色／游標座標、地城入口及交通點，可移動／縮放地圖、保留縮放程度並調整戰場地圖。這些地圖資訊不能直接視為自動選出最快交通路線，也不會替角色完成探索。
- `/ltm` 開設定。Forever [1.60.27 起的發佈紀錄](https://www.curseforge.com/wow/addons/leatrix-maps/files/9467345) 已加入副本地圖，含入口／首領位置；副本地圖與 DungeonJournal 的任務前置／掉落資料仍有分工，不能只把它描述成取消地圖迷霧。
- `Leatrix_Maps_Locale.lua` 有 `GameLocale == "zhTW"` 翻譯區段；`.toc` 僅列 ElvUI 為 OptionalDeps。Leatrix Plus 是獨立插件，部分進階整合才需要兩者搭配；並非地圖基本功能的必要前置。

## 10. DungeonJournal：地城任務、入口與掉落手冊

- 遊戲內查首領掉落、地城相關任務與獎勵，點任務可定位地圖；查證的 2.0.1 原始碼另有 `QuestChains.lua`、`DungeonEntrances.lua`、`DungeonRoutes.lua` 與地圖標記，支援行前查詢及部分路線說明。資料會隨官方更動補正，不能以「無限副本手冊」推論所有地城與掉落已完整。
- `/dj` 開手冊，`/dj minimap` 恢復小地圖按鈕；[2.0.1 發佈說明](https://www.curseforge.com/wow/addons/dungeonjournal/files/9547760) 另有 `/dj tracker` 恢復地城追蹤器，以及多處掉落／任務修正，並明列尚待補齊的內容。
- 插件目錄為 `_forever_/Interface/AddOns/ForeverDungeonJournal`，`.toc` 為 `Interface: 16001`、`Version: 2.0.1`，沒有宣告額外必要插件。目錄名與 CurseForge 顯示名稱不同，後續盤點需包含 `ForeverDungeonJournal`。
- `Localization/Locale_zhTW.lua` 與 `Content_zhTW.lua` 分別提供繁中介面／內容，`.toc` 確實列入載入清單；語系解析器依 `zhTW` 客戶端選繁中，可用 `/dj lang zhtw`、`/dj lang auto` 切換。檔案註明由簡中轉換並調整台服詞彙，缺詞回退英文；不能保證所有新增內容均已人工校對。
- 與 AtlasLoot 有掉落查詢交集，與 GearInsight／ForeverDungeons 有地城指南交集。是否取代需比較目標副本、永恆新增內容及所需 BiS／其他資料；地城手冊不取代 DBM 的戰鬥計時與警告。

## 11. DungeonsForever：地城、探索與專業手冊

2026-11-12（台灣）重新核對 [作者專案](https://www.curseforge.com/wow/addons/dungeonsforever)、[發佈檔 9550141](https://www.curseforge.com/wow/addons/dungeonsforever/files/9550141) 與該 ZIP，仍為上表的 2.1.87。該檔同列 Forever／Retail、遊戲版本 `1.60.1`／`12.1.7`，沒有 changelog；介紹文字與套件功能不完全同步，依目標分支的實際載入清單判斷。

- `/df` 或小地圖按鈕開啟。提供地城總覽、首領掉落、任務前置與接交位置、入口地圖標記及部分入口路線；營地與商人也有可點選的位置資料。Forever 另有專業概覽、配方、採集、衝等、傳承與營地資訊，探索模組含書籍追蹤與睡袋任務等內容。手冊資料與導航標記不等於自動完成任務或戰鬥警告。
- **套件模組要分別辨識。** 2.1.87 ZIP 除 `DungeonsForever` 主體外，內含 `DungeonsForeverProf`（專業）、`DungeonsForeverExplore`（探索）、`DungeonsForeverClass`（職業）、`DungeonsForeverGear`（裝備／BiS）、`DungeonsForeverFaction`（聲望）、`DungeonsForeverPvP`、`DungeonsForeverSpell`（技能書）與 `DF_CNLocale`。前述功能子模組均依賴主體，按需載入且可分別停用；`DF_CNLocale` 是供非中文客戶端強制中文的開關，繁中客戶端依原生語系載入。
- **探索與收藏需啟用 `DungeonsForeverExplore`＋主體。** 書籍頁提供陣營篩選、進度與位置標記，另有睡袋任務步驟、法師研究說明及坐騎／寵物／玩具等收藏資料。此版 `Core/ExploreUI.lua` 與繁中 `Data_Explore.lua` 的獎勵畫面包含 10／20／25 本三檔，比專案介紹只提 10／20 本更完整；回答獎勵或研究玩法時仍須核對當前官方規則，包內部分說明保留測試服註記。
- 專業衝等需啟用 **`DungeonsForeverProf`＋主體**。專業模組提供固定攻略、材料清單、步驟追蹤，以及搭配 Auctionator 的自動成本路線；可比較採購、自製與配方依賴，方案有最省錢、穩定升級、材料成本、次數最少等。依當前專業的可用模式與配方資料判斷，不能將採集或每項專業都當成相同的製造路線。
- 主體 `.toc` 列 `Version: 2.1.87`、Interface 含 `16001`，只有 EllesmereUI 為 OptionalDeps。包內專業模組仍列 `2.0.3`、技能書模組列 `2.0.4`；這是同一發佈 ZIP 的實際內容，不能僅因子模組版本不同就判定混裝。套件已內嵌 LibDBIcon／LibDataBroker；[Relations 頁](https://www.curseforge.com/wow/addons/dungeonsforever/relations/dependencies) 的 Embedded Library 不代表需要另裝同名插件。Auctionator 是行情計算與直接匯入的整合來源，並非整個地城手冊的必要前置。
- **繁中證據**：主體 `Locales/zhTW.lua` 檢查 `GetLocale() == "zhTW"`；`.toc` 以 `[AllowLoadTextLocale zhTW]` 載入繁中介面與 `Core/Data/zhTW/` 地城／專業資料。專業模組另載 `Data_ProfRecipes.lua`、`Data_ProfLeveling.lua`，探索模組另載 `Data_Explore.lua` 及收藏等繁中資料。專案頁仍只寫英文／簡中，這份套件已包含繁中檔案；翻譯品質、字型及所有頁面完整度尚未遊戲內實測。
- **設定儲存層級**：主體與子模組以 `SavedVariables` 宣告 `DungeonsForeverDB`、`DungeonsForeverExploreDB` 等帳號層資料；探索模組再用 `角色名-伺服器` 索引書籍進度（`ExploreUI.lua` 的 `CharKey()`／`Found()`）。備份或排查進度時讀對應的帳號層設定檔，不能把「按角色保存進度」當成 `SavedVariablesPerCharacter`，也不能把不同角色的收書紀錄混用。
- **相近名稱不是別名**：本款是 yuanyuande 的 `DungeonsForever`（`1709577`）；[ForeverDungeons](https://www.curseforge.com/wow/addons/foreverdungeons) 是 rakfunk_ 的另一專案（`1715833`），整合於遊戲的尋求組隊視窗；DungeonJournal 則是 ExehnTV 的 `1707971`，Forever 目錄為 `ForeverDungeonJournal`。與 DungeonJournal／AtlasLoot 比較掉落與任務覆蓋，與 GearInsight 比較專業、職業及 BiS 模組；依實際需要選用，不能因名稱相近就推論已裝或可全面取代。地城手冊仍不取代 DBM。

## 12. Auctionator：行情掃描、購物清單與拍賣交易

- 提供物品提示框拍賣價格、完整掃描、篩選搜尋與歷史、購物清單、上架防低價及壓價掃描／取消；製造介面可顯示材料成本與利潤，搜尋所需材料。共用專案頁含 Retail 等分支功能，實際選項依 Forever 套件判斷；作者特別標明的 Retail 自動掃描行為不能直接當成 Forever 的預設。
- 在拍賣場的 Auctionator 分頁按 **完整掃描（Full Scan）** 更新資料，再到購物清單搜尋材料；確認數量與單價後購買。掃描價是該市場的歷史觀測，不代表當下仍有同價存貨，也不會自動完成採買。`/atr` 或 `/auctionator` 顯示指令說明，`/atr version` 查版本；設定由遊戲設定中的 Auctionator 開啟。
- 345 的 `.toc` 列 `Version: 345`、Interface 含 `16001`，只有 LibAHTab 為 OptionalDeps；`Locales/Manifest.xml` 確實載入 `Locales/zhTW.lua`，含完整掃描、購物清單等繁中詞條。基本買賣／掃描不依賴 DungeonsForever。此版 [發佈說明](https://www.curseforge.com/wow/addons/auctionator/files/9548985) 修正 Forever 製造利潤及壓價百分比；回報利潤異常時先核對版本，再查價格來源。
- 繁中介面叫「拍賣小幫手」，拍賣場下方多出「購買／銷售／取消／拍賣小幫手」分頁，購物清單在「購買」分頁。購物清單的匯入格式、讀完整掃描存檔（`/reload` 或登出後才寫入）與價格資料庫不分陣營拍賣場的限制，見 [market-recipe-value.md](auction-market.md#拍賣小幫手auctionator完整掃描)；以上依 347 版原始碼與 2026-11-18 實測。
- 與 DungeonsForever 的分工是「Auctionator 蒐集行情並管理採買；專業模組計算衝等步驟與缺口」。Baganator／Syndicator、BagSync 的庫存查詢不能直接當成拍賣行情來源；分解估價也需另查材料價格與產出假設。

## 13. CraftProfit Forever：專業視窗內的配方利潤排序

2026-11-23 核對 [作者專案](https://www.curseforge.com/wow/addons/craftprofit-forever)、[發佈檔 9764132](https://www.curseforge.com/wow/addons/craftprofit-forever/files/9764132) 與 [作者原始碼](https://github.com/Vystery/CraftProfit)：`CraftProfit.toc` 列 `Interface: 16001`、`Version: 0.5.14`，Auctionator、TradeSkillMaster 只是 OptionalDeps，資料夾為 `CraftProfit`。2026-11-23 站主的 Mac 已安裝，本機 `.toc` 同為 0.5.14，下列算法與存檔格式讀自本機原始碼；遊戲內功能還沒驗證。

- 不開新視窗：內建專業視窗的配方列加上利潤標籤，配方明細多一塊利潤面板，訓練師處標出值得學的配方。`/cf sort` 或專業視窗的「篩選」選單切換按利潤排序（各分類內由高到低），`/cf profit` 只列有賺的配方，`/cf net vendor` 改看賣給商人的淨利，`/cf cut` 設定拍賣手續費。面板的 Shop 可把材料加進它自己的拍賣場購物清單。
- 價格來源用 `/cf source auto|craftprofit|auctionator|tsm` 切換，`/cf scan` 在拍賣場開著時執行內建掃描。作者 README 註明：拍賣小幫手與 TSM 的價格、訓練師標籤都還沒在遊戲內實測，數字可疑時先改回 `/cf source craftprofit`。
- 繁中：原始碼沒有語系檔，`.toc` 也沒有載入任何語系，介面是英文；配方與物品名稱照遊戲客戶端顯示。
- 會對外傳訊：`sendReports` 預設開啟。遊戲擋下動作並點名 CraftProfit 時，紀錄（時間、函式、版本、當時畫面、呼叫堆疊）會密語給作者角色，也會經公會、隊伍裡其他裝了 CraftProfit 的玩家轉送；`/cf report` 會把製作、攜帶與轉送全部關閉。0.5.14 另會從公會與隊伍成員得知有新版，每次登入提示一次，可在選項關閉。
- 和 Auctionator 製造介面的差別：後者也顯示單一配方的成本與利潤，CraftProfit 多了整個專業依利潤排序、訓練師標籤與回本次數。2026-11-22 YouTube 頻道「老吳魔獸」的永恆賺錢專業影片即以 CraftProfit Forever 搭配 Auctionator 示範。
- **算法（`Scanner.lua`、`Calculator.lua`）**，本 repo 腳本可以借用：
  - **深度價**：取最便宜的 20% 在售件數（至少 5、最多 1000 件）照件數加權平均，一張誘餌低價幾乎不影響，整排高價掛單也不會算進去。它的售價預設用最低一口價，`/cf basis market` 才改用深度價。
  - **正常價**：每天記一次深度價、留 14 天，取前 7 天（不含今天）的中位數，要有 3 天資料；今天比正常價低 10% 以上標便宜、高 10% 以上標偏貴。
  - **每日賣出量**：同一物品相隔至少 1 小時的兩次掃描間，件數減少的部分換算成一天；到期與下架也算進去，所以是上限。
  - **淨利**：售價 × 每次產量 − 拍賣抽成（預設 5%）− 製作成本；賣店淨利＝商人收購價 × 產量 − 成本。另算每項材料的「最高能接受價」（超過就不賺）與訓練師配方幾次回本。能自己做的中間材料（礦→錠→零件）在比買便宜時用自製成本，要先開過那個專業視窗。
- **它沒做的**：不排練等路線（不看配方顏色與升級機率），也不算分解價值，所以不能取代 `scripts/leveling_route.py` 或無限副本手冊；本 repo 的路線與快訊目前用最低一口價，可改用上面的深度價。
- **存檔（給 agent 讀）**：帳號層 `SavedVariables/CraftProfit.lua` 的 `CraftProfitDB`（另有角色層 `CraftProfitCharDB`）。`vendor` 是去過的商人賣價（物品 ID → 銅）；`recipeCache` 是客戶端給的配方材料與產量範圍，可拿來核對永恆的實際材料；`learned` 是各角色已學配方；`realms["PvP-Horde"]` 下有 `prices`、`history`（各次掃描的件數，算賣出量用）、`ladders`（價位階梯）、`mv`（深度價）、`daily`（每日深度價）、`purchases`。登出時寫成壓縮格式（`packed = 2`：數字用 36 進位、每串約 150 筆，只留這次或上次用到的物品），解法見 `Core.lua` 的 Compact on-disk format，目前還沒有讀取腳本。2026-11-23 剛裝時檔案是空的，要在拍賣場 `/cf scan`、各專業視窗開過一次才有資料。
- **角色鍵只用名字**：`learned` 與信箱紀錄以「名字-伺服器鍵」區分，不含姓氏；永恆名字相同、姓氏不同的角色會共用一份。站主就有兩隻同名的小號，讀已學配方時不能分出是哪一隻。Mac 上看到的伺服器鍵是 `Unknown`。
- 其他按利潤排序的插件與挑選方式見 [配方利潤排序候選](addon-selection.md#配方利潤排序候選)。

## DungeonsForever 與 Auctionator 專業衝等操作

遊戲內的完整掃描、自動選路、缺料處理及匯入步驟見 [專業衝等操作](profession-addon-workflow.md)。

### 常見狀況

掃描、選路、同步及匯入問題見 [專業衝等常見狀況](profession-addon-workflow.md#常見狀況)。

## 選用時的功能分工

| 想補足的能力 | 優先比較 |
| --- | --- |
| 升級時看屬性與忘記學的技能 | GnomeLevelUp；與目前整合 UI 的技能提醒比較。 |
| 決定下一個任務與練等順序 | RestedXP／Polestar；先核對 Forever 指南、陣營與免費範圍。 |
| 決定如何到目的地 | Shortest Path Forever＋正確的 ForeverCore；附近服務查詢另核對 QuestieDB。 |
| 更醒目的畫面內目標 | Waypoint UI；先試目前導航來源已有的箭頭。 |
| 分類背包及查其他角色庫存 | Baganator＋Syndicator；和整合背包、BagSync／Account Overview 逐項比較。只要 agent 讀庫存時單裝 Syndicator。 |
| 姓名板、任務怪與仇恨顏色 | Platynator／Plater／Threat Plates／整合 UI 選主要來源。 |
| 讀任務劇情 | Immersion；同步檢查自動接交設定。 |
| 便利功能、地圖資訊、地城行前查詢 | 分別評估 Leatrix Plus、Leatrix Maps、DungeonJournal／DungeonsForever，按模組關閉重複功能。 |
| 書籍、睡袋任務與收藏查詢 | DungeonsForever＋探索模組；與 HandyNotes 的書籍／地圖標記逐項比較，先核對目前角色的進度。 |
| 專業衝等步驟、材料缺口與成本 | DungeonsForever＋專業模組＋Auctionator；先取得完整行情，再核對目標技能、配方與庫存。 |
| 拍賣行情與材料採買 | Auctionator；背包／跨角色庫存插件另負責已有物資。 |
| 找出哪些配方有賺、按利潤排序 | CraftProfit Forever；其他候選見 [配方利潤排序候選](addon-selection.md#配方利潤排序候選)。行情來源仍以 Auctionator 完整掃描為主。 |
