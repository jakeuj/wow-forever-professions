# 公開專業規劃網站維護

這是面向一般玩家的公開專業規劃網站。遊戲規則、專業選擇理由和點數計算見 [professions-and-legacy.md](professions-and-legacy.md)；本檔集中網站的定位、位置與維護約束。

## 專案位置與發布

- 名稱：永恆・專業議事廳／魔獸世界：永恆專業與傳承分配規劃。
- 專案根目錄：此技能所在 repo 的根目錄；從 `.agents/skills/wow-forever` 向上三層定位，避免固定本機 checkout 路徑。
- 公開 repo：[jakeuj/wow-forever-professions](https://github.com/jakeuj/wow-forever-professions)。
- 正式站：[https://blog.jakeuj.com/wow-forever-professions/](https://blog.jakeuj.com/wow-forever-professions/)。
- GitHub Pages 使用 `main` 根目錄與 `.nojekyll`，沿用帳號既有的 `blog.jakeuj.com` 網域；HTTPS 已啟用。後續發布先讀當前 Pages 設定，保留其來源與網域。

這是 GitHub repo／Pages 專案，在目前 repo checkout 修改。網站建置技能可協助設計與 QA，發布仍沿用 GitHub Pages。

## 公開受眾與預設

面向一般玩家，依序顯示：

| 順序／標籤 | 穩定方案 ID | 定位 |
| --- | --- | --- |
| 01／PLAN A，首選 | `crafting` | 雙採集主號＋三隻雙製造小號，六製造集中在三位工匠 |
| 02／PLAN B | `gathering` | 雙採集起手，之後主號剝皮換煉金 |
| 03／PLAN C | `balanced` | 直接配對採集與製造，建立全專業分工 |
| 04／PLAN D | `paladin` | 聖騎士多路線：保留現況、主角雙製造、主角雙採集 |

- 無方案參數時預設 `crafting`。德魯伊主號採草／剝皮、法師裁縫／附魔、獵人製皮／煉金、戰士鍛造／工程，另由盜賊採礦並保留第二格彈性。完整規劃是五職業、九專業、三位製造工匠、18 點上限；可先從主號與法師開始，逐步補齊。
- 新 01 不使用開局／長期階段切換；主號長期維持雙採集。盜賊以真實的 `mining` 專業計數；「彈性一格」是說明，不作額外專業 ID 或點數來源。
- `gathering` 保留在 02，`stage=start` 為雙採集，`stage=final` 為主號保留採草、剝皮換煉金。原本分享連結繼續指向這個分階段方案。
- 首頁、說明、材料流向、圖示和分享預覽以一般玩家的集中雙製造分工為主。聖騎士作 04 的條件式延伸；實際玩家角色現況依當次提供資料判斷。
- 「我的製造里程碑」是每位訪客自行輸入的本機進度，與方案可得上限分開；不讀取遊戲資料。

方案編號可以調整，分享連結的 ID 維持相容：

- [雙製造小號首選](https://blog.jakeuj.com/wow-forever-professions/#plan=crafting)
- [雙採集開局](https://blog.jakeuj.com/wow-forever-professions/#plan=gathering&stage=start)
- [雙採集轉製造的長期配置](https://blog.jakeuj.com/wow-forever-professions/#plan=gathering&stage=final)
- [直接全專業分工](https://blog.jakeuj.com/wow-forever-professions/#plan=balanced)
- [聖騎士路線比較](https://blog.jakeuj.com/wow-forever-professions/#plan=paladin)：舊入口預設 A 保留採礦／鍛造，也可用 `route=keep`。
- [聖騎士 B 主角雙製造](https://blog.jakeuj.com/wow-forever-professions/#plan=paladin&route=crafting)
- [聖騎士 C 主角雙採集](https://blog.jakeuj.com/wow-forever-professions/#plan=paladin&route=gathering)

04 內部的路線 A／B／C 與外層 PLAN A／B／C 是不同層級。三條路線都提供五職業、九專業、18 點上限；製造角色數依序為 4／3／3，B 的三位包含聖騎士主角。每條路線列出主角調整、材料流向與適合情境，完整分工見 [professions-and-legacy.md](professions-and-legacy.md#04plan-d聖騎士多路線)。切換路線會同步更新分配表、覆蓋摘要、複製文字及分享網址；裸 `#plan=paladin` 或無效路線回 A。

## 修改與驗證重點

現行配置讀 repo 的 `data.mjs`，操作和驗證指令讀 `README.md`。修改預設或方案順序時，同時對齊 `index.html` 的初始可讀內容、標籤順序／選取狀態、`app.js` 的初始方案／階段，以及資料中的 PLAN 標籤。如此 JavaScript 載入前、無 JavaScript 時和互動畫面會呈現同一個預設。

保留深色、金色、暗紅視覺與台灣繁中用語。沿用專案路徑下的相對資源；canonical、`og:url` 與分享圖使用正式站的絕對 HTTPS URL。更換分享圖時使用新檔名並同步 metadata；若更新樣式或模組的快取版本，同步 HTML 與模組 import。

按變更驗證對應情境：

- 新訪客首頁預設 01 雙製造小號，顯示 9／9 專業、3 位製造工匠、18 點上限；三位工匠各自雙製造、六項各一次，主號保留草藥學／剝皮。
- 02 開局的完整規劃顯示 8／9 專業、4 位製造工匠、15 點上限；長期為 9／9、5 位製造工匠、18 點。既有 `#plan=gathering&stage=final` 仍直接開啟此方案的長期階段。
- 四個方案的切換與鍵盤左右鍵順序跟畫面一致，聖騎士維持最後；手機版兩列選項且無橫向溢出。
- 04 的三個路線選項在手機改為單欄；分別開啟或重新整理分享網址能還原選取，其他方案隱藏此選單。
- 涉及傳承記錄時，確認重新整理後保留進度，且計分按六項專業里程碑各算一次。
- 發布完成以對應 commit 的 Pages 工作成功及正式頁、受影響資源可讀為準；來源推送成功是中間狀態。

## 外部資料整合

加入物品提示框、材料行情、配方清單或公會工匠名冊時，先讀 [public-data-sources.md](public-data-sources.md) 的增強方向與靜態網站整合模式。需要 API 憑證的資料由排程預先產生；發布方式若從 `main` 根目錄改為 Actions 部署，同步更新本檔與 README。

## 公會招生區

2026-11-11 已發布《黎明之劍》招生整合，[公開入口為 `#guild`](https://blog.jakeuj.com/wow-forever-professions/#guild)。公會公開資訊與招募文來源統一查 [dawnblade-guild.md](dawnblade-guild.md)。

- 網站繼續以專業規劃為主；首頁只有一句邀請，完整招生區置於分配表之後、分配原則之前。手機主要導覽為「專業／傳承／公會」，資料依據與原始碼保留在頁尾。
- 主標「篝火旁還有位置。」搭配完整營火橫幅，保留前景空位；方形劍徽縮為公會識別。文案延續新手教學、回鍋復健、團本開荒與日常組隊。
- 主要入口為 Discord，次要入口為巴哈全文。公會聯絡人、BattleTag 與網站來源的打招呼訊息各有複製按鈕；複製失敗提供手動選取提示。
- 招生內容、聯絡方式與外連均在 `index.html`，無 JavaScript 仍可閱讀。複製按鈕由 JavaScript 顯示；頁內招生連結捲動並移動焦點至標題，保留既有 `plan／stage／route` 雜湊。
- 營火圖使用 `assets/guild-campfire-640.webp`（640×360）與 `assets/guild-campfire-1280.webp`（1280×720）的 `srcset`；`assets/guild-emblem.webp` 為 240×240 劍徽。圖片維持原構圖、設定尺寸並延遲載入。
- 首頁標題、canonical 與 `social-v3.png` 分享預覽沿用專業規劃主題。這次 HTML、樣式與模組的快取版本為 `20261111-guild`。

初次上線 commit 為 `046fd07bf4d3f770d982784472ff0e107405c8f4`，[Pages 工作成功](https://github.com/jakeuj/wow-forever-professions/actions/runs/43052634666)。已核對正式頁與靜態資源符合該 commit；14 項既有專業測試、桌機與 360px 手機版、四方案與聖騎士三路線、複製與無 JavaScript 內容、進度保存均完成對應驗證。剪貼簿拒絕寫入以模擬 API 驗證實際事件處理器。
