# 12 款永恆插件功能指南

查證日：2026-11-11（台灣）。依 [CurseForge WoW](https://www.curseforge.com/wow) 入口，核對作者專案、具體發佈檔及套件內容。以下版本是查證快照，安裝／更新時重新核對 Forever 檔案。

查證範圍為套件 `.toc`、語系及必要實作；DungeonJournal 使用同版本原始碼，其餘 11 款檢查對應發佈 ZIP。這些證據支持「宣告相容／具有語系資料」，不代表已安裝或在遊戲內測試，也不保證每段翻譯完整或符合台服用語。

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

- `/df` 或小地圖按鈕開啟。提供地城總覽、首領掉落、任務前置與接交位置、入口地圖標記及部分入口路線；營地與商人也有可點選的位置資料。Forever 另有專業概覽、配方、採集、衝等、傳承與營地資訊，探索模組含書籍追蹤與睡袋任務等內容。手冊資料與導航標記不等於自動完成任務或戰鬥警告。
- **套件模組要分別辨識。** 2.1.87 ZIP 除 `DungeonsForever` 主體外，內含 `DungeonsForeverProf`（專業）、`DungeonsForeverExplore`（探索）、`DungeonsForeverClass`（職業）、`DungeonsForeverGear`（裝備／BiS）、`DungeonsForeverFaction`（聲望）、`DungeonsForeverPvP`、`DungeonsForeverSpell`（技能書）與 `DF_CNLocale`。前述功能子模組均依賴主體，按需載入且可分別停用；`DF_CNLocale` 是供非中文客戶端強制中文的開關，繁中客戶端依原生語系載入。
- 專業衝等需啟用 **`DungeonsForeverProf`＋主體**。專業模組提供固定攻略、材料清單、步驟追蹤，以及搭配 Auctionator 的自動成本路線；可比較採購、自製與配方依賴，方案有最省錢、穩定升級、材料成本、次數最少等。依當前專業的可用模式與配方資料判斷，不能將採集或每項專業都當成相同的製造路線。
- 主體 `.toc` 列 `Version: 2.1.87`、Interface 含 `16001`，只有 EllesmereUI 為 OptionalDeps。包內專業模組仍列 `2.0.3`、技能書模組列 `2.0.4`；這是同一發佈 ZIP 的實際內容，不能僅因子模組版本不同就判定混裝。Auctionator 是行情計算與直接匯入的整合來源，並非整個地城手冊的必要前置。
- **繁中證據**：主體 `Locales/zhTW.lua` 檢查 `GetLocale() == "zhTW"`；`.toc` 以 `[AllowLoadTextLocale zhTW]` 載入繁中介面與 `Core/Data/zhTW/` 地城／專業資料。專業模組另載 `Data_ProfRecipes.lua`、`Data_ProfLeveling.lua` 等繁中資料。專案頁仍只寫英文／簡中，這份套件已包含繁中檔案；翻譯品質、字型及所有頁面完整度尚未遊戲內實測。
- **相近名稱不是別名**：本款是 yuanyuande 的 `DungeonsForever`（`1709577`）；[ForeverDungeons](https://www.curseforge.com/wow/addons/foreverdungeons) 是 rakfunk_ 的另一專案（`1715833`），整合於遊戲的尋求組隊視窗；DungeonJournal 則是 ExehnTV 的 `1707971`，Forever 目錄為 `ForeverDungeonJournal`。與 DungeonJournal／AtlasLoot 比較掉落與任務覆蓋，與 GearInsight 比較專業、職業及 BiS 模組；依實際需要選用，不能因名稱相近就推論已裝或可全面取代。地城手冊仍不取代 DBM。

## 12. Auctionator：行情掃描、購物清單與拍賣交易

- 提供物品提示框拍賣價格、完整掃描、篩選搜尋與歷史、購物清單、上架防低價及壓價掃描／取消；製造介面可顯示材料成本與利潤，搜尋所需材料。共用專案頁含 Retail 等分支功能，實際選項依 Forever 套件判斷；作者特別標明的 Retail 自動掃描行為不能直接當成 Forever 的預設。
- 在拍賣場的 Auctionator 分頁按 **完整掃描（Full Scan）** 更新資料，再到購物清單搜尋材料；確認數量與單價後購買。掃描價是該市場的歷史觀測，不代表當下仍有同價存貨，也不會自動完成採買。`/atr` 或 `/auctionator` 顯示指令說明，`/atr version` 查版本；設定由遊戲設定中的 Auctionator 開啟。
- 345 的 `.toc` 列 `Version: 345`、Interface 含 `16001`，只有 LibAHTab 為 OptionalDeps；`Locales/Manifest.xml` 確實載入 `Locales/zhTW.lua`，含完整掃描、購物清單等繁中詞條。基本買賣／掃描不依賴 DungeonsForever。此版 [發佈說明](https://www.curseforge.com/wow/addons/auctionator/files/9548985) 修正 Forever 製造利潤及壓價百分比；回報利潤異常時先核對版本，再查價格來源。
- 與 DungeonsForever 的分工是「Auctionator 蒐集行情並管理採買；專業模組計算衝等步驟與缺口」。Baganator／Syndicator、BagSync 的庫存查詢不能直接當成拍賣行情來源；分解估價也需另查材料價格與產出假設。

## DungeonsForever 與 Auctionator 專業衝等操作

以下依 **DungeonsForever 2.1.87＋Auctionator 345** 的載入清單及 `DungeonsForeverProf/Core/ProfessionUI.lua`、`ProfRouteAuto.lua`、`ProfFollow.lua`、`AuctionatorBridge.lua` 查證。這是檔案層流程，尚未進遊戲驗證。

1. **確認模組。** CurseForge 選 Forever／本機 `_forever_`，在插件列表確認 `DungeonsForever`、`DungeonsForeverProf`、`Auctionator` 已啟用；若剛改啟用狀態，重載介面。主體能開地城頁不代表專業模組也已啟用。
2. **取得完整行情。** 需要新掃描時，在「設定選項 → 插件 → Auctionator → 進階」檢查並啟用較慢的備用／複製掃描模式，再到拍賣場按完整掃描，等待完成。DungeonsForever 的提示用語為「預設使用較慢的備用掃描模式」；這版專業功能需要可驗證的完整掃描快照，摘要掃描不能替代。已有有效快照可沿用；不使用專業功能時，插件建議切回摘要模式。
3. **計算目標路線。** `/df` 開專業手冊，依目標專業選擇衝等頁，例如鍛造，核對讀到的目前技能與已學配方，設定目標技能；為傳承規劃時依需求設為 150／225／300。選「自動計算」與「最省錢」比較當次可行成本；缺資料或該專業只支援固定路線時，依提示查閱固定攻略，待補齊行情、配方與學習條件後重算。
4. **核對並匯入缺口。** 開背包與銀行，確認已有材料、需向 NPC 購買、自製中間材料及拍賣採購缺口；先確認圖紙與學習費是否有資料，再按「一鍵匯入」。`AuctionatorBridge` 使用 `Auctionator.API.v1.CreateShoppingList`，清單依專業命名；只匯入拍賣採購缺口，NPC 貨物與自製材料不匯入，**同名清單會被覆寫**。回 Auctionator 選該清單，逐項核對價格與實際數量再買；空清單先確認是否確實無缺口。
5. **依實際進度調整。** 開專業製作介面，按路線與步驟追蹤製作；學配方、升階、技能點與材料變化後重新核對，行情有變則重新掃描並計算。黃色／綠色配方不保證每次升點，預估回收與淨成本也不保證成交；「最省錢」是依可用資料的方案估算，不能保證零浪費或全市場最低價。

### 常見狀況

| 狀況 | 處理方式 |
| --- | --- |
| 有地城頁，沒有專業頁 | 核對 Forever 分支及 `DungeonsForeverProf` 的安裝、啟用與主體依賴；按需載入模組不必從登入起就顯示為已載入。 |
| 顯示 Auctionator 未安裝／未啟用／初始化中 | 分別確認套件、啟用狀態及等待載入，必要時重載；地城手冊本身可用不代表行情整合可用。 |
| 無價格、僅做過摘要掃描、完整掃描失敗 | 依上方模式重新完成完整掃描後計算；缺價不能當 0 銅。失敗時可能仍顯示上次快照，核對畫面的狀態與時間。 |
| 快照過期、屬於其他角色／市場或資料無效 | 用目前角色在目標市場重新完整掃描；此版提示超過 2 天即過期，重載或切換模式不會延長有效期。 |
| 材料或圖紙在售量不足、配方尚未學會 | 核對現貨、NPC／其他已確認來源與角色學習條件，更新資料或更換路線；掃描紀錄不能保證現在買得到。 |
| 匯入失敗或只出現可複製字串 | 確認 Auctionator 的購物清單 API 可用；若有匯出字串，可在 Auctionator 的購物清單匯入處貼上。先確認目前專業與同名清單覆寫範圍。 |

## 選用時的功能分工

| 想補足的能力 | 優先比較 |
| --- | --- |
| 升級時看屬性與忘記學的技能 | GnomeLevelUp；與目前整合 UI 的技能提醒比較。 |
| 決定下一個任務與練等順序 | RestedXP／Polestar；先核對 Forever 指南、陣營與免費範圍。 |
| 決定如何到目的地 | Shortest Path Forever＋正確的 ForeverCore；附近服務查詢另核對 QuestieDB。 |
| 更醒目的畫面內目標 | Waypoint UI；先試目前導航來源已有的箭頭。 |
| 分類背包及查其他角色庫存 | Baganator＋Syndicator；和整合背包、BagSync／Account Overview 逐項比較。 |
| 姓名板、任務怪與仇恨顏色 | Platynator／Plater／Threat Plates／整合 UI 選主要來源。 |
| 讀任務劇情 | Immersion；同步檢查自動接交設定。 |
| 便利功能、地圖資訊、地城行前查詢 | 分別評估 Leatrix Plus、Leatrix Maps、DungeonJournal／DungeonsForever，按模組關閉重複功能。 |
| 專業衝等步驟、材料缺口與成本 | DungeonsForever＋專業模組＋Auctionator；先取得完整行情，再核對目標技能、配方與庫存。 |
| 拍賣行情與材料採買 | Auctionator；背包／跨角色庫存插件另負責已有物資。 |
