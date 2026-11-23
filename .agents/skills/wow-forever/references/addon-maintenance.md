# 插件盤點、安裝與排錯

## 辨識分支與啟用狀態

從安裝根目錄的 `.build.info` 選啟用的 `Product=wowf` 列，並核對 `_forever_/.flavor.info`。多個版本共用安裝根目錄時依 Product 選列。插件放在 `_forever_/Interface/AddOns`。可用唯讀工具盤點各 `.toc`。

```sh
python '<skill-dir>/scripts/inspect_install.py' --root '<WoW 安裝根目錄>' --addon '*AtlasLoot*'
```

`--root` 接受安裝根目錄或 `_forever_` 目錄，省略 `--addon` 會盤點全部插件。檢查角色啟用狀態時，優先讀 `_forever_/WTF/Account/<帳號>/<伺服器>/<角色>/AddOns.txt`。依插件宣告查角色層或帳號層 `SavedVariables`；磁碟紀錄可能落後遊戲內尚未儲存的狀態。查客戶端解除安裝、CurseForge 忽略其他版本或共用 `Data`，見[客戶端版本管理](client-installation.md)。

## 查證版本與相容性

- 開作者的專案頁和具體發佈檔案頁，對照已裝 `.toc` 的 `Version`、`Interface`、`X-Curse-Project-ID`，核對 Forever flavor、支援版本、更新日期與變更內容。以專案 ID 和套件目錄分辨同名插件，依各專案自己的發佈紀錄比較。DungeonsForever、ForeverDungeons、DungeonJournal 各有獨立的套件；AtlasLoot 見[專案與版本辨識](environment-and-atlasloot.md)。
- 回報時區分套件宣告、實際啟用與遊戲內驗證。定位載入或 Lua 問題時核對 API、依賴與實際執行結果；調整 `Interface` 只會改宣告。
- 核對 `zhTW` 選單、中文遊戲資料與字型顯示；採用 `zhCN` 回退時明示。挑插件時以需求、相容分支與維護狀況判斷現有版本能否繼續用，並核對重複模組。詳見[插件挑選](addon-selection.md)。

## 安裝與更新

詢問推薦時先查證並回報。收到安裝、更新或修復要求時，優先沿用使用者的管理器與相同發佈來源。使用 CurseForge 時，從目前安裝或系統捷徑找管理器並確認選到 Forever。

1. 確認 `_forever_` 安裝路徑、目標專案 ID 與具體發佈檔案。遊戲執行中可先查證，關閉後再替換。
2. 備份要替換的插件目錄到 `AddOns` 外，確認更新會覆寫的本機修補。保留 `WTF`、SavedVariables 及其他插件。
3. 經管理器完成本次要求，整包子模組一起核對，避免混裝版本。需要 GitHub 專用分支、管理器沒有相容檔案或使用者指定手動安裝時，從作者來源下載 ZIP 到暫存位置，核對檔案路徑、頂層插件目錄、`.toc` 和必要依賴。只替換目標套件，結構為 `AddOns/<插件目錄>/<檔名>.toc`。
4. 回讀最終目錄、`.toc` 版本與專案 ID。有可用的遊戲環境就驗證載入、功能與 Lua 錯誤，回報實際完成的驗證層級。下載或驗證套件失敗時保留原安裝並說明原因。

## Lua 錯誤與設定修復

取得完整錯誤、觸發動作、客戶端與插件版本。核對已載入的分支、缺失依賴、重複目錄和子模組版本，再縮到最少相關插件重現。優先只停用或修復可疑插件。重設前備份該插件的 SavedVariables，使用當前 Forever 可用的指令和 API 驗證。採本機暫時修補時記錄修改位置、原因與復原方式。
