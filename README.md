# 魔獸世界：永恆｜專業與傳承分配規劃

[開啟網站](https://blog.jakeuj.com/wow-forever-professions/)

面向《魔獸世界：永恆》玩家的台灣繁體中文專業規劃頁。預設推薦「雙採集主號＋裁縫／附魔小號」開局，先從兩隻角色起步，再逐步補齊其他工匠。

三版方案依序為：01 雙採集主號＋後勤小號、02 直接全專業分工、03 聖騎士既有配置延伸。包含九項專業覆蓋檢查、六項製造傳承里程碑記錄，以及可複製的分配表與方案連結。既有 `#plan=gathering&stage=final` 連結仍可直接開啟長期配置。

網站為純 HTML／CSS／JavaScript，不需安裝相依套件。進度只保存在使用者瀏覽器，不會讀取或同步遊戲資料。查證日期為 2026-11-11；規則與搭配依據列在網站中。

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

## 發布

GitHub Pages 使用 `main` 分支根目錄發布。所有站內資源使用相對路徑，支援 `/wow-forever-professions/` 專案路徑。

這是非官方社群規劃工具，與 Blizzard Entertainment 無隸屬關係。
