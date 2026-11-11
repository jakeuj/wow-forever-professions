# AtlasLoot 專案與版本辨識

查證日期：2026-11-08（Asia/Taipei）。以下保留公開專案與發佈紀錄作為辨識線索；目前版本、維護狀態與玩家的安裝內容須重新核對。

## 安裝辨識

從實際安裝根目錄的 `.build.info` 選啟用的 `Product=wowf` 列，並核對 `_forever_/.flavor.info`。插件路徑以 `_forever_/Interface/AddOns` 為基準；只讀必要的 `.toc`，有設定或錯誤排查需求時才讀 `WTF`。

`AtlasLootClassic/AtlasLootClassic_Forever.toc` 的 `Interface`、`Version`、`X-Curse-Project-ID` 可協助辨認套件。目錄或 `.toc` 存在只證明檔案與宣告，不代表遊戲內已載入或運作正常。

## 兩個容易混淆的 AtlasLoot 專案

兩者在查證當日都由 Sliccer 發佈，且發佈檔案均列出支援永恆 `1.60.1`。

| 專案網址 | 頁面顯示名稱 | CurseForge 專案 ID | 當日發佈檔案 |
| --- | --- | --- | --- |
| [atlasloot-classic-forever](https://www.curseforge.com/wow/addons/atlasloot-classic-forever) | AtlasLoot Forever | 1699589 | 1.0.8，2026-11-06；列出 Forever 與 Classic |
| [atlasloot-forever](https://www.curseforge.com/wow/addons/atlasloot-forever) | AtlasLoot Classic Forever | 1422985 | 1.3.3，2026-11-08；列出 Forever |

當時的具體發佈紀錄：

- [AtlasLoot Forever 1.0.8，檔案 9467020](https://www.curseforge.com/wow/addons/atlasloot-classic-forever/files/9467020)：支援 `1.60.1`、`1.15.9`。
- [AtlasLoot Classic Forever 1.3.3，檔案 9503738](https://www.curseforge.com/wow/addons/atlasloot-forever/files/9503738)：支援 `1.60.1`，變更說明標示為 `16001` 的新版部署。

以專案 ID、具體發佈檔與實際 `.toc` 判斷；不能只依網址是否帶 `classic`，或跨專案比較版本數字大小。頁面主推檔案可能落後 Recent Files，判定最新版本時查看 Forever 的檔案列表。是否保留或更換，依目前安裝、作者更新與本次需求決定。
