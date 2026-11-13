# 魔獸世界：永恆｜專業與傳承分配規劃

[開啟網站](https://blog.jakeuj.com/wow-forever-professions/)

面向《魔獸世界：永恆》玩家的台灣繁體中文專業規劃頁。預設推薦「雙採集主號＋雙製造小號」：法師裁縫／附魔、獵人製皮／煉金、戰士鍛造／工程，搭配德魯伊採草／剝皮與盜賊採礦。三位製造工匠集中六項製造，五種職業涵蓋九項專業；盜賊第二格可彈性保留。

四版方案依序為：01 雙製造小號（`crafting`，預設）、02 雙採集後轉製造（`gathering`）、03 直接全專業分工（`balanced`）、04 聖騎士多路線（`paladin`）。包含九項專業覆蓋檢查、六項製造傳承里程碑記錄，以及可複製的分配表與方案連結。既有 `#plan=gathering&stage=final` 連結仍可直接開啟長期配置。

聖騎士方案提供三條可切換、可複製分享的路線：

- [A 保留採礦／鍛造](https://blog.jakeuj.com/wow-forever-professions/#plan=paladin&route=keep)：四位製造角色，小號集中其餘製造；原本 `#plan=paladin` 連結也預設開啟這條。
- [B 主角鍛造／工程](https://blog.jakeuj.com/wow-forever-professions/#plan=paladin&route=crafting)：聖騎士與法師、獵人共三位雙製造工匠，盜賊供礦。
- [C 主角採礦／剝皮](https://blog.jakeuj.com/wow-forever-professions/#plan=paladin&route=gathering)：三位小號製造，戰士接手鍛造／工程、德魯伊供草藥。

三條路線都是五種不同職業、九項專業全覆蓋、18 點製造傳承上限，另列主角專業調整、材料流向與適合情境。

網站為純 HTML／CSS／JavaScript，不需安裝相依套件。進度只保存在使用者瀏覽器，不會讀取或同步遊戲資料。查證日期為 2026-11-11；規則與搭配依據列在網站中。

## 《黎明之劍》公會招生

專業分配表之後設有[公會招生區](https://blog.jakeuj.com/wow-forever-professions/#guild)，面向永恆亞服 PvP 部落玩家。文案依 [2026-11-11 巴哈招生文](https://forum.gamer.com.tw/C.php?bsn=5219&snA=681451)，以新手教學、回鍋復健、日常組隊與預計 2026 年 12 月團本開荒為主。

主要入口為 [Discord](https://discord.gg/RyTEUNTMMt)，另提供巴哈全文與公會公開聯絡方式：遊戲內私訊 `真田 幸村 / 南方 勇者`，BattleTag `御星幻#3967 / amigo#3262`。聯絡欄依使用者 2026-11-13 指定內容更新。

招生圖採用使用者提供的營火橫幅，`assets/guild-campfire-640.webp`、`assets/guild-campfire-1280.webp` 保留完整構圖，`assets/guild-emblem.webp` 為方形公會識別。營火圖依螢幕寬度載入，所有圖片均設定尺寸與延遲載入。

分配原則區開頭另放置「各有所長，一起準備下一段冒險。」專業分工插圖，呼應《黎明之劍》的互助與傳承意境。`assets/guild-professions-640.webp`、`assets/guild-professions-1280.webp`、`assets/guild-professions-1672.webp` 依螢幕寬度載入，保留完整人物與前景空位，設定圖片尺寸、替代文字與延遲載入；列印時隱藏插圖，保留分配說明。

聯絡區以兩張人物卡呈現，每位聯絡人的遊戲角色與 BattleTag 放在同一卡片；桌機並排、手機上下排列。角色名稱與 BattleTag 分別複製，避免將兩位聯絡方式一起貼入遊戲。開場訊息另置於下方，可單獨複製。

招生文案、聯絡方式與外連均在靜態 HTML 中，無 JavaScript 時仍可閱讀與手動複製；啟用 JavaScript 後顯示五個複製按鈕，成功時按鈕短暫顯示「已複製」並播報所複製的內容。頁內招生入口會捲動並移動焦點至標題，保留目前的方案分享參數。複製失敗時顯示手動選取提示。

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
```

資料集中於 `data.mjs`；`app.js` 處理方案切換、複製與本機進度。分享圖可用 `scripts/make-social-card.py` 重建，需要 Python、Pillow 與 Windows 微軟正黑體。

招生區另以瀏覽器檢查桌機與 360px 手機版、五個複製按鈕、既有路線參數保留、停用 JavaScript 後的靜態內容，以及傳承進度重新整理後的保存。剪貼簿拒絕寫入情境可用受限瀏覽器測試；自動化環境若接管剪貼簿，則以 API 拒絕的模擬驗證實際事件處理器。

## 發布

GitHub Pages 使用 `main` 分支根目錄發布。所有站內資源使用相對路徑，支援 `/wow-forever-professions/` 專案路徑。

這是非官方社群規劃工具，與 Blizzard Entertainment 無隸屬關係。
