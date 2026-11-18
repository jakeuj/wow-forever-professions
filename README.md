# 魔獸世界：永恆｜專業與傳承分配規劃

[開啟網站](https://jakeuj.com/wow-forever-professions/)

面向《魔獸世界：永恆》玩家的台灣繁體中文專業規劃頁。預設推薦「雙採集主號＋雙製造小號」：法師裁縫／附魔、獵人製皮／煉金、戰士鍛造／工程，搭配德魯伊採草／剝皮與盜賊採礦。三位製造工匠集中六項製造，五種職業涵蓋九項專業；盜賊第二格可彈性保留。

四版方案依序為：01 雙製造小號（`crafting`，預設）、02 雙採集後轉製造（`gathering`）、03 直接全專業分工（`balanced`）、04 聖騎士多路線（`paladin`）。包含九項專業覆蓋檢查、六項製造傳承里程碑記錄，以及可複製的分配表與方案連結。既有 `#plan=gathering&stage=final` 連結仍可直接開啟長期配置。

聖騎士方案提供四條可切換、可複製分享的路線：

- [A 保留採礦／鍛造](https://jakeuj.com/wow-forever-professions/#plan=paladin&route=keep)：四位製造角色，小號集中其餘製造；原本 `#plan=paladin` 連結也預設開啟這條。
- [B 主角鍛造／工程](https://jakeuj.com/wow-forever-professions/#plan=paladin&route=crafting)：聖騎士與法師、獵人共三位雙製造工匠，盜賊供礦。
- [C 主角採礦／剝皮](https://jakeuj.com/wow-forever-professions/#plan=paladin&route=gathering)：三位小號製造，戰士接手鍛造／工程、德魯伊供草藥。
- [D 術士接布甲](https://jakeuj.com/wow-forever-professions/#plan=paladin&route=warlock)：聖騎士保留採礦／鍛造，術士裁縫／附魔，法師草藥／煉金（轉化軍團鋼供鍛造），獵人剝皮／製皮，盜賊工程；五位角色都有製造。

四條路線都是五種不同職業、九項專業全覆蓋、18 點製造傳承上限，另列主角專業調整、材料流向與適合情境。

網站為純 HTML／CSS／JavaScript，不需安裝相依套件。進度只保存在使用者瀏覽器，不會讀取或同步遊戲資料。查證日期為 2026-11-11；規則與搭配依據列在網站中。

## 《黎明之劍》公會招生

三個頁面的左上角以「黎明之劍 / 專業議事廳」呈現，公會名採淡金色，副標為 `WOW FOREVER · HORDE GUILD`，保留回首頁的導覽功能。

專業分配表之後設有[公會招生區](https://jakeuj.com/wow-forever-professions/#guild)，面向永恆亞服 PvP 部落玩家。文案依 [2026-11-11 巴哈招生文](https://forum.gamer.com.tw/C.php?bsn=5219&snA=681451)，以新手教學、回鍋復健、日常組隊與預計 2026 年 12 月團本開荒為主。

主要入口為 [Discord](https://discord.gg/RyTEUNTMMt)，另提供巴哈全文與公會公開聯絡方式：遊戲內私訊 `真田 信村 / 南方 勇者`，BattleTag `御星幻#3967 / amigo#3262`。聯絡欄依使用者 2026-11-13 指定內容更新。

招生圖採用使用者提供的營火橫幅，`assets/guild-campfire-640.webp`、`assets/guild-campfire-1280.webp` 保留完整構圖，`assets/guild-emblem.webp` 為方形公會識別。營火圖依螢幕寬度載入，所有圖片均設定尺寸與延遲載入。

分配原則區開頭另放置「各有所長，一起準備下一段冒險。」專業分工插圖，呼應《黎明之劍》的互助與傳承意境。`assets/guild-professions-640.webp`、`assets/guild-professions-1280.webp`、`assets/guild-professions-1672.webp` 依螢幕寬度載入，保留完整人物與前景空位，設定圖片尺寸、替代文字與延遲載入；列印時隱藏插圖，保留分配說明。

聯絡區以兩張人物卡呈現，每位聯絡人的遊戲角色與 BattleTag 放在同一卡片；桌機並排、手機上下排列。角色名稱與 BattleTag 分別複製，避免將兩位聯絡方式一起貼入遊戲。開場訊息另置於下方，可單獨複製。

招生文案、聯絡方式與外連均在靜態 HTML 中，無 JavaScript 時仍可閱讀與手動複製；啟用 JavaScript 後顯示五個複製按鈕，成功時按鈕短暫顯示「已複製」並播報所複製的內容。頁內招生入口會捲動並移動焦點至標題，保留目前的方案分享參數。複製失敗時顯示手動選取提示。

## 終局採購清單（個人整理頁）

互相連結的終局採購與練等筆記，價格為亞服 PvP 部落拍賣場的日期快照：

- [`endgame/`](https://jakeuj.com/wow-forever-professions/endgame/)：聖騎鐵匠的附加物品、依專精挑選的設計圖、聖騎職業套裝、軍團鋼瓶頸與材料。
- [`alchemy/`](https://jakeuj.com/wow-forever-professions/alchemy/)：分享給煉金同伴的轉化、配方（AH／NPC／商人青睞／看到再收）與材料行情。
- [`speculation/`](https://jakeuj.com/wow-forever-professions/speculation/)：配方期貨清單，依經典版經驗整理會漲的條件、可囤與不要囤的配方。
- [`leveling/`](https://jakeuj.com/wow-forever-professions/leveling/)：鍛造 200→300 的最省路線，列出每段配方與次數，以及每種材料的數量、單價、小計與佔比長條。
- [`alchemy-leveling/`](https://jakeuj.com/wow-forever-professions/alchemy-leveling/)：煉金 1→300 路線，照 wowf.io 的配方順序、用部落掃描價重算，列出每段次數、配方來源（拍賣場或 NPC）與每種材料的數量、單價、小計與佔比；材料費同樣由 `leveling/leveling.js` 讀 `market/data.json` 重算
- [`market/`](https://jakeuj.com/wow-forever-professions/market/)：部落拍賣行情，可依名稱、類型、品質查詢與排序。裝備、武器、配方用官方拍賣 API 的每小時最低一口價，附 24 小時漲跌與 7 天走勢；材料、藥水這類能堆疊的物品官方沒有提供，用站主拍賣小幫手完整掃描的價格。點名稱旁的 ☆ 可以收藏（存在瀏覽器的 localStorage），再複製 `#fav=物品ID.物品ID…` 的連結分享。

- 首頁只在頁尾連到這六頁，各頁也互相連結；都不在主要導覽與 `sitemap.xml`，並設 `noindex`，但網址仍是公開的。
- 純靜態 HTML，沿用 `style.css`，各頁共用 `endgame/endgame.css`；所有連結為相對路徑。
- 物品名稱以 `<span data-ah="遊戲內完整名稱">` 標記，`endgame/ah-copy.js` 會把它們變成點一下就複製的按鈕，方便貼到拍賣場搜尋；剪貼簿被拒時改為選取文字。沒有 JavaScript 時仍是一般文字。
- 標了 `data-ah-list="清單名稱"` 的表格或區塊會變成拍賣小幫手（Auctionator）的購物清單；頁首面板可複製這頁、複製全部頁面或下載 `.txt`，到插件「購買」分頁按「匯入」貼上。名稱加引號做完全比對，套裝前綴加 `data-ah-prefix`；`.is-skip` 的列不列入。行情頁收藏的物品是另一份清單「行情-收藏」，「全部頁面」會一起帶上；行情頁也能把拍賣小幫手匯出的清單貼回來加入收藏。
- 價格與角色進度是手動更新的快照，更新時同步頁面上的快照日期。
- 行情頁讀 `market/data.json`。在遊戲內完整掃描後輸入 `/reload`，再執行 `python3 scripts/build-market-data.py` 重建：價格來自本機的拍賣小幫手存檔，名稱與分類來自 wago.tools 的永恆客戶端資料表，客戶端沒有的名稱與所有圖示取自 Wowhead；查詢結果有快取，已知物品沿用上一份 `data.json`。
- 官方拍賣價：`.github/workflows/auction-collect.yml` 每小時執行 `scripts/collect-auctions.py`，把亞服 PvP 部落拍賣場（TW 區 113 號）的最低一口價寫進 `auction-data` 分支的 `auctions.json`：最近 7 天逐小時，更早每天留一個最低價，保留 90 天。行情頁從 `raw.githubusercontent.com` 讀這個檔，所以 `main` 不會每小時多一個 commit，Pages 也不用重建；讀不到或比掃描舊 3 小時以上時，整頁改用掃描價格。憑證放在 repo Secrets 的 `BLIZZARD_CLIENT_ID`、`BLIZZARD_CLIENT_SECRET`；手動執行的 `auction-probe.yml` 可重新確認哪一間是部落拍賣場。公開 repo 的排程在 60 天沒有活動後會被 GitHub 停用，到 Actions 分頁重新啟用即可。
- 官方 API 涵蓋率：手動執行的 `.github/workflows/api-probe.yml` 跑技能的 `scripts/forever_api_coverage.py`，把官方 Retail／Classic 文件列出的每個端點換成永恆路徑呼叫一次，結果寫進 Step Summary 與 `api-probe` artifact，不 commit。測試角色放在選填的 repo Secret `FOREVER_PROBE_CHARACTER`（`名字-姓氏`），輸出時會遮掉。本機查詢用技能的 `scripts/forever_api.py`，憑證讀環境變數或 macOS 鑰匙圈；整理結果見技能的 `references/battlenet-api.md`。
- 練等頁的 HTML 是路線與價格的快照；`leveling/leveling.js` 開頁時讀 `market/data.json`（依物品 ID），重算單價、小計、佔比、階段合計與設計圖價，所以重建行情資料後材料費會跟著更新。路線本身要重排時，執行技能的 `scripts/leveling_route.py --from 200 --market-json market/data.json --json > route.json`，再跑 `python3 scripts/build-leveling-page.py route.json` 填好頁面的路線、材料與設計圖表（標記外的說明文字手改）。路線會扣掉拍賣場買掉的件數，不夠就換配方或自製中間材料。

## 六項製造升級總覽

[`crafting-leveling/`](https://jakeuj.com/wow-forever-professions/crafting-leveling/) 由首頁的「我的製造里程碑」進入。各列是從技能 1 起步的累計金額，優先順序按各階段的追加支出估算。六項都練到 150 的總預算合併共用材料，再按同一批在售量報價。編排路線時優先比較配方來源與當次在售量。

以拍賣小幫手的慢速模式完整掃描台灣 PvP 部落拍賣場，確認無限副本手冊的專業模組已啟用，再在遊戲內輸入 `/reload`。用實際安裝位置取代範例路徑：

```powershell
python scripts/build-crafting-leveling.py --root 'C:/Games/World of Warcraft'
```

重建會讀同一輪的 `Auctionator.lua` 與 `DungeonsForeverProf.lua`，使用後者保存的各價位件數。需要指定存檔時加 `--file '<Auctionator.lua 路徑>'`。資料不完整或市場不符時會留下上一份頁面。加入 `--check` 可驗證已產生的 HTML 是否與輸入一致。路線資料依本機無限副本手冊的繁中資料表與 `scripts/crafting-leveling-routes.json` 中已核對的替代段落，估價與排序會一併產生。

## 專案技能

共用的 [wow-forever 技能](.agents/skills/wow-forever/SKILL.md) 位於 `.agents/skills/wow-forever`，包含永恆玩法、插件查證、專業與傳承規劃、網站及公會招生維護、官方 API 與公開資料來源參考，以及唯讀插件盤點工具。

技能文件使用 repo 相對路徑與通用佔位符。個人角色、帳號目錄、私人 BattleTag、本機絕對路徑與憑證留在操作環境；公開公會聯絡方式統一參照既有招生內容。

## 本機預覽

在專案目錄執行：

```sh
python -m http.server 8765 --bind 127.0.0.1
```

開啟 `http://127.0.0.1:8765/`。ES modules 需經 HTTP 提供。

## 驗證

```sh
node --test scripts/plans.test.mjs
python -m unittest discover -s scripts -p test_crafting_leveling.py
```

資料集中於 `data.mjs`；`app.js` 處理方案切換、複製與本機進度。分享圖可用 `scripts/make-social-card.py` 重建，需要 Python、Pillow 與 Windows 微軟正黑體。

招生區另以瀏覽器檢查桌機與 360px 手機版、五個複製按鈕、既有路線參數保留、停用 JavaScript 後的靜態內容，以及傳承進度重新整理後的保存。剪貼簿拒絕寫入情境可用受限瀏覽器測試；自動化環境若接管剪貼簿，則以 API 拒絕的模擬驗證實際事件處理器。

## 發布

GitHub Pages 使用 `main` 分支根目錄發布。所有站內資源使用相對路徑，支援 `/wow-forever-professions/` 專案路徑。

這是非官方社群規劃工具，與 Blizzard Entertainment 無隸屬關係。
