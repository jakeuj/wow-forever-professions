# 黎明之劍公會｜魔獸世界：永恆

[公會官網](https://jakeuj.com/wow-forever-professions/) · [專業與傳承分配規劃](https://jakeuj.com/wow-forever-professions/professions/) · [製造升級總覽](https://jakeuj.com/wow-forever-professions/crafting-leveling/) · [部落拍賣行情](https://jakeuj.com/wow-forever-professions/market/)

《黎明之劍》是《魔獸世界：永恆》亞服 PvP 部落公會，歡迎新手、回鍋與老手。首頁提供公會介紹、招募聯絡方式與玩家工具，包含站主的插件清單。

## 維護地圖

網站使用靜態 HTML、CSS 和 ES modules，由 GitHub Pages 直接發布。各功能的程式與樣式放在自己的目錄，共用版面、導覽與控制項定義於 `style.css`。

| 功能 | 維護入口 |
| --- | --- |
| 公會首頁 | `index.html` 是招募文案、公開聯絡人與玩家工具入口的來源。複製互動和首頁舊網址在 `guild/`。 |
| 公會資料 | `guild/overview.mjs` 顯示概況，`professions/artisans/` 提供配方搜尋。`scripts/collect_guild.py` 建立快照，`guild/worker/` 發布與讀取。 |
| 軍械庫與練等匯入 | `guild/worker/armory.mjs` 讀角色資料，`players/players.mjs` 提供匯入操作，`crafting-leveling/state.mjs` 管理練等計畫。端點規則見 [Battle.net API（永恆）](.agents/skills/wow-forever/references/battlenet-api.md#角色與公會)。 |
| 專業與傳承 | `professions/` 內的 `data.mjs` 定義方案、配對及點數規則，`planner.mjs` 控制切換與分享，`milestones.mjs` 讀寫進度。 |
| 六項製造升級 | `crafting-leveling/planner.mjs` 控制網頁試算，`auto-search.mjs` 搜尋自動路線。Python 建置入口為 `scripts/build-crafting-leveling.py`，各模組和產物見[練等來源與產物](#練等來源與產物)。 |
| 行情與採購 | `market/model.mjs` 合併官方與掃描快照、計算漲跌及排序，`market/market.js` 處理載入與頁面互動。購物清單由 `endgame/ah-copy.js` 匯整。跨陣營價差頁由 `scripts/build-cross-faction-page.py` 填入。木箱貢獻頁的木箱與填法在 `waylaid/data.mjs`，`waylaid/optimizer.mjs` 依價位算最便宜的組合，用 `node --test scripts/waylaid.test.mjs` 驗證。行情規則可用 `node --test scripts/market.test.mjs` 驗證。 |

新增工具時沿用目錄下的 `index.html` 和站內相對連結。分享網址、錨點與瀏覽器儲存鍵都屬於既有介面，變更時先驗證舊資料與連結。

## 採買、軍械庫與團本工具

- 行情頁的批量估價、六項製造的互動試算、配方利潤和團本採買共用 `market-depth.json`。現有拍賣排程把同一輪台區 PvP 部落 113 號價階送到公會 Publisher，Reader 自 KV 提供三小時內的快照。維護端也可在完整站主掃描後跑 `python scripts/build-crafting-leveling.py --root <遊戲目錄> --scan-depth-out market/scan-depth.json`，提供三小時內的同市場備援。
- 路線資料以 `python scripts/build-crafting-leveling.py --addon-zip <DungeonsForever ZIP>` 重建。現有繁中候選路線來自 [DungeonsForever 2.1.118](https://www.curseforge.com/wow/addons/dungeonsforever/files/9696731) 與 repo 的已核對路線修訂。SHA 或版本以發佈包為準，更新後重新驗證六項製造與中途起算。
- 自動選路預設 90% 達標機率，每次試算重新抓取可用價階，依庫存與學習條件搜尋。要更新完整自動配方庫，在上面的 ZIP 指令加上 `--auto-professions alchemy blacksmithing enchanting engineering leatherworking tailoring`。角色等級用於核對配方和升階條件，留空時仍可使用已學配方及已具備的技能階級。
- 配方目錄由公會排程以 `recipes` 模式收集官方六項製造配方，免登入訪客可瀏覽；官方目錄暫時失效時頁面提供已核對的練等配方。收藏、角色分工、勾選和已學配方存在瀏覽器。
- 配方目錄依 ID 收錄，名稱依繁中配方名、繁中成品名和英文配方名補足。練等建置使用已核對的官方材料與固定產量，產量區間另外顯示。重新核對後可用 `python scripts/build-crafting-leveling.py --battle-net-audit <本機核對報告>` 更新建置資料，再重建練等配方庫。
- 軍械庫可匯入角色的已學配方、目前技能和技能上限，練等計畫按角色與專業保存在瀏覽器。更換自動選路配方庫後，將 Reader 的 `recipes.json` 存在本機，再執行 `python scripts/build-crafting-leveling.py --battle-net-catalog <本機快照路徑>` 重建配方 ID 對照。
- 正式發布順序為 Publisher、Reader、資料排程、Pages。Publisher 沿用 `PUBLISH_TOKEN`。每小時拍賣排程使用現有 GitHub Secrets 向 Battle.net 取得應用程式 token，透過有認證的 Publisher 放進私人 KV，三小時後到期。Reader 只在伺服器端使用 token，也可選擇設定 `BLIZZARD_CLIENT_ID` 和 `BLIZZARD_CLIENT_SECRET` 直接授權。執行 `guild-collect.yml` 的 `refresh` 初始化撤下清單及配方，執行 `auction-collect.yml` 取得新價階。於正式 Pages 開放入口前驗證 Workers 的 `/market-depth.json`、`/recipes.json` 與角色查詢。

## 公會招募

首頁以營火橫幅與劍徽呈現「篝火旁還有位置」，主入口是 Discord，也提供巴哈招生文及遊戲內聯絡方式。公開聯絡人與開場訊息以根目錄 `index.html` 為準。角色名稱、已公開的 BattleTag 與開場訊息可分別複製。停用 JavaScript 時仍可閱讀和選取文字。 [巴哈招生文](https://forum.gamer.com.tw/C.php?bsn=5219&snA=681451)

## 公會概況與工匠名冊

[公會概況](https://jakeuj.com/wow-forever-professions/#overview) 統計永恆台區全公會的角色、職業與等級。[公會工匠名冊](https://jakeuj.com/wow-forever-professions/professions/artisans/) 以配方 ID 關聯角色已學的六項製造配方，用繁中或原文搜尋。[資料使用與撤下](https://jakeuj.com/wow-forever-professions/guild/data-policy/) 說明公開欄位、資料來源與聯絡方式。

`.github/workflows/guild-collect.yml` 每天台灣時間約 07:20 更新，也可手動執行 `refresh`。它復用 `BLIZZARD_CLIENT_ID` 和 `BLIZZARD_CLIENT_SECRET`，透過 `DAWNBLADE_PUBLISH_URL` repository variable 及 `DAWNBLADE_PUBLISH_TOKEN` secret 發布至公會的 Workers KV。公開 Reader 和需要憑證的 Publisher 共用該 namespace。Publisher 的 Cloudflare secret 為 `PUBLISH_TOKEN`，與 GitHub Actions 的值相同。兩支 Worker 的設定分別在 `guild/worker/wrangler.toml` 和 `guild/worker/wrangler.publish.toml`，變更後各自用 `wrangler deploy --config` 發布。

Publisher 另有 cron trigger 啟動拍賣收集（見 `guild/worker/dispatch.mjs`），需要 Cloudflare secret `GITHUB_DISPATCH_TOKEN`。到 GitHub 的 Settings → Developer settings → Fine-grained tokens 建立 token：Repository access 只選本 repo，Permissions 的 Actions 設為 Read and write，到期日記下來。在 `guild/worker` 執行 `npx wrangler secret put GITHUB_DISPATCH_TOKEN --config wrangler.publish.toml`，在提示時貼上。確認方式：`gh run list --repo jakeuj/wow-forever-professions --workflow auction-collect.yml --event workflow_dispatch` 每小時出現兩筆；或 `npx wrangler tail --config wrangler.publish.toml` 看 cron 事件。token 缺少、過期或 workflow 被停用時，cron 事件會記錄錯誤及 HTTP 狀態碼，GitHub 端就只剩原本不準時的排程。

每份快照於擷取七天後過期。部分角色端點錯誤會讓當次名冊標註資料不完整。公會、名冊或靜態資料取用失敗時，未產出的快照沿用上一份至原定到期。查看 Actions 執行摘要可確認發布筆數，公開快照可從 `guild/data-source.mjs` 定義的來源檢查。

撤下角色時，以角色 slug 查 Battle.net 角色資料的 `id`，在 GitHub Actions secret `DAWNBLADE_EXCLUDED_CHARACTER_IDS` 維護整份 JSON 整數陣列。保留先前排除的 ID，加入新項目後手動執行 `apply-exclusions`。這會先更新現有快照並保留原本的到期時間，後續排程也會套用排除名單。KV 跨區讀取可能需要約一分鐘才同步。 [Cloudflare KV 快取行為](https://developers.cloudflare.com/kv/api/read-key-value-pairs/)

## 專業與傳承分配規劃

面向《魔獸世界：永恆》玩家的台灣繁體中文專業規劃頁。預設推薦「雙採集主號＋雙製造小號」：法師裁縫／附魔、獵人製皮／煉金、戰士鍛造／工程，搭配德魯伊採草／剝皮與盜賊採礦。三位製造工匠集中六項製造，五種職業涵蓋九項專業；盜賊第二格可彈性保留。

四版方案依序為：01 雙製造小號（`crafting`，預設）、02 雙採集後轉製造（`gathering`）、03 直接全專業分工（`balanced`）、04 聖騎士多路線（`paladin`）。包含九項專業覆蓋檢查、六項製造傳承里程碑記錄，以及可複製的分配表與方案連結。舊首頁上的 `#plan=...`、`#plans`、`#legacy`、`#principles`、`#sources` 會轉到專業頁，保留網址參數。舊 `#guild` 仍指向公會介紹。

聖騎士方案提供五條可切換、可複製分享的路線：

- [A 保留採礦／鍛造](https://jakeuj.com/wow-forever-professions/professions/#plan=paladin&route=keep)：四位製造角色，小號集中其餘製造；原本 `#plan=paladin` 連結也預設開啟這條。
- [B 主角鍛造／工程](https://jakeuj.com/wow-forever-professions/professions/#plan=paladin&route=crafting)：聖騎士與法師、獵人共三位雙製造工匠，盜賊供礦。
- [C 主角採礦／剝皮](https://jakeuj.com/wow-forever-professions/professions/#plan=paladin&route=gathering)：三位小號製造，戰士接手鍛造／工程、德魯伊供草藥。
- [D 術士接布甲](https://jakeuj.com/wow-forever-professions/professions/#plan=paladin&route=warlock)：聖騎士保留採礦／鍛造，術士裁縫／附魔，法師草藥／煉金（轉化軍團鋼供鍛造），獵人剝皮／製皮，盜賊工程；五位角色都有製造。
- [E 術士附魔煉金](https://jakeuj.com/wow-forever-professions/professions/#plan=paladin&route=warlock-alchemy)：與 D 只交換術士的裁縫與法師的煉金。術士附魔／煉金，拆鍛造綠裝並供應轉化軍團鋼；法師草藥／裁縫，草藥寄給術士。

五條路線都是五種不同職業、九項專業全覆蓋、18 點製造傳承上限，另列主角專業調整、材料流向與適合情境。

網站為純 HTML／CSS／JavaScript，不需安裝相依套件。進度以 `wow-forever-professions:milestones:v1` 保存在使用者瀏覽器。查證日期為 2026-11-11；規則與搭配依據列在網站中。

## 拍賣行情、採購與練等

互相連結的終局採購與練等筆記，價格為亞服 PvP 部落拍賣場的日期快照：

- [`endgame/`](https://jakeuj.com/wow-forever-professions/endgame/)：聖騎鐵匠的附加物品、依專精挑選的設計圖、聖騎職業套裝、軍團鋼瓶頸與材料。
- [`alchemy/`](https://jakeuj.com/wow-forever-professions/alchemy/)：分享給煉金同伴的轉化、配方（AH／NPC／商人青睞／看到再收）與材料行情。
- [`speculation/`](https://jakeuj.com/wow-forever-professions/speculation/)：配方期貨清單，依經典版經驗整理會漲的條件、可囤與不要囤的配方。
- [`leveling/`](https://jakeuj.com/wow-forever-professions/leveling/)：鍛造 225→300 的最省路線（採礦 250 自熔瑟銀）、買錠走法、聖騎自用與[防騎法傷裝](https://jakeuj.com/wow-forever-professions/leveling/#prot)（30～50 級自製與拍賣場的坦裝）、[釣魚 225→300](https://jakeuj.com/wow-forever-professions/leveling/#fishing)（釣點、魚價與魚餌）、[烹飪 195→300](https://jakeuj.com/wow-forever-professions/leveling/#cooking)（買魚來煮與開上限任務），列出每段配方與次數，以及每種材料的數量、單價、小計與佔比長條。
- [`alchemy-leveling/`](https://jakeuj.com/wow-forever-professions/alchemy-leveling/)：煉金 1→300 路線，照 wowf.io 的配方順序、用部落掃描價重算，列出每段次數、配方來源（拍賣場或 NPC）與每種材料的數量、單價、小計與佔比；材料費同樣由 `leveling/leveling.js` 讀 `market/data.json` 重算
- [`cross-faction/`](https://jakeuj.com/wow-forever-professions/cross-faction/)：部落比聯盟便宜的物品，依價差由高到低排，附中立拍賣場轉賣淨利（經典版抽成 15% 估算）。部落價取官方 API 即時掛單，聯盟與中立價取阿莫比的掃描；技能的 `faction_spread.py --json` 產生資料，`python3 scripts/build-cross-faction-page.py <JSON>` 填頁面標記內的表格。
- [`waylaid/`](https://jakeuj.com/wow-forever-professions/waylaid/)：遭攔截的木箱換商人貢獻點，哪一種每點最便宜，以及湊到目標點數（網址參數 `?goal=300&level=34`）要買的木箱與材料，可複製拍賣小幫手清單。開頁時讀 `market-depth.json` 的部落各價位件數重算，三小時內的資料都讀不到就不顯示價格。木箱、填法與貢獻點取自 [遭攔截木箱助手](https://www.curseforge.com/wow/addons/waylaid-auction-helper) v1.3.0 的 `Data.lua` 與 `Favor.lua`（MIT），插件改版時重新產生 `waylaid/data.mjs`，名稱用阿莫比物品清單的繁中名。
- [`market/`](https://jakeuj.com/wow-forever-professions/market/)：部落拍賣行情，可依名稱、類型、品質查詢與排序。裝備、配方、材料、藥水都用官方拍賣 API 的每小時最低一口價（能堆疊的是單價），附 24 小時漲跌與 7 天走勢；官方資料裡沒有、或官方資料比掃描舊時，用站主拍賣小幫手完整掃描的價格。點名稱旁的 ☆ 可以收藏（存在瀏覽器的 localStorage），再複製 `#fav=物品ID.物品ID…` 的連結分享。

- 部落行情從公會首頁進入。七個個人採購、練等、價差與木箱頁位於專業頁尾，並可互相切換。這八頁保留 `noindex`，皆可用公開網址開啟。
- 純靜態 HTML，沿用 `style.css`，各頁共用 `endgame/endgame.css`；所有連結為相對路徑。
- 物品名稱以 `<span data-ah="遊戲內完整名稱">` 標記，`endgame/ah-copy.js` 會把它們變成點一下就複製的按鈕，方便貼到拍賣場搜尋；剪貼簿被拒時改為選取文字。沒有 JavaScript 時仍是一般文字。
- 頁面寫了觸發價的物品另加 `data-ah-buy-below="金額"`。技能的 `scripts/auction_brief.py` 據此比對部落現價（官方 API 與本機完整掃描取較新的），先列出現在該買或該賣的幾項，見[行情快訊](.agents/skills/wow-forever/references/auction-market.md#行情快訊現在該買賣什麼)。
- 標了 `data-ah-list="清單名稱"` 的表格或區塊會變成拍賣小幫手（Auctionator）的購物清單；頁首面板可複製這頁、複製全部頁面或下載 `.txt`，到插件「購買」分頁按「匯入」貼上。名稱加引號做完全比對，套裝前綴加 `data-ah-prefix`；`.is-skip` 的列不列入。行情頁收藏的物品是另一份清單「行情-收藏」，「全部頁面」會一起帶上；行情頁也能把拍賣小幫手匯出的清單貼回來加入收藏。
- 價格與角色進度是手動更新的快照，更新時同步頁面上的快照日期。
- 行情頁讀 `market/data.json`。在遊戲內完整掃描後輸入 `/reload`，再執行 `python3 scripts/build-market-data.py`。程式優先選 `PvP Horde` 資料庫，同輪有無限副本手冊的完整快照時，採用其最低價與在售量。舊資料保留給收藏與分享，直到再次掃到前顯示為歷史掛單。名稱、分類與圖示取自遊戲資料表和 Wowhead。
- 官方拍賣價：`.github/workflows/auction-collect.yml` 每小時執行 `scripts/collect-auctions.py`，把亞服 PvP 部落拍賣場（TW 區 113 號）單件掛單與 `/commodities`（能堆疊的物品，回應的清單 key 是 `auctions`）的最低單價與上架件數寫進 `auction-data` 分支的 `auctions.json`：`/commodities` 失敗或不是同一小時的資料時整個小時跳過；最近 7 天逐小時，更早每天留一個最低價，保留 90 天。行情頁從 `raw.githubusercontent.com` 讀這個檔，所以 `main` 不會每小時多一個 commit，Pages 也不用重建；讀不到或比掃描舊 3 小時以上時，整頁改用掃描價格。憑證放在 repo Secrets 的 `BLIZZARD_CLIENT_ID`、`BLIZZARD_CLIENT_SECRET`；手動執行的 `auction-probe.yml` 可重新確認哪一間是部落拍賣場。公開 repo 的排程在 60 天沒有活動後會被 GitHub 停用，到 Actions 分頁重新啟用即可。 要看某段期間的漲跌，或直接向 API 取即時各價位件數，用技能的 `scripts/auction_changes.py`，見[官方拍賣 API 每小時資料](.agents/skills/wow-forever/references/auction-market.md#官方拍賣-api-每小時資料)。
  - 觸發：GitHub 自己的每小時排程實際一天只跑 3～4 次（2026-11-19～11-23），所以改由 Publisher Worker 的 Cloudflare cron（`guild/worker/wrangler.publish.toml`，每小時 :10、:40）呼叫 GitHub API 的 `workflow_dispatch`，程式在 `guild/worker/dispatch.mjs`。同一小時已記過的快照會跳過，所以一小時兩次只記一次；GitHub 排程留著當備援。Publisher 需要 Cloudflare secret `GITHUB_DISPATCH_TOKEN`：只授權本 repo、權限 Actions「Read and write」的 fine-grained token。設定與檢查見下方 [公會概況與工匠名冊](#公會概況與工匠名冊) 的 Worker 段落。
  - 每小時件數：同一個 run 另把能堆疊物品的 `[最低單價, 上架件數, 最便宜 20 件均價]` 追加到 `auction-data` 分支的 `hourly/<台灣日期>.jsonl`（一行一次快照，約 20 KB；保留 56 天，格式見 `collect-auctions.py` 開頭）。行情頁不讀這些檔。累積一兩週後用技能的 `scripts/auction_hours.py` 比較各台灣時段（`--weekday` 比星期）的價格與件數，見[時段與星期的價格](.agents/skills/wow-forever/references/auction-market.md#時段與星期的價格)。
- 官方 API 涵蓋率：手動執行的 `.github/workflows/api-probe.yml` 跑技能的 `scripts/forever_api_coverage.py`，把官方 Retail／Classic 文件列出的每個端點換成永恆路徑呼叫一次，結果寫進 Step Summary 與 `api-probe` artifact。選填的 repo Secret `FOREVER_PROBE_CHARACTER`（`名字-姓氏`）供角色端點取樣，輸出時會遮掉。操作見 [端點實測與探測](.agents/skills/wow-forever/references/battlenet-api-coverage.md)，個別查詢與憑證設定見 [本機查詢工具](.agents/skills/wow-forever/references/battlenet-local-tools.md)。
- 練等頁的 HTML 是路線與價格的快照；`leveling/leveling.js` 開頁時讀 `market/data.json`（依物品 ID），重算單價、小計、佔比、階段合計與設計圖價，所以重建行情資料後材料費會跟著更新。路線本身要重排時，執行技能的 `scripts/leveling_route.py --from 225 --to 300 --mining 250 --products disenchant --live --json > route.json`，再跑 `python3 scripts/build-leveling-page.py route.json` 填好頁面的路線、材料與設計圖表（第二個分頁用 `--mining 230` 的結果加 `--prefix de-`；標記外的說明文字手改）。路線會扣掉拍賣場買掉的件數，不夠就換配方或自製中間材料。

## 六項製造升級總覽

[`crafting-leveling/`](https://jakeuj.com/wow-forever-professions/crafting-leveling/) 可從公會首頁或專業頁的「我的製造里程碑」進入。各列是從技能 1 起步的累計金額，優先順序按各階段的追加支出估算。六項都練到 150 的總預算合併共用材料，再按同一批在售量報價。編排路線時優先比較配方來源與當次在售量。

以拍賣小幫手的慢速模式完整掃描台灣 PvP 部落拍賣場，確認無限副本手冊的專業模組已啟用，再在遊戲內輸入 `/reload`。用實際安裝位置取代範例路徑：

```powershell
python scripts/build-crafting-leveling.py --root 'C:/Games/World of Warcraft'
```

重建會讀同一輪的 `Auctionator.lua` 與 `DungeonsForeverProf.lua`，使用後者保存的各價位件數。需要指定存檔時加 `--file '<Auctionator.lua 路徑>'`。資料不完整或市場不符時會留下上一份頁面。加入 `--check` 可驗證已產生的 HTML 是否與輸入一致。路線資料依本機無限副本手冊的繁中資料表與 `scripts/crafting-leveling-routes.json` 中已核對的替代段落，估價與排序會一併產生。

也可用 `--auction-snapshot <JSON 路徑>` 改讀官方價位階梯。快照帶 `region: "tw"`、`ruleset: 1`、`house: 113`、含時區的 `updatedAt`，以及以物品 ID 為鍵、以 `[單價（銅）, 件數]` 陣列為值的 `depth`。價位須取同一輪官方單件掛單與 `/commodities`。

### 練等來源與產物

以下參數接在 `python scripts/build-crafting-leveling.py` 後。重建時使用已核對的插件版本與市場資料。

| 要改的行為 | 來源 | 產物與驗證 |
| --- | --- | --- |
| 練等頁版面與費用呈現 | `scripts/crafting-leveling.html`、`scripts/crafting_leveling/render.py` | `--root <遊戲目錄>` 產生 `crafting-leveling/index.html`，同組輸入加 `--check` 比對。 |
| 配方來源 | `scripts/crafting_leveling/sources.py` 讀插件與已核對資料，`catalog.py` 編排瀏覽器目錄。 | `--addon-zip <ZIP>` 產生 `crafting-leveling/routes.json`。加 `--auto-professions alchemy blacksmithing enchanting engineering leatherworking tailoring` 產生 `crafting-leveling/auto-recipes.json`。跑 Python 與 Node 測試驗證資料與試算。 |
| 固定路線與估價 | `scripts/crafting_leveling/routes.py` 計算固定路線與估價，修訂資料在 `scripts/crafting-leveling-routes.json`。 | `--root <遊戲目錄>` 重建 HTML，路線有更新時以 `--addon-zip <ZIP>` 同步固定路線目錄。 |
| 官方配方欄位與軍械庫 ID 對照 | `scripts/crafting_leveling/catalog.py` 管理目錄、欄位核對與 ID 對照；`sources.py` 載入已核對欄位。 | `--battle-net-audit <核對報告>` 產生 `scripts/battle-net-leveling-data.json`。重建自動配方庫後，以 `--battle-net-catalog <官方配方快照>` 產生 `crafting-leveling/battle-net-recipe-map.json`，跑兩套測試驗證核對與角色匯入。 |
| 掃描價階備援 | `scripts/crafting_leveling/sources.py` 驗證同輪部落完整掃描。 | `--root <遊戲目錄> --scan-depth-out market/scan-depth.json` 匯出備援，核對市場、掃描時間及價階件數。 |

## 專案技能

共用的 [wow-forever 技能](.agents/skills/wow-forever/SKILL.md) 位於 `.agents/skills/wow-forever`，包含永恆玩法、插件查證、專業與傳承規劃、網站及公會招生維護、官方 API 與公開資料來源參考，以及唯讀插件盤點工具。

Codex 直接讀 `.agents/skills`；Claude Code 讀 `.claude/skills/wow-forever`，那是指向同一個資料夾的符號連結，兩邊用的是同一份技能。Windows 要先開啟「開發人員模式」，再於 repo 內執行 `git config core.symlinks true` 與 `git checkout -- .claude/skills/wow-forever`，連結才會還原；否則它只是一個寫著路徑的文字檔，Claude Code 讀不到技能。

技能文件使用 repo 相對路徑與通用佔位符。個人角色、帳號目錄、私人 BattleTag、本機絕對路徑與憑證留在操作環境；agent 需要時讀家目錄的 `.config/wow-forever/local.md`（每台電腦各一份，不提交，格式見技能的 `references/local.example.md`）。公開公會聯絡方式統一參照既有招生內容。

## 本機預覽

在專案目錄執行：

```sh
python -m http.server 8765 --bind 127.0.0.1
```

開啟 `http://127.0.0.1:8765/`。ES modules 需經 HTTP 提供。

## 驗證

```sh
node --test scripts/*.test.mjs
python -m unittest discover -s scripts
```

專業頁的分享圖可用 `scripts/make-social-card.py` 重建，需要 Python、Pillow 與 Windows 微軟正黑體。公會首頁的分享圖 `assets/social-guild.jpg` 由營火橫幅縮放為 1200 × 675。

在桌機與 360px 手機版檢查首頁、專業頁與三個工具入口。驗證舊分享網址、里程碑保存、剪貼簿成功與手動備援、停用 JavaScript 後的招募與預設分工，以及行情收藏與購物清單匯出。

## 發布

GitHub Pages 使用 `main` 分支根目錄發布。所有站內資源使用相對路徑，支援 `/wow-forever-professions/` 專案路徑。

多台電腦或其他 agent session 都可能直接推送 `main`，所以推送前先 `git fetch`，遠端有新 commit 時先 rebase 再推。同一個資料夾也可能同時有別的 session 在工作：提交時只 `git add` 自己改的檔案；推送前用 `git log origin/main..HEAD` 看有沒有別人還沒推的 commit，有的話先問站主要不要一起推，因為推送 `main` 會連它們一起上線。

這是非官方社群規劃工具，與 Blizzard Entertainment 無隸屬關係。
