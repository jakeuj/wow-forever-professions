# 公開專業規劃網站維護

黎明之劍公會官網提供招募資訊、公開專業規劃與行情工具。遊戲規則、專業選擇理由和點數計算見 [professions-and-legacy.md](professions-and-legacy.md)；本檔集中網站的定位、位置與維護約束。

## 專案位置與發布

- 專案根目錄：此技能所在 repo 的根目錄；從 `.agents/skills/wow-forever` 向上三層定位，避免固定本機 checkout 路徑。
- 公開 repo：[jakeuj/wow-forever-professions](https://github.com/jakeuj/wow-forever-professions)。
- 正式站：[黎明之劍公會官網](https://jakeuj.com/wow-forever-professions/) · [專業與傳承分配規劃](https://jakeuj.com/wow-forever-professions/professions/)。
- GitHub Pages 使用 `main` 根目錄與 `.nojekyll`，不設自訂網域，由使用者站網域 `jakeuj.com` 自動掛在 `/wow-forever-professions/`（2026-11-16 起；舊 `blog.jakeuj.com/wow-forever-professions/` 由 Cloudflare 301 過來）；HTTPS 已啟用。後續發布先讀當前 Pages 設定，保留其來源。

這是 GitHub repo／Pages 專案，在目前 repo checkout 修改。網站建置技能可協助設計與 QA，發布仍沿用 GitHub Pages。

## 公開受眾與預設

方案順序、公開說明和分享網址見 [README 的專業與傳承分配規劃](../../../../README.md#專業與傳承分配規劃)，配置與路線 ID 以 [professions/data.mjs](../../../../professions/data.mjs) 為準。

沒有方案參數時使用 `crafting`（01），主號長期雙採集，這個方案無需開局／長期切換。保留既有方案 ID 和分享參數。`gathering`（02）以 `stage=start` 選開局、`stage=final` 選長期；`paladin`（04）以 `route` 選 A～E，缺少或無效值回 A。04 的路線字母和外層 PLAN A～D 各自使用。里程碑依訪客本機進度計算，與方案可得上限分開。

## 修改與驗證重點

配置讀 `professions/data.mjs`，各功能入口、建置來源及驗證指令見 [README 維護地圖](../../../../README.md#維護地圖)與[驗證](../../../../README.md#驗證)。修改預設或方案順序時，同時對齊 `professions/index.html` 的靜態預設內容、`professions/planner.mjs` 的初始選取，以及資料中的 PLAN 標籤。如此 JavaScript 載入前、無 JavaScript 時和互動畫面會呈現同一個預設。

保留深色、金色、暗紅視覺與台灣繁中用語。沿用專案路徑下的相對資源；canonical、`og:url` 與分享圖使用正式站的絕對 HTTPS URL。更換分享圖時使用新檔名並同步 metadata；若更新樣式或模組的快取版本，同步 HTML 與模組 import。

按變更驗證對應情境：

- 新訪客開啟專業頁時預設 01 雙製造小號，顯示 9／9 專業、3 位製造工匠、18 點上限；三位工匠各自雙製造、六項各一次，主號保留草藥學／剝皮。
- 02 開局的完整規劃顯示 8／9 專業、4 位製造工匠、15 點上限；長期為 9／9、5 位製造工匠、18 點。既有 `#plan=gathering&stage=final` 仍直接開啟此方案的長期階段。
- 四個方案的切換與鍵盤左右鍵順序跟畫面一致，聖騎士維持最後；手機版兩列選項且無橫向溢出。
- 04 的五個路線選項桌機一列五欄，900px 以下兩欄、640px 以下單欄。開啟或重新整理分享網址能還原選取，其他方案隱藏此選單。
- 涉及傳承記錄時，確認重新整理後保留進度，且計分按六項專業里程碑各算一次。
- 發布完成以對應 commit 的 Pages 工作成功及正式頁、受影響資源可讀為準；來源推送成功是中間狀態。

## 個人整理頁：終局採購清單

`endgame/index.html`（鐵匠，`https://jakeuj.com/wow-forever-professions/endgame/`）、`alchemy/index.html`（分享給煉金同伴，`.../alchemy/`）、`speculation/index.html`（配方期貨，`.../speculation/`）、`leveling/index.html`（鍛造練等，`.../leveling/`）、`alchemy-leveling/index.html`（煉金練等，`.../alchemy-leveling/`）、`cross-faction/index.html`（跨陣營價差，`.../cross-faction/`）與 `market/index.html`（部落拍賣行情，`.../market/`）是站主的個人筆記，不屬於一般玩家的方案內容；各頁共用 `endgame/endgame.css`，頁尾互相連結。

- 官網首頁提供部落行情入口。六個採購、練等與價差筆記在專業頁尾，與行情皆維持 `noindex`，從公開網址可直接開啟。新增個人頁時，各頁的頁尾導覽都加上它。
- 配方期貨頁的篩選條件與價格更新步驟以 [配方期貨與價格更新](market-recipe-value.md#配方期貨囤配方等漲價)為準。更新時同步頁首的「部落價」標籤、清單說明、資料依據區的時間，以及 scope-note 寫的資料來源與時間。
- 可在拍賣場買的物品名稱包成 `<span data-ah="遊戲內完整名稱">顯示文字</span>`，由 `endgame/ah-copy.js` 轉成複製按鈕。`data-ah` 填要買的那件東西：設計圖、配方要含「設計圖：」「配方：」等前綴，成品與材料用物品名；一組套裝可用共同前綴（例：「設計圖：祝福鎧甲」），並加 `data-ah-prefix`。新增或改名後，以阿莫比的拍賣物品清單與 `/professions/{代號}` 的配方名稱逐一比對，確保完全一致。NPC、商人青睞、聲望取得的項目不加。
- 頁面文字寫了「Ng 以下再收」這類觸發價時，在同一個 `data-ah` 上加 `data-ah-buy-below="N"`（金，可有小數），同頁同名的每個 span 都加；`scripts/auction_brief.py` 依它判斷「現在處理」。頁面顯示不變，改觸發價或改價格建議時文字和屬性一起改。目前標在鍛造清單、煉金清單、配方期貨三頁。
- 站主買到頁面上的設計圖或配方後，把那項的 `data-ah` span 改成純文字（同頁每一處），一併拿掉 `data-ah-buy-below`，文字寫買到的日期與價格並加 `<span class="eg-tag bop">已買到</span>`，或在名稱後加「（已買到）」。這樣複製按鈕、購物清單與快訊都不再列它；提醒站主重新匯入那份清單。例：2026-11-23 鍛造清單的奧金斧。要留著轉賣的期貨或替朋友收的配方，保留 `data-ah` 讓複製按鈕還能查價，但拿掉 `data-ah-buy-below`，在 `<tr>` 或 `<li>` 加 `class="is-skip"`（購物清單與快訊都會略過），文字寫「已有 N 張」。頁面不寫是哪個角色拿著。例：2026-11-23 背包存檔顯示已有的有限無敵藥水、貓鼬藥劑、附魔護腕 - 超強耐力等配方。期貨 A 表這樣全標完時，「期貨-A買」清單會消失，提醒站主在插件裡刪掉舊清單。
- 要買或要盯的表格與區塊加 `data-ah-list="頁別-用途"`（目前：鐵匠-附加物品／設計圖／材料、鍛造-225以後／設計圖、鍛造分解-225以後／設計圖、鍛造聖騎-裝備／225以後／設計圖、防騎法傷-裝備／材料、釣魚-看價／要買、烹飪-195到225／蚌肉大餐／225以後、煉金-配方／看到就收／材料／練等到225／練等225以後／練等配方、期貨-A買／B小量／C觀望），`ah-copy.js` 會在頁首產生拍賣小幫手購物清單面板：複製這頁、複製全部頁面（讀 `PAGES` 列出的其他頁 HTML）與下載 `.txt`；新增個人頁時把頁名加進 `PAGES` 與網址判斷。行情頁收藏的物品是清單「行情-收藏」（`ah-copy.js` 從 localStorage 的 ID 與 `market/data.json` 的名稱組成），「全部頁面」最後一份就是它；`ah-copy.js` 把清單工具放在 `window.wfpShoppingLists`，行情頁先載入它，再由 `market.js` 提供複製收藏清單、複製全部清單、下載，以及把拍賣小幫手匯出的文字貼回來加入收藏（引號完全比對，沒引號包含比對，只取 `;` 前的名稱）。面板都附拍賣小幫手的介紹與 CurseForge 連結。同名清單在插件內匯入時會整份取代，所以清單內容變了要提醒站主重新匯入那幾份，清單名稱改了要告訴站主刪掉舊的；`.is-skip` 的列、「先別買」與 NPC 區塊不加。格式見 [拍賣小幫手購物清單](auction-market.md#拍賣小幫手auctionator完整掃描)。
- 頁面保留 `<meta name="robots" content="noindex">` 與指向自身的 canonical；不要改用 `robots.txt` 封鎖，否則搜尋引擎讀不到 noindex。
- 頁面說明網址仍公開。角色名稱、BattleTag、帳號等私人資訊不放進頁面；陣營、職業、等級與專業進度依站主當次提供的內容。
- 沿用 `../style.css`（版本參數與共用樣式一致）並以 `endgame/endgame.css` 補樣式；連結與圖示一律相對路徑，以支援 `/wow-forever-professions/` 專案路徑。
- 內容來源：鍛造與煉金需求讀 [endgame-crafting.md](endgame-crafting.md)，價格依 [拍賣行情](auction-market.md)的腳本與規則重算。更新時同步頁首快照日期與資料依據區的日期。
- 只更新價格時（2026-11-20、11-23 兩次都這樣做）：用 `scripts/auction_changes.py --from-html endgame/index.html alchemy/index.html speculation/index.html --since <上次頁面快照> --live` 取得部落即時各價位件數與期間走勢，`scripts/amobi_item_prices.py --from-html` 補聯盟與中立價，再逐頁手改。同步每頁的頁首標籤、表格 caption、`verified-date` 與 scope-note 的快照時間；頁面寫的是即時快照的 `Last-Modified`（台灣時間），不是 `auctions.json` 的 `updatedAt`。期貨清單照觸發價移動 A／B／C 後，提醒站主重新匯入變動的那幾份購物清單。角色等級與技能點用 `forever_api.py character` 重查再改頁首。
- 站主在遊戲內完整掃描或傳來拍賣場截圖時，依 [遊戲內資料與阿莫比對照](auction-market.md#遊戲內資料與阿莫比對照)更新：部落價以遊戲內為準（完整掃描用 `scripts/auctionator_prices.py --from-html` 讀三頁的所有可複製名稱），再用 `scripts/amobi_item_prices.py --from-html` 補上中立與聯盟價格，以及遊戲內資料之前已經被買走的低價。頁面標明哪些是遊戲內、哪些是阿莫比與掃描時間。
- 行情頁：`market/market.js` 讀 `market/data.json`，由 repo 的 `scripts/build-market-data.py` 從拍賣小幫手存檔產生（先請站主完整掃描並 `/reload`）。名稱、品質與分類用 wago.tools 的永恆客戶端資料表（版本取安裝目錄 `.build.info` 的 wowf），客戶端沒有的名稱（約四成）與所有圖示用 Wowhead 的永恆繁中 tooltip 資料；已知物品沿用上一份 `data.json`，所以平常只查新物品。網站不讀阿莫比的端點，只在每列連到阿莫比的物品頁。拍賣小幫手不分陣營，頁面只放主城掃描的結果。官方 API 有的物品（單件掛單與 `/commodities` 的材料、藥水都有）改用 `auction-data` 分支的 `auctions.json`（`scripts/collect-auctions.py` 每小時寫入，格式見腳本說明），顯示「官方 HH:MM」、24 小時漲跌與 7 天走勢線，沒貨時變淡並標「M/D H 時起沒貨」。官方 API 列出整間拍賣場的掛單；官方快照比掃描新卻沒有這件時，改標「掃描看到，官方已沒貨」並變淡（2026-11-19 前只套用在不能堆疊的類別）。能堆疊物品的件數是上架總數量，價格是單價。官方資料讀不到或比掃描舊 3 小時以上時整頁用掃描價格。本機預覽可加 `?auctions=<測試檔>` 改讀測試資料。收藏存在瀏覽器 localStorage 的 `wfp.market.favorites`（物品 ID 陣列，讀寫都包 try/catch，被封鎖時頁面照常運作並提示先複製連結）；「複製分享連結」產生 `#fav=ID.ID…`，打開時只顯示那些物品，並可「加到我的收藏」或「看全部物品」。網址雜湊另有 `mine=1`（只看收藏）；頁內錨點如 `#sources` 不含 `=`，不會重設篩選。
- 拍賣資料排程：`.github/workflows/auction-collect.yml` 執行 `scripts/collect-auctions.py`，bot 只 commit 到 `auction-data` 分支（`auctions.json` 與 `hourly/`）；API 連線共用 `scripts/blizzard_api.py`，憑證是 repo Secrets 的 `BLIZZARD_CLIENT_ID`、`BLIZZARD_CLIENT_SECRET`。
  - 觸發：GitHub 的 `schedule`（:12）實際一天只跑 3～4 次（2026-11-19～11-23 共 15 次排程執行，台灣 18～23 時五天只有一次），只當備援。主要由 Publisher Worker（`dawnblade-guild-publish`）的 Cloudflare cron `10,40 * * * *` 呼叫 `workflow_dispatch`（`guild/worker/dispatch.mjs`），兩次是為了吸收 API 更新分鐘的漂移，同一小時第二次會跳過。需要 Cloudflare secret `GITHUB_DISPATCH_TOKEN`（本 repo 的 fine-grained token，Actions：Read and write），設定指令見 README 的「公會概況與工匠名冊」。token 到期或 workflow 被停用時，Worker 的 cron 事件會記錄錯誤及 HTTP 狀態碼（`npx wrangler tail --config wrangler.publish.toml`，或 Cloudflare 儀表板 Workers → dawnblade-guild-publish → Logs）。
  - 每小時件數：`--hourly-dir auction-data/hourly` 把能堆疊物品的最低單價、上架件數與最便宜 20 件均價追加到 `hourly/<台灣日期>.jsonl`。一行約 20 KB（2026-11-23 有 904 種），一天約 460 KB，`--hourly-keep-days` 預設保留 56 天，所以分支上大約有 26 MB，較舊的檔案仍留在 git 歷史。行情頁不讀這些檔，分析用技能的 `auction_hours.py`。
  - 檢查：`gh run list --repo jakeuj/wow-forever-professions --workflow auction-collect.yml`（`--event workflow_dispatch` 只看 Worker 觸發的），以及 `auctions.json` 的 `updatedAt`。同一快照已記過、或掛單物品不到上次四成時，腳本跳過並在執行摘要留警告；token 失敗則整個 run 失敗。新加入的排程第一次可能延遲一小時以上（2026-11-18 16:10 加入，到 17:36 都還沒排程執行過）；要最新快照時手動跑 `gh workflow run auction-collect.yml --repo jakeuj/wow-forever-professions`，等 API 的 `Last-Modified` 進入新一小時後再跑，更新分鐘數見[官方拍賣 API](auction-market.md#官方拍賣-api-每小時資料)。
  - 2026-11-19 起也收 `/commodities` 的能堆疊物品，每小時價格變動較多。連續兩小時之間約有 300～900 件物品換最低價，每點約 15 bytes。真的每小時都收到之後，`auctions.json` 估計會從 11/23 的 620 KB（7 天只有 20 個快照）長到約 1.5～2 MB。留意檔案大小與行情頁載入時間；太大時調小 `collect-auctions.py` 的 `--hourly-days`（預設 7），更早的資料會併成每天一點。每小時件數另外放在 `hourly/`，不會讓這個檔變大。
  - 公開 repo 60 天沒有活動時，GitHub 會停用排程，到 Actions 分頁重新啟用。`workflow_dispatch` 的工作流程要先進 `main` 才能手動執行。執行紀錄是公開的，腳本不印 token。
  - 拍賣場可能換編號（例如伺服器合併，或行情頁突然大量出現「官方已沒貨」）：請站主在部落拍賣場完整掃描並 `/reload`，重建 `market/data.json`，再手動跑 `auction-probe.yml`。它比對 repo 裡的 `market/data.json`，所以先推送；也可以下載它的 artifact，用其中的 `best_prices` 和本機的新掃描比對。同價比例最高的那間就是部落拍賣場，再改 `collect-auctions.py` 的 `--house` 預設值。
- 練等頁：路線、次數與材料總量是 [專業練等路線](leveling-route.md)的腳本算出的快照；`leveling/leveling.js` 依物品 ID 讀 `market/data.json` 重算單價、小計、佔比長條、階段合計、總覽卡與設計圖價（行情沒有的材料沿用快照並標「沿用快照」），頁首時間跟著行情資料的完整掃描時間。賣店收回金額固定寫在 `data-lv-vendor`。價格大變、技能進度或等級門檻改變時，重跑腳本（`--json`）再用 `scripts/build-leveling-page.py <route.json>` 填頁面：它改寫 `<!-- lv:card-1/card-2/card-plans/route/mats/plans -->` 標記之間的預算卡數字、路線表、材料表（含「自己做」的中間材料）與設計圖表（從 225 起算的路線沒有 card-1；`--prefix de-` 改填第二個分頁的 `lv:de-*`；已買到的設計圖用 `--owned <物品 ID>`，不進購物清單也不計入圖紙總價；`--live` 的路線要用 `--market` 給同一輪官方快照，格式見腳本開頭），以及頁首掃描時間與資料依據的存檔時間；標記外的開頭介紹、時間軸、注意事項要照新路線手改。材料列有 NPC 買的件數時帶 `data-lv-fixed`／`data-lv-other`，`leveling.js` 只用行情重算拍賣場那部分。「在遊戲裡自己排路線」（`#addons`）教玩家用無限副本手冊＋拍賣小幫手在遊戲內重算；選項與按鈕名稱照 [專業衝等操作](profession-addon-workflow.md) 的繁中介面文字，插件改版、名稱變動時兩邊一起改，並更新段末的實測版本與日期；只依插件說明、原始碼或存檔推斷的內容（目前是第 3 步：「考慮拍賣行的銷售數量」在永恆多半沒有作用）在段末註明，作者修正或站主實測後再改。行情頁的「拍賣小幫手是什麼？」也連到這一段。
- 練等頁的釣魚分頁（`#fishing`）：手寫快照，沒有產生器。`.lv-plans` 的魚價、魚餌價與件數由 `leveling.js` 重算；每竿估值、漲跌說明、料理價與前言要手改。每次估值是各種漁獲「掉落率 × 平均堆疊 × 價格」的總和，只算魚和荊棘藻，箱子另列每 100 次幾個；一行用現價，一行用三天最低價。掉落率取自 [GoldScout](https://wowgoldscout.com/fishing)（只收永恆玩家漁獲，逐區頁 `/fishing/<地圖 ID>`：大河林地 2548、荊棘谷 1434、塔納利斯 1446、菲拉斯 1444、奧特蘭克 1416、海加爾山 2482、東瘟疫之地 1423、艾薩拉 1447）。它是整區全天平均，魚群和開放水域合在一起；頁上的每小時金額照 200 次、也會把天價掛單算進去，不要照抄，改用 `auction_changes.py --live` 的各價位件數自己算，只剩離群掛單的魚用前一天的價。不脫鉤技能取自 DungeonsForeverProf 的 `Core/Data/Data_ProfFishingRoutes.lua`，魚餌時間取自 DungeonsForever 的 `Core/Data/zhTW/Data_Professions.lua`，魚的時段是經典版資料。永恆改過料理效果，寫「留魚煮來賣」之前先查 Wowhead 永恆 tooltip，跟同效果的便宜料理比（2026-11-25 夜鱗魚湯 24.5 銀，與 1 銀的斑點黃尾魚同為法傷 +22）。
- 練等頁的烹飪分頁（`#cooking`）：手寫快照，沒有產生器。材料表與任務材料的價格由 `leveling.js` 重算，次數、三種走法的花費與說明要手改。變色點數取自 DungeonsForeverProf 的 `zhTW/Data_ProfRecipes.lua`，次數用「（灰 − 技能）÷（灰 − 黃）」算期望值，多備取第 90 百分位。`leveling_route.py --profession cooking` 會把賣店價算進成本，195→205 選到要煮 117 次的瘦狼排，直接照抄不實用。蚌肉大餐的材料價一天內可漲數倍（2026-11-25 巨蛋 10 時 3.2 銀，11 時 30 銀，15 時 10 銀只有 19 件），寫建議時列出各價位件數與三天最低價；冷酪由商人買，商人與掉率來源見[公開資料來源](public-data-sources.md#依需求選來源)。
- 跨陣營價差頁：整頁是快照，表格、資料條件、舊聯盟價清單與資料依據都在 `<!-- cf:NAME -->` 標記內，由 `scripts/build-cross-faction-page.py` 從技能 `faction_spread.py --json` 的結果填入（`--min-spread` 預設只列價差 1g 以上）；標記外的說明手改。更新時先跑技能腳本再跑產生器，方法與判讀見[跨陣營價差](auction-market.md#跨陣營價差)。名稱是複製按鈕但不加 `data-ah-list`，不會進購物清單與快訊；聯盟價連到阿莫比物品頁。`cross-faction.js` 只負責「只看轉賣有賺的」篩選（藏 `.cf-loss` 列），沒有 JavaScript 時照常顯示全表。
- 煉金練等頁：路線照 wowf.io 的「煉金快速升級」配方順序，次數用阿莫比的變色點數重算，價格依 `market/data.json`；沒有像鍛造頁那樣的產生器，是手寫快照，以 `leveling/leveling.js` 重算材料費（瓶子是 `data-lv-qty="0"` 加 `data-lv-fixed` 的商人價列）。訓練師等級門檻（技工 50／10 級、專家 125／20 級、工匠 200／35 級）與石鱗魚油一次產出 2 個，取自 DungeonsForeverProf 的 `Core/Data/Data_ProfTrainers.lua` 與 `zhTW/Data_ProfRecipes.lua`（阿莫比寫 1 個）。價格大變或路線要改時，重算各段次數、兩階段材料與賣店收回，再改頁面與預算卡。
- 驗證：桌機與 360px 手機無橫向溢出、手機版表格改為卡片、專業頁尾連結可進入各筆記，頁首品牌通往公會首頁，回專業連結通往 `../professions/`。行情頁另確認頁首的掃描日期、件數與官方 API 時間，搜尋與類型篩選、排序、「只看現在有貨」與「只看收藏」、收藏後重新整理仍在、分享連結在清空收藏的瀏覽器打開與加入收藏、網址雜湊還原條件、「顯示更多」、點名稱複製、圖示與走勢線，以及官方資料讀不到時改用掃描價格。瀏覽器窗格隱藏時 `innerWidth`、`clientWidth` 都是 0，量到的溢出沒有意義，先用 `resize_window` 指定 360 與桌機寬度再量。手機溢出用 `document.documentElement.scrollWidth` 對 `clientWidth` 判斷：模擬手機時頁面被撐寬，`innerWidth` 會跟著變大（曾因資料依據區不換行的時間字串變成 462px）。自動化腳本點「複製分享連結」寫不進剪貼簿，會改顯示手動複製欄位，這是預期的備援；實際點擊才會複製。

## 個人整理頁：插件清單

`addons/index.html`（`https://jakeuj.com/wow-forever-professions/addons/`，`noindex`）是站主插件的手寫盤點，從首頁玩家工具進入；`addons/addons.js` 依用途、啟用狀態與關鍵字篩選卡片。

- 頁首的插件數、資料夾數、客戶端版本與盤點日期都取自同一次本機盤點；改動時連同「資料依據」的存檔時間一起更新。
- 卡片的 `data-addon-state` 有 `enabled`（已啟用）、`disabled`（已停用）、`planned`（準備安裝）。還沒裝的插件標 `planned`，版本寫 CurseForge 最新發佈，「安裝前須知」列預計資料夾、語系與需要注意的設定，且不計入盤點數字。實際裝好並重新盤點後，改回安裝目錄格式與 `enabled`，再更新頁首數字。
- 盤點後才補裝、但還沒重新盤點的插件（目前是 Syndicator）：用 `inspect_install.py --root <安裝根目錄> --addon <資料夾>` 讀 `.toc` 版本，卡片照已安裝格式標 `enabled`，頁首插件數與資料夾數照加，盤點日期不動；「資料依據」寫補裝日期與版本讀取日期。下次整份重新盤點時刪掉這段說明。站主問「我裝了什麼沒列上去」時，比對本頁卡片、本機 `Interface/AddOns`、技能文件的「站主實測」紀錄與 `local.md`。
- CurseForge 等外部連結一律另開分頁（`target="_blank" rel="noopener noreferrer"`，文字後加 `<span aria-hidden="true">↗</span>`，有 `aria-label` 的結尾加「（另開分頁）」），站主才能連續點開好幾個插件安裝，不用一直按返回。新增卡片照這個寫法。
- 改 `addons.css` 或 `addons.js` 時同步更新 `index.html` 引用的 `?v=` 查詢字串。

## 外部資料整合

加入物品提示框、材料行情、配方清單或公會工匠名冊時，先讀 [public-data-sources.md](public-data-sources.md) 的增強方向與靜態網站整合模式。需要 API 憑證的資料由排程預先產生；發布方式若從 `main` 根目錄改為 Actions 部署，同步更新本檔與 README。

公會概況在首頁 `#overview`，工匠名冊在 `/professions/artisans/`。資料排程、Cloudflare 快照與撤下角色的操作見 README 的「公會概況與工匠名冊」。

### Cloudflare 對照

網站用到 Cloudflare 的只有下列幾處（2026-11-23 依 `main` 盤點）；Worker 的部署與撤下角色步驟以 README 為準。

- **DNS**：`jakeuj.com` 的 DNS 在 Cloudflare，記錄不經代理，直接指向 GitHub Pages（185.199.108～111.153），回應標頭是 `server: GitHub.com`，所以網頁本身沒有 Cloudflare 快取或防護。舊 `blog.jakeuj.com` 的 301 由 Cloudflare 處理。
- **兩支 Worker 共用一個 KV**（`guild/worker/`，綁定 `SNAPSHOTS`）：
  - Reader `dawnblade-guild-data`，網址在 `guild/data-source.mjs` 的 `guildDataOrigin`。公開，CORS 只允許 `https://jakeuj.com`，只接受 GET（`curl -I` 會得到 405）。快照有 `/overview.json`、`/artisans.json`、`/recipes.json`、`/market-depth.json`；`/characters/{slug}.json`、`/items/{id}.json` 在伺服器端即時查 Battle.net，`PROFILE_RATE` 限每個 IP 每分鐘 20 次。
  - Publisher `dawnblade-guild-publish`：帶 `PUBLISH_TOKEN` 才能寫入。
- **寫入 KV 的排程**：`guild-collect.yml`（每天）寫概況、名冊、配方快照（7 天到期）與撤下名單；`auction-collect.yml` 加 `--publish-depth`（每小時兩次，由 Publisher 自己的 cron 觸發）寫價階（3 小時內有效）與 `battle-net-token`（3 小時到期）。`auction-probe.yml`、`api-probe.yml` 與 `auction-data` 分支的價格歷史都不經過 Cloudflare。
- **讀 Reader 的頁面**：首頁概況、工匠名冊、配方目錄、玩家頁（含即時查詢）、製造練等、行情頁批量估價與團本採買；價階讀不到時改用 `market/scan-depth.json`。`crafting-leveling/auto-worker.mjs` 是瀏覽器的 Web Worker，與 Cloudflare 無關。
- **排程不準的影響**：GitHub 排程常延後或漏跑（2026-11-22～23 每小時的拍賣排程 24 小時內只跑 4 次；每天 07:20 的公會排程實際約 11:00～12:00 才跑）。價階與 token 都只撐 3 小時；間隔超過時頁面改用備援價階，Reader 若沒有自己的 `BLIZZARD_CLIENT_ID`、`BLIZZARD_CLIENT_SECRET`，角色與物品即時查詢會失敗。是否已設定要登入 Cloudflare 查：`wrangler secret list --config guild/worker/wrangler.toml`。
- **檢查**：`curl -s -H "Origin: https://jakeuj.com" https://dawnblade-guild-data.jakeuj.workers.dev/overview.json`，看 `fetchedAt`、`expiresAt`；價階看 `updatedAt`。

## 公會首頁與舊入口

公會介紹、招募與連結在根目錄 `index.html`。公開資訊來源與圖片維護見 [dawnblade-guild.md](dawnblade-guild.md)。

- 首頁的 `#guild` 保留原有招生入口。工具區提供專業與傳承、製造升級總覽及部落拍賣行情。首頁採用營火分享圖，專業頁沿用 `assets/social-v3.png`。
- `guild/legacy-links.mjs` 將舊首頁的方案雜湊和 `#plans`、`#legacy`、`#principles`、`#sources` 轉到專業頁，保留查詢字串與雜湊。新增分享網址時用 `/professions/`。
- 公會內容以靜態 HTML 提供。檢查桌機、360px 手機版、聯絡方式複製按鈕和拒絕剪貼簿時的手動選取提示。停用 JavaScript 後，可閱讀公會聯絡資訊並從工具區進入專業頁。
