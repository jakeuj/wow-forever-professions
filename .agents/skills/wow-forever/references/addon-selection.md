# 永恆插件挑選

## 來源與使用方式

2026-11-08 整理以下兩篇巴哈主文；只整理目標主文，沒有混入回覆樓層與留言：

| 來源 | 目標與範圍 |
| --- | --- |
| [【閒聊】永恆插件整理 11/4](https://forum.gamer.com.tw/C.php?bsn=5219&snA=681058) | `article#cf5505749`；43 個候選。 |
| [【密技】永恆開服前推薦幾個必備插件分享給拓荒的你（更新中）](https://forum.gamer.com.tw/C.php?bsn=5219&snA=681023) | 目標 `section#post_5505533`，正文為 `article#cf5505533`；作者 niagura，顯示編輯時間 2026-10-28 17:33:28；15 個工具／服務，其中 4 個與前表相同。 |

下方候選表依專案去重後共 54 個：53 個 CurseForge 專案與一個 GitHub 分支。GearInsight 網站是同工具的補充入口，沒有另外計數；額外光環套件網站也不作獨立插件計數。

另有插件功能調查；作者來源、Forever 發佈、相依插件、指令與繁中證據集中於 [插件功能指南](addon-feature-guide.md)。功能指南獨立於下方兩篇主文的 54 個候選統計。

社群文提供發現插件的入口；相容性、Beta 狀態、依賴與翻譯仍以當下作者發佈為準。網站取用工具若讀不到巴哈，可透過一般 HTTP 取得公開頁面，再只解析該 article；不要因此推測全文內容。主文含 Questie 追蹤字型調整、Polestar 任務對話選項的截圖線索，需要確切設定位置時回查目前版本。

評估台灣繁中需求時，先用技能的唯讀盤點工具讀目前插件，再按本次需求補缺少的能力；以「保留／新增／替換／關閉重複模組」表達建議。把「作者列出支援 Forever」「有獨立 zhTW 翻譯」「已在遊戲內測試」分開說明。

## 功能取捨

| 需求 | 選擇原則 |
| --- | --- |
| 整套介面 | AnoUI+、NDui Classic、EllesmereUI 預設擇一作為主要 UI；先確認 Forever 檔案與繁中語系。其他專用插件能否共存，依模組控制範圍判斷。 |
| 動作列、提示框、小地圖 | 整合 UI 已接管該功能時，再評估 Bartender4、PrettyTooltip、SexyMap 或按鈕收納是否仍有必要；距離染色由同一來源負責。 |
| 熱鍵與配置搬移 | Myslot 處理動作列內容、巨集與按鍵配置，與單純動作列造型不同；若整合 UI 已含 Action Profiles，先比較匯出範圍。套用前保留現有配置並確認匯入項目。 |
| 姓名板 | Plater、Threat Plates、Platynator 或整合 UI 的姓名板選一個主要來源；整合 UI 能關閉對應模組時，可改由專用插件接管。 |
| 任務 | 區分 Questie 的任務位置資料、追蹤清單、Polestar／RestedXP 的任務路線，以及 Immersion 的任務對話。調整字型不需要因此更換任務資料插件；重複追蹤清單與自動接交由一套負責。 |
| 交通與導航 | Shortest Path Forever 規劃跨區交通，Waypoint UI 顯示世界空間標記；前者已有箭頭與地圖路線，後者按視覺需求選用。Leatrix Maps 側重地圖資訊與視窗；地圖迷霧顯示和實際探索進度分開判斷。相依插件與整合條件見功能指南。 |
| 裝備與地城 | 分開看 BiS 推薦、物品權重評分、掉落資料、地城任務前置、首領戰鬥警告。地城指南與 DBM 計時屬於不同能力。 |
| 團隊與治療 | 整合 UI 團隊框架、VuhDo 與 Decursive 依顯示、點擊施法、驅散需求取捨，先查看目前職業與操作習慣。 |
| 背包與交易 | 背包外觀、跨角色庫存、拍賣行情、商店售價與批次收信分別判斷。Baganator＋Syndicator 同時涉及背包與庫存查詢，先比較 BagSync／Account Overview 的實際用途；售價顯示候選先比較已有提示框功能。 |
| 分身與物品用途 | Account Overview 與 BagSync 的庫存查詢有交集，但前者還涵蓋其他角色資料；ItemTree 的用途關聯也不等同 BiS 或背包外觀。 |
| 採集與釣魚 | 節點資訊、導航、閃光提示與釣魚操作分開選。多套閃光／互動鍵模組同時控制設定時，確認由哪套負責。 |
| 光環與警告 | 整合 UI 內建冷卻／提醒與 ForeverAuras 套件有部分重疊。先核對實際需要的光環，再加入套件及其依賴。 |

## 開服推薦文的版本與操作線索

以下來自第二篇主文，保留能影響選擇的差異，不把 Beta 時期經驗視為目前版本測試：

- EllesmereUI 是整合 UI 候選；作者貼出的公會配置未公開提供。可使用公開插件與自行設定，不要把加入公會／Discord 當作安裝前置，也不能聲稱已取得該配置。2026-11-08 的 [作者專案](https://www.curseforge.com/wow/addons/ellesmereui) 同時列出 Retail、Forever，下載時核對所選檔案支援分支；繁中翻譯尚未由本次查證確認。
- Myslot 的 `/myslot` 可開啟匯出／匯入。依 [作者說明](https://www.curseforge.com/wow/addons/myslot)，其動作列、巨集、熱鍵搬移與整合 UI 的外觀配置不同；部分額外功能僅限 Retail，不能整套套用到 Forever。
- 原文 SpellActivationOverlay 連到 [ennvina 分支 v2.8.4](https://github.com/ennvina/spellactivationoverlay/releases/tag/v2.8.4)。該發佈標為 Forever Update 4，含職業觸發提示修正；這是指定的歷史版本，後續先查 [該分支發佈列表](https://github.com/ennvina/spellactivationoverlay/releases)，不能當作永遠最新的版本，也不能自動換成名稱相同的其他分支。
- GearInsight 補充入口：[官方網站](https://gearinsight.app/wow/en/forever)。它與既有 GearInsight 候選相同，網址語言或路徑不代表遊戲內有完整台灣繁中。
- Leatrix Maps 原文指定 [下載 9040723](https://www.curseforge.com/wow/addons/leatrix-maps/download/9040723)。推薦時回專案選目前支援的 Forever 發佈；地圖迷霧顯示與實際探索／成就進度分別判斷。
- 原文描述 ItemTree 的 Ctrl＋右鍵完整清單當時沒有中文。這是有日期的社群觀察；本次 [作者頁](https://www.curseforge.com/wow/addons/itemtree) 可確認 Forever `1.60.1` 與物品關聯用途，但沒有證實當前完整 `zhTW` 翻譯。後續要看實際語系檔、資料語言與字型。
- Layer 候選需與目前 GearInsight 的 Layer／LayerGuild／LayerHop 模組比較。分層偵測不代表能無條件切換鏡像，依當前遊戲與插件能力說明。
- Account Overview 與 BagSync 都涉及跨角色資料；先區分要查庫存，還是裝備、配方、貨幣等資料，再選工具。
- BlitzFramesTargets 的原文網址落在 `/comments`，候選表使用專案首頁。戰場相容性與效能應另查作者發佈，不能直接採用原文「可用」或低記憶體的評語。
- Target Arrow 的目標高亮，需與整合 UI／姓名板已有的目標箭頭比較；Siz DisenchantValue 的分解估價與 Auctionator 的行情用途分別確認，價格來源與台服資料有關。

## 常見插件組合的比較基線

下表整理 2026-11-08 比對過的插件組合與用途，不代表任何玩家的目前安裝。實際版本、啟用狀態與設定值，先盤點 `_forever_/Interface/AddOns` 再判斷。

| 插件群組 | 與 AnoUI+ 的關係 |
| --- | --- |
| AtlasLootClassic 各子模組、AtlasBIStooltips | 掉落與 BiS 資料仍有用途。AnoUI 的提示框造型不是這些資料的完整替代；版本／專案 ID 詳見 [AtlasLoot 線索](environment-and-atlasloot.md)。 |
| GearInsight_Forever、Group、Guild | 與 AnoUI 的攻略／介面分工、重複功能取捨及套件子模組差異，讀 [GearInsight 比對](gearinsight-overlap.md)。 |
| Questie、QuestieDB、QuestieTrace | 任務追蹤外觀和地圖顯示部分重疊；保留任務資料用途，追蹤清單選一個主要來源。DB／Trace 是同組資料與輔助模組，不能當作三套獨立任務 UI。 |
| LFGForever、LFGForeverLanguageChineseTraditional | 副本組隊與繁中語言包；不能只因 GearInsight 有 Group 子模組就判定整套重複，差異見同一份 GearInsight 比對。 |
| tullaRange、tullaRange_Config | 與 AnoUI Actionbars 的 Custom Range Warning 重疊；先測試由哪套負責距離染色。設定模組已有 `localization/zhTW.lua`。 |
| ForeverLootSparkles | 地上可互動物件與採集閃光，不等同戰利品視窗或拾取通知美化。 |

NodeSight 的 `Locales/zhTW.lua` 提供繁中線索；查證過的 `NodeSight/Sparkles.lua` 與 `ForeverLootSparkles/SoftTarget.lua` 都會在啟用相關功能時操作 soft-interact 設定與物件提示，草藥／礦脈閃光有功能重疊。實際同時安裝時，依目前設定選一套負責閃光；功能重疊本身不能證明已發生衝突。

## AnoUI+：繁中與功能的查證紀錄

查證日 2026-11-08；專案 ID `1748636`。

- [CurseForge 專案](https://www.curseforge.com/wow/addons/anoui) 列出 Forever `1.60.1`。
- [作者指南](https://anoui.dev/guide) 的語言清單含簡體中文，沒有獨立繁體中文；可在設定頂部旗幟按鈕切換插件語言，該選擇不改遊戲客戶端語言。
- 從 [作者官網](https://anoui.dev/) 的 [下載包](https://anoui.dev/download) 讀得 `AnoUI/AnoUI.toc`、`AnoUI_Options/AnoUI_Options.toc`：`Interface: 16001`、`Version: vR0.11`。下載只作 ZIP 內容檢查，未安裝或執行插件。
- 該版 `AnoUI/Core/Locale.lua` 的 `ClientLanguage()` 將 `zhTW` 對應成 `zhCN`。因此台服預設會使用簡中插件標籤，不能依指南的通用 English fallback 描述誤判成台服預設英文。
- 主要語言清單沒有 `zhTW`，但部分特定資料有繁中，例如 `WeakAuras_API/MageBooksData.lua`。這不代表整套設定介面已有繁中翻譯。
- 包內有 CJK 字型與字型處理；尚未在台服遊戲內驗證所有中文字元、版面或第三方插件相容性。
- [功能清單](https://anoui.dev/features) 涵蓋介面框架、姓名板、動作列、背包、提示框、地圖、計量、天賦與日常工具，且模組可個別開關。[動作列指南](https://anoui.dev/guide?chapter=ActionBars) 的 Custom Range Warning 可對圖示或快捷鍵染色。
- [CurseForge 說明](https://www.curseforge.com/wow/addons/anoui) 指出：只有要匯入／使用附帶職業光環套件時，才需要另外安裝 ForeverAuras；它不是單純安裝 AnoUI 的無條件前置。

評估結論為：可考慮作為全面改造介面的候選，但目前不符合「整套繁中選單」需求；現有專用插件多數仍有用途。這是該版原始碼與作者宣告的判斷，後續版本需重新核對。

## 社群候選：升級與裝備

| 插件 | 評估用途 |
| --- | --- |
| [GearInsight Forever](https://www.curseforge.com/wow/addons/gearinsight-forever) | 綜合角色規劃；原文提醒簡中介面。 |
| [Forever Leveling BiS](https://www.curseforge.com/wow/addons/forever-leveling-bis) | 練等階段裝備候選。 |
| [GearQuest Forever](https://www.curseforge.com/wow/addons/gearquest-forever) | 裝備提升來源。 |
| [Pawn](https://www.curseforge.com/wow/addons/pawn) | 依權重比較裝備；權重須符合永恆職業版本。 |
| [AtlasLoot Classic Forever](https://www.curseforge.com/wow/addons/atlasloot-forever) | 掉落與 BiS 資料；專案區別見既有 AtlasLoot 參考。 |

## 社群候選：介面與戰鬥

| 插件 | 評估用途 |
| --- | --- |
| [AnoUI+](https://www.curseforge.com/wow/addons/anoui) | 整合 UI；繁中限制見上方查證。 |
| [NDui Classic](https://www.curseforge.com/wow/addons/ndui-classic) | 整合 UI；在此專案選 Forever 發佈。 |
| [EllesmereUI](https://www.curseforge.com/wow/addons/ellesmereui) | 整合 UI 的另一候選。 |
| [Myslot](https://www.curseforge.com/wow/addons/myslot) | 動作列內容、巨集與熱鍵搬移。 |
| [Bartender4](https://www.curseforge.com/wow/addons/bartender4) | 動作列配置。 |
| [tullaRange](https://www.curseforge.com/wow/addons/tullarange) | 技能距離染色。 |
| [PrettyTooltip](https://www.curseforge.com/wow/addons/prettytooltip) | 提示框外觀。 |
| [Focus Interrupt Sounds](https://www.curseforge.com/wow/addons/focusinterruptsounds) | 施法／打斷聲音提示。 |
| [Spy (Forever)](https://www.curseforge.com/wow/addons/spy-forever) | 野外敵對玩家資訊。 |
| [HeadHunter - Wanted: Dead or Alive](https://www.curseforge.com/wow/addons/headhunter-wanted-dead-or-alive) | PvP 追蹤。 |
| [Forever Enhanced Cursor](https://www.curseforge.com/wow/addons/forever-enhanced-cursor) | 游標視覺與施法提示。 |
| [ForeverAuras](https://www.curseforge.com/wow/addons/foreverauras) | 自訂光環；[套件入口](https://wago.io/browse/foreverauras)。 |
| [SpellActivationOverlay（ennvina Forever 分支）](https://github.com/ennvina/spellactivationoverlay) | 技能觸發提示；原文特定發佈版本見上方線索。 |
| [Plater Nameplates](https://www.curseforge.com/wow/addons/plater-nameplates) | 姓名板配置。 |
| [Threat Plates](https://www.curseforge.com/wow/addons/tidy-plates-threat-plates) | 仇恨導向姓名板。 |
| [GTFO](https://www.curseforge.com/wow/addons/gtfo) | 危險傷害音效。 |
| [RangeDisplay](https://www.curseforge.com/wow/addons/range-display) | 單位距離估算。 |
| [MinimapButtonButton](https://www.curseforge.com/wow/addons/minimapbuttonbutton) | 小地圖按鈕整理。 |
| [SexyMap](https://www.curseforge.com/wow/addons/sexymap) | 小地圖造型。 |
| [BlitzFramesTargets](https://www.curseforge.com/wow/addons/blitzframestargets) | 戰場目標框架。 |
| [Target Arrow Forever](https://www.curseforge.com/wow/addons/target-arrow-forever) | 選取目標的視覺標記。 |

## 社群候選：團隊與副本

| 插件 | 評估用途 |
| --- | --- |
| [VuhDo](https://www.curseforge.com/wow/addons/vuhdo) | 團隊框架與點擊施法。 |
| [Decursive](https://www.curseforge.com/wow/addons/decursive) | 驅散介面。 |
| [DBM](https://www.curseforge.com/wow/addons/deadly-boss-mods) | 首領警告核心。 |
| [DBM Dungeons, Delves, Challenges, & Events](https://www.curseforge.com/wow/addons/deadly-boss-mods-dbm-dungeons) | DBM 內容模組；先確認所選檔案是否涵蓋 Forever 地城及其核心依賴。 |
| [ForeverDungeons](https://www.curseforge.com/wow/addons/foreverdungeons) | 地城資訊與準備。 |
| [DungeonJournal](https://www.curseforge.com/wow/addons/dungeonjournal) | 地城資料查詢。 |

## 社群候選：背包與交易

| 插件 | 評估用途 |
| --- | --- |
| [BagSync](https://www.curseforge.com/wow/addons/bagsync) | 跨角色物資查詢。 |
| [Account Overview](https://www.curseforge.com/wow/addons/account-overview) | 跨角色資料管理。 |
| [ItemTree](https://www.curseforge.com/wow/addons/itemtree) | 物品用途關聯；繁中狀態需查證。 |
| [Auctionator](https://www.curseforge.com/wow/addons/auctionator) | 拍賣交易輔助。 |
| [Siz DisenchantValue](https://www.curseforge.com/wow/addons/siz-disenchantvalue) | 分解材料價值預估。 |
| [Better Vendor Price](https://www.curseforge.com/wow/addons/better-vendor-price) | 售價提示。 |
| [Vendor Price Plus](https://www.curseforge.com/wow/addons/vendor-price-plus) | 售價提示的另一候選。 |
| [Posty Forever](https://www.curseforge.com/wow/addons/posty-forever) | 郵件操作。 |

## 社群候選：任務與綜合指南

| 插件 | 評估用途 |
| --- | --- |
| [Polestar Guides](https://www.curseforge.com/wow/addons/polestar-guides) | 任務路線指南；確認是否要啟用自動接交任務。 |
| [Waylaid Auction Helper](https://www.curseforge.com/wow/addons/waylaid-auction-helper) | 箱子相關交易成本。 |
| [Questie](https://www.curseforge.com/wow/addons/questie) | 任務資料與標示。 |
| [OneForAll - Forever](https://www.curseforge.com/wow/addons/oneforall-forever) | 多用途指南；先與 GearInsight／地城指南比對。 |
| [Layer](https://www.curseforge.com/wow/addons/layer) | 分層資訊工具；先比對現有 Layer 模組。 |

## 社群候選：採集與釣魚

| 插件 | 評估用途 |
| --- | --- |
| [FishMaster](https://www.curseforge.com/wow/addons/fishmaster) | 釣魚管理。 |
| [Better Fishing](https://www.curseforge.com/wow/addons/better-fishing) | 釣魚操作便利。 |
| [Node Sight](https://www.curseforge.com/wow/addons/node-sight) | 節點辨識與提示。 |
| [Forever Loot Sparkles](https://www.curseforge.com/wow/addons/forever-loot-sparkles) | 地上物件閃光提示；與 NodeSight 的重疊見比較基線。 |

## 社群候選：地圖標記

| 插件 | 評估用途 |
| --- | --- |
| [HandyNotes](https://www.curseforge.com/wow/addons/handynotes) | 標記核心，搭配所需內容模組。 |
| [HandyNotes: WoW Forever](https://www.curseforge.com/wow/addons/handynotes-wow-forever) | 稀有／寶藏。 |
| [HandyNotes - Forever Books](https://www.curseforge.com/wow/addons/handynotes-forever-books) | 書籍物件。 |
| [HandyNotes: DungeonLocations (Classic)](https://www.curseforge.com/wow/addons/handynotes_dungeonlocations-classic) | 副本入口。 |
| [Leatrix Maps](https://www.curseforge.com/wow/addons/leatrix-maps) | 地圖資訊與外觀。 |

需要內容模組時依其當前 `.toc`／發佈說明加入核心；HandyNotes 家族尤其要區分核心與資料模組。上列清單不是所有永恆插件的完整目錄，依使用者實際需求與當前來源繼續評估。
