# GearInsight 的功能重疊與分工

## 查證範圍

2026-11-08（Asia/Taipei）以 GearInsight `0.7.5` 的套件內容比對 [作者官網](https://gearinsight.app/wow/forever) 與相關插件。保留套件結構與功能差異，不記錄玩家的安裝清單；未在遊戲內測試所有功能、啟用狀態或效能。

查證版本的 `GearInsight_Forever`、`GearInsight_Forever_Group`、`GearInsight_Forever_Guild` `.toc` 均為 `0.7.5`。目前安裝狀態先用 [唯讀盤點工具](../scripts/inspect_install.py) 確認；以下取捨是該版本快照，不是固定推薦。

## 逐項判斷

| 比較插件 | 與 GearInsight 的交集 | 保留價值與判斷 |
| --- | --- | --- |
| AtlasLootClassic 各子模組 | 裝備、地城掉落、取得來源等查詢有較多重疊。 | GearInsight 提供依等級／專精的升級裝備規劃；AtlasLoot 集中整理掉落表與階段資料。若只使用 GearInsight 查掉落，可考慮擇一；若使用其天賦、專業或任務指南，仍有獨立用途。 |
| AtlasBIStooltips | 都提供裝備推薦資訊，但呈現位置與判定不同。 | Atlas 的物品提示框按職業／階段標示 BiS；GearInsight 的角色裝備格角標按目前等級與天賦權重推薦可換裝備。不能直接當作同一套 BiS 規則，也不能把推薦不同視為程式衝突。 |
| Questie 及其資料／輔助模組 | 副本前置、任務資訊與地圖定位有部分重疊。 | Questie 廣泛標記接取、交付與任務目標；GearInsight 的路線、專業規劃與指定任務前置屬指南。保留 Questie 作任務導航，避免把指南當成完整任務位置資料的替代品。 |
| LFGForever＋繁中語言包 | 找人、邀請等操作有少量交集。 | 此版本的 GearInsight Group 主要是附近共同任務與進度分享；LFG Forever 是副本組隊列表、職責／職業篩選與密語管理。這份 GearInsight 安裝包不能直接取代 LFG Forever，詳見下節。 |
| tullaRange＋設定模組 | 未發現直接替代技能按鈕超距離染色的對應功能。 | GearInsight 的鍵位規劃、手法與 HUD 不等同距離染色；不能因都接觸技能按鈕就判定重複。 |
| ForeverLootSparkles | 未發現直接替代地上物件閃光的對應功能。 | GearInsight 的採集資料、觀測與專業指南不等同草藥、礦脈、任務物件的視覺閃光。 |

## 與 AnoUI+ 的功能重疊與分工

2026-11-08 將 GearInsight `0.7.5` 與 [AnoUI 作者功能清單](https://anoui.dev/features)、[CurseForge 說明](https://www.curseforge.com/wow/addons/anoui) 及 [操作指南](https://anoui.dev/guide) 比較。以下是功能範圍的比較與取捨建議，沒有完成兩者同時載入的相容性或效能測試。

| 功能 | GearInsight | AnoUI+ | 重疊與差異 |
| --- | --- | --- | --- |
| 天賦 | 職業建議、升級加點與天賦規劃。 | 天賦規劃、方案儲存與分享。 | 規劃功能有較多交集；方案管理不能直接替代攻略建議。 |
| 巨集與快捷鍵 | 提供職業巨集範本與鍵位規劃。 | 管理、編輯巨集，以及動作列和快捷鍵配置。 | 有部分交集；範本內容與編輯工具分別評估。兩者同用時，明確選擇由哪套套用巨集／鍵位配置。 |
| 副本任務 | 依等級與陣營整理前置、接取位置及路線。 | Dungeon Helper 提供副本地圖與任務鏈準備。 | 有部分交集；按實際任務覆蓋範圍與操作習慣選主要入口。 |
| 技能與冷卻提示 | 有鍵位、手法與 HUD 相關程式。 | 有冷卻管理、資源條、提醒與施法顯示。 | 只有當該版 GearInsight 實際提供並啟用相關顯示時才構成重疊；檔案存在不等於功能已開啟。 |
| 裝備、BiS、專業與升級指南 | 屬於主要資料與攻略用途。 | 作者列出的介面功能無法完整替代這些資料。 | 交集較少；角色面板與提示框的造型不等於配裝推薦資料。 |
| 血條、姓名板、團隊框架、背包與聊天外觀 | 並非主要用途。 | 屬於主要介面用途。 | 交集較少，可由 AnoUI 負責整體介面。 |

兩者一起使用時，建議按以下需求分工，而不是預設整包互相替代：

- GearInsight 作角色攻略與資料入口：依使用者目前角色的陣營、職業及實際專精查天賦、裝備、專業路線與任務前置。
- AnoUI 作介面入口：整體外觀、動作列、姓名板、團隊框架及需要的視覺提醒。
- 天賦規劃、巨集管理、副本助手各選一個常用入口；實際出現重複顯示或重複操作時，按 [作者指南](https://anoui.dev/guide) 關閉相應 AnoUI 模組，或調整 GearInsight 的對應功能。保留另一套獨有的資料用途。

若只想補攻略功能，既有 GearInsight 通常沒有因這些交集而加裝 AnoUI 的必要；需要全面改造介面時，再評估 AnoUI。需要保證共存或排除衝突時，仍要在目標角色上測試。

兩者當時都沒有獨立的完整台灣繁中介面：GearInsight 的簡繁共用處理見下節；AnoUI 的 `zhTW` → `zhCN` 原始碼紀錄與字型查證集中在 [插件挑選參考](addon-selection.md) 的 AnoUI 語系章節，後續核對新版本時更新該處，避免重複保存語系實作細節。

## Group 與 Guild 的打包差異

查證依據為 `Interface/AddOns` 下的實際 `.toc`、Lua 檔案與條件分支：

- `GearInsight_Forever_Group.toc` 宣告 `LoadOnDemand: 1`、依賴主插件，只載入 `QuestMates.lua`。其主要用途是附近共同任務玩家、進度與邀請；詳細任務進度分享需要對方也有對應插件。
- 官網歷史更新曾提到副本組隊，但這份安裝包沒有 `PageGroup.lua`，也沒有 `ns.BuildGroupPanel` 的定義。`QuestMates.lua` 與主插件 `UI.lua` 只有在該函式存在時才提供「副本組隊 · 測試」入口。因此該版本正式包的 Group 不等同官網歷史紀錄中的全套副本組隊能力。
- [LFG Forever 作者頁](https://www.curseforge.com/wow/addons/lfg-forever) 說明其擴充遊戲原生組隊列表、篩選和密語；`LFGForeverLanguageChineseTraditional` 是依賴 LFGForever 的繁中語言包，並非第二套組隊插件。
- `GearInsight_Forever_Guild.toc` 也宣告按需載入，載入公會招募與本公會資訊頁；是否重複須比較當前其他工具的公會功能。Group、Guild 是主插件子模組，不應當作三套互相重複的整合 UI。
- 主插件自己也載入 `GuildChatLevel.lua`、`LevelShare.lua` 等功能。停用 Guild 子插件不代表主插件的公會等級標示或升級播報一併停止，相關設定須回主插件確認。

若未使用附近共同任務或公會招募，可依需求停用相應子模組；保留主插件仍可使用其其他功能。不要因為已裝 LFG Forever 就直接宣告 GearInsight Group 全無用途。

## 繁中處理

該版本 `GearInsight_Forever/Core.lua` 先以 `GetLocale()` 判斷：`zhCN`、`zhTW` 都將 `ns.zh` 設為 true；`ns.L(cn, en)` 對這兩種客戶端都返回同一份 `cn` 字串。該版選單與資料含大量簡體中文，並沒有獨立的完整台灣繁中介面。

因此「可以辨識台服客戶端」與「完整繁中翻譯」是兩件事。使用者偏好繁中時，可優先以 Questie 處理日常任務、LFG Forever 繁中包處理副本組隊，再依是否需要天賦、專業路線、任務前置與裝備規劃決定保留 GearInsight。

## 後續讀取重點

需要重新比較或執行精簡時，只讀相應檔案，不必載入整套大型資料表：

- 模組範圍：三個 GearInsight `.toc`、`UI.lua`、Group 的 `QuestMates.lua`。
- 語系：`Core.lua` 中的 `ns.zh`、`ns.L`；有需要再看實際字串。
- 升級裝備與角色角標：`SpecGear.lua`、`PagePlan.lua`、`BisCorner.lua`。
- 提示框：GearInsight 的 `Tooltip.lua`、AtlasBIStooltips 的渲染與階段設定；前者還含技能變更說明與英文效果的簡中翻譯，不能全部視為 BiS 提示。

搜尋時用檔案範圍或 `rg --max-columns 240 --max-columns-preview` 限制長行輸出；GearInsight 的資料檔可能把大量資料放在單行，整目錄搜尋常造成巨量輸出。
