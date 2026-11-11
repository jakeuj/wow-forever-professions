# 魔獸世界：永恆｜專業與傳承分配規劃

[開啟網站](https://blog.jakeuj.com/wow-forever-professions/)

台灣繁體中文的全帳號專業規劃頁：比較從零分配、雙採集開局、保留聖騎士採礦／鍛造三版方案。包含九項專業覆蓋檢查、六項製造傳承里程碑記錄，以及可複製的分配表與方案連結。

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
