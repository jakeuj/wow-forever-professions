# 公開專業規劃網站維護

這是面向一般玩家的公開專業規劃網站。遊戲規則、專業選擇理由和點數計算見 [professions-and-legacy.md](professions-and-legacy.md)；本檔集中網站的定位、位置與維護約束。

## 專案位置與發布

- 名稱：永恆・專業議事廳／魔獸世界：永恆專業與傳承分配規劃。
- 專案根目錄：此技能所在 repo 的根目錄；從 `.agents/skills/wow-forever` 向上三層定位，避免固定本機 checkout 路徑。
- 公開 repo：[jakeuj/wow-forever-professions](https://github.com/jakeuj/wow-forever-professions)。
- 正式站：[https://jakeuj.com/wow-forever-professions/](https://jakeuj.com/wow-forever-professions/)。
- GitHub Pages 使用 `main` 根目錄與 `.nojekyll`，不設自訂網域，由使用者站網域 `jakeuj.com` 自動掛在 `/wow-forever-professions/`（2026-11-16 起；舊 `blog.jakeuj.com/wow-forever-professions/` 由 Cloudflare 301 過來）；HTTPS 已啟用。後續發布先讀當前 Pages 設定，保留其來源。

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

- [雙製造小號首選](https://jakeuj.com/wow-forever-professions/#plan=crafting)
- [雙採集開局](https://jakeuj.com/wow-forever-professions/#plan=gathering&stage=start)
- [雙採集轉製造的長期配置](https://jakeuj.com/wow-forever-professions/#plan=gathering&stage=final)
- [直接全專業分工](https://jakeuj.com/wow-forever-professions/#plan=balanced)
- [聖騎士路線比較](https://jakeuj.com/wow-forever-professions/#plan=paladin)：舊入口預設 A 保留採礦／鍛造，也可用 `route=keep`。
- [聖騎士 B 主角雙製造](https://jakeuj.com/wow-forever-professions/#plan=paladin&route=crafting)
- [聖騎士 C 主角雙採集](https://jakeuj.com/wow-forever-professions/#plan=paladin&route=gathering)

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

## 個人整理頁：終局採購清單

`endgame/index.html`（鐵匠，`https://jakeuj.com/wow-forever-professions/endgame/`）、`alchemy/index.html`（分享給煉金同伴，`.../alchemy/`）、`speculation/index.html`（配方期貨，`.../speculation/`）、`leveling/index.html`（鍛造練等，`.../leveling/`）與 `market/index.html`（部落拍賣行情，`.../market/`）是站主的個人筆記，不屬於一般玩家的方案內容；各頁共用 `endgame/endgame.css`，頁尾互相連結。

- 首頁只在頁尾連到這五頁；不加入主要導覽、首頁內文或 `sitemap.xml`。
- 配方期貨頁的篩選條件與價格更新步驟以 [market-recipe-value.md](market-recipe-value.md) 的「配方期貨」一節為準。更新時同步頁首的「部落價」標籤、清單說明、資料依據區的時間，以及 scope-note 寫的資料來源與時間。
- 可在拍賣場買的物品名稱包成 `<span data-ah="遊戲內完整名稱">顯示文字</span>`，由 `endgame/ah-copy.js` 轉成複製按鈕。`data-ah` 填要買的那件東西：設計圖、配方要含「設計圖：」「配方：」等前綴，成品與材料用物品名；一組套裝可用共同前綴（例：「設計圖：祝福鎧甲」），並加 `data-ah-prefix`。新增或改名後，以阿莫比的拍賣物品清單與 `/professions/{代號}` 的配方名稱逐一比對，確保完全一致。NPC、商人青睞、聲望取得的項目不加。
- 要買或要盯的表格與區塊加 `data-ah-list="頁別-用途"`（目前：鐵匠-附加物品／設計圖／材料、鍛造-到225／設計圖／225以後、煉金-配方／看到就收／材料、期貨-A買／B小量／C觀望），`ah-copy.js` 會在頁首產生拍賣小幫手購物清單面板：複製這頁、複製全部頁面（讀 `PAGES` 列出的其他頁 HTML）與下載 `.txt`；新增個人頁時把頁名加進 `PAGES` 與網址判斷。行情頁收藏的物品是清單「行情-收藏」（`ah-copy.js` 從 localStorage 的 ID 與 `market/data.json` 的名稱組成），「全部頁面」最後一份就是它；`ah-copy.js` 把清單工具放在 `window.wfpShoppingLists`，行情頁先載入它，再由 `market.js` 提供複製收藏清單、複製全部清單、下載，以及把拍賣小幫手匯出的文字貼回來加入收藏（引號完全比對，沒引號包含比對，只取 `;` 前的名稱）。面板都附拍賣小幫手的介紹與 CurseForge 連結。同名清單在插件內匯入時會整份取代，所以清單內容變了要提醒站主重新匯入那幾份，清單名稱改了要告訴站主刪掉舊的；`.is-skip` 的列、「先別買」與 NPC 區塊不加。格式見 [market-recipe-value.md](market-recipe-value.md) 的拍賣小幫手一節。
- 頁面保留 `<meta name="robots" content="noindex">` 與指向自身的 canonical；不要改用 `robots.txt` 封鎖，否則搜尋引擎讀不到 noindex。
- 頁面說明網址仍公開。角色名稱、BattleTag、帳號等私人資訊不放進頁面；陣營、職業、等級與專業進度依站主當次提供的內容。
- 沿用 `../style.css`（版本參數與首頁一致）並以 `endgame/endgame.css` 補樣式；連結與圖示一律相對路徑，以支援 `/wow-forever-professions/` 專案路徑。
- 內容來源：鍛造與煉金需求讀 [endgame-crafting.md](endgame-crafting.md)，價格依 [market-recipe-value.md](market-recipe-value.md) 的腳本與規則重算。更新時同步頁首快照日期與資料依據區的日期。
- 站主在遊戲內完整掃描或傳來拍賣場截圖時，依 [market-recipe-value.md](market-recipe-value.md) 的「遊戲內資料與阿莫比對照」更新：部落價以遊戲內為準（完整掃描用 `scripts/auctionator_prices.py --from-html` 讀三頁的所有可複製名稱），再用 `scripts/amobi_item_prices.py --from-html` 補上中立與聯盟價格，以及遊戲內資料之前已經被買走的低價。頁面標明哪些是遊戲內、哪些是阿莫比與掃描時間。
- 行情頁：`market/market.js` 讀 `market/data.json`，由 repo 的 `scripts/build-market-data.py` 從拍賣小幫手存檔產生（先請站主完整掃描並 `/reload`）。名稱、品質與分類用 wago.tools 的永恆客戶端資料表（版本取安裝目錄 `.build.info` 的 wowf），客戶端沒有的名稱（約四成）與所有圖示用 Wowhead 的永恆繁中 tooltip 資料；已知物品沿用上一份 `data.json`，所以平常只查新物品。網站不讀阿莫比的端點，只在每列連到阿莫比的物品頁。拍賣小幫手不分陣營，頁面只放主城掃描的結果。官方 API 有的物品（不能堆疊的裝備、武器、配方）改用 `auction-data` 分支的 `auctions.json`（`scripts/collect-auctions.py` 每小時寫入，格式見腳本說明），顯示「官方 HH:MM」、24 小時漲跌與 7 天走勢線，沒貨時變淡並標「M/D H 時起沒貨」。容器、武器、護甲、配方、箭袋（類別 1、2、4、9、11，`market.js` 的 `API_CLASSES`）不會堆疊，官方一定列得到；官方快照比掃描新卻沒有這件時，改標「掃描看到，官方已沒貨」並變淡。官方資料讀不到或比掃描舊 3 小時以上時整頁用掃描價格。本機預覽可加 `?auctions=<測試檔>` 改讀測試資料。收藏存在瀏覽器 localStorage 的 `wfp.market.favorites`（物品 ID 陣列，讀寫都包 try/catch，被封鎖時頁面照常運作並提示先複製連結）；「複製分享連結」產生 `#fav=ID.ID…`，打開時只顯示那些物品，並可「加到我的收藏」或「看全部物品」。網址雜湊另有 `mine=1`（只看收藏）；頁內錨點如 `#sources` 不含 `=`，不會重設篩選。
- 拍賣資料排程：`.github/workflows/auction-collect.yml` 每小時 :12 執行 `scripts/collect-auctions.py`，bot 只 commit 到 `auction-data` 分支；API 連線共用 `scripts/blizzard_api.py`，憑證是 repo Secrets 的 `BLIZZARD_CLIENT_ID`、`BLIZZARD_CLIENT_SECRET`。
  - 檢查：`gh run list --repo jakeuj/wow-forever-professions --workflow auction-collect.yml`，以及 `auctions.json` 的 `updatedAt`。同一快照已記過、或掛單物品不到上次四成時，腳本跳過並在執行摘要留警告；token 失敗則整個 run 失敗。新加入的排程第一次可能延遲一小時以上（2026-11-18 16:10 加入，到 17:36 都還沒排程執行過）；要最新快照時手動跑 `gh workflow run auction-collect.yml --repo jakeuj/wow-forever-professions`，API 每小時 :06 左右更新，:07 之後跑才拿得到新的。
  - 公開 repo 60 天沒有活動時，GitHub 會停用排程，到 Actions 分頁重新啟用。`workflow_dispatch` 的工作流程要先進 `main` 才能手動執行。執行紀錄是公開的，腳本不印 token。
  - 拍賣場可能換編號（例如伺服器合併，或行情頁突然大量出現「官方已沒貨」）：請站主在部落拍賣場完整掃描並 `/reload`，重建 `market/data.json`，再手動跑 `auction-probe.yml`。它比對 repo 裡的 `market/data.json`，所以先推送；也可以下載它的 artifact，用其中的 `best_prices` 和本機的新掃描比對。同價比例最高的那間就是部落拍賣場，再改 `collect-auctions.py` 的 `--house` 預設值。
- 練等頁：路線、次數與材料總量是 [market-recipe-value.md](market-recipe-value.md) 的「練等路線與成本」腳本算出的快照；`leveling/leveling.js` 依物品 ID 讀 `market/data.json` 重算單價、小計、佔比長條、階段合計、總覽卡與設計圖價（行情沒有的材料沿用快照並標「沿用快照」），頁首時間跟著行情資料的完整掃描時間。賣店收回金額固定寫在 `data-lv-vendor`。價格大變、技能進度或等級門檻改變時，重跑腳本（`--json`）再用 `scripts/build-leveling-page.py <route.json>` 填頁面：它改寫 `<!-- lv:card-1/card-2/card-plans/route/mats/plans -->` 標記之間的預算卡數字、路線表、兩張材料表（含「自己做」的中間材料）與設計圖表，以及頁首掃描時間與資料依據的存檔時間；標記外的開頭介紹、時間軸、注意事項要照新路線手改。材料列有 NPC 買的件數時帶 `data-lv-fixed`／`data-lv-other`，`leveling.js` 只用行情重算拍賣場那部分。「在遊戲裡自己排路線」（`#addons`）教玩家用無限副本手冊＋拍賣小幫手在遊戲內重算；選項與按鈕名稱照 [addon-feature-guide.md](addon-feature-guide.md#dungeonsforever-與-auctionator-專業衝等操作) 的繁中介面文字，插件改版、名稱變動時兩邊一起改，並更新段末的實測版本與日期；只依插件說明或原始碼補上的步驟（目前是第 3 步「考慮拍賣行的銷售數量」）在段末註明，站主實測後再拿掉。行情頁的「拍賣小幫手是什麼？」也連到這一段。
- 驗證：桌機與 360px 手機無橫向溢出、手機版表格改為卡片、首頁頁尾連結可進入、頁面的首頁連結回到 `../`。行情頁另確認頁首的掃描日期、件數與官方 API 時間，搜尋與類型篩選、排序、「只看現在有貨」與「只看收藏」、收藏後重新整理仍在、分享連結在清空收藏的瀏覽器打開與加入收藏、網址雜湊還原條件、「顯示更多」、點名稱複製、圖示與走勢線，以及官方資料讀不到時改用掃描價格。手機溢出用 `document.documentElement.scrollWidth` 對 `clientWidth` 判斷：模擬手機時頁面被撐寬，`innerWidth` 會跟著變大（曾因資料依據區不換行的時間字串變成 462px）。自動化腳本點「複製分享連結」寫不進剪貼簿，會改顯示手動複製欄位，這是預期的備援；實際點擊才會複製。

## 外部資料整合

加入物品提示框、材料行情、配方清單或公會工匠名冊時，先讀 [public-data-sources.md](public-data-sources.md) 的增強方向與靜態網站整合模式。需要 API 憑證的資料由排程預先產生；發布方式若從 `main` 根目錄改為 Actions 部署，同步更新本檔與 README。

## 公會招生區

2026-11-11 已發布《黎明之劍》招生整合，[公開入口為 `#guild`](https://jakeuj.com/wow-forever-professions/#guild)。公會公開資訊與招募文來源統一查 [dawnblade-guild.md](dawnblade-guild.md)。

- 網站繼續以專業規劃為主；首頁只有一句邀請，完整招生區置於分配表之後、分配原則之前。手機主要導覽為「專業／傳承／公會」，資料依據與原始碼保留在頁尾。
- 主標「篝火旁還有位置。」搭配完整營火橫幅，保留前景空位；方形劍徽縮為公會識別。文案延續新手教學、回鍋復健、團本開荒與日常組隊。
- 主要入口為 Discord，次要入口為巴哈全文。公會聯絡人、BattleTag 與網站來源的打招呼訊息各有複製按鈕；複製失敗提供手動選取提示。
- 招生內容、聯絡方式與外連均在 `index.html`，無 JavaScript 仍可閱讀。複製按鈕由 JavaScript 顯示；頁內招生連結捲動並移動焦點至標題，保留既有 `plan／stage／route` 雜湊。
- 營火圖使用 `assets/guild-campfire-640.webp`（640×360）與 `assets/guild-campfire-1280.webp`（1280×720）的 `srcset`；`assets/guild-emblem.webp` 為 240×240 劍徽。圖片維持原構圖、設定尺寸並延遲載入。
- 首頁標題、canonical 與 `social-v3.png` 分享預覽沿用專業規劃主題。這次 HTML、樣式與模組的快取版本為 `20261111-guild`。

初次上線 commit 為 `046fd07bf4d3f770d982784472ff0e107405c8f4`，[Pages 工作成功](https://github.com/jakeuj/wow-forever-professions/actions/runs/43052634666)。已核對正式頁與靜態資源符合該 commit；14 項既有專業測試、桌機與 360px 手機版、四方案與聖騎士三路線、複製與無 JavaScript 內容、進度保存均完成對應驗證。剪貼簿拒絕寫入以模擬 API 驗證實際事件處理器。
