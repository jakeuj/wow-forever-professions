# wow-forever 本機設定範本

複製到家目錄 `.config/wow-forever/local.md`（Windows：`%USERPROFILE%\.config\wow-forever\local.md`），依需要填寫。這是給 agent 讀的 Markdown，不執行；不提交 local.md，也不填密碼、client secret 或 token。每台電腦各自一份。

## 角色

- 主角色：待設定（名字 姓氏、職業、專業）
- API 角色 slug：待設定（`名字-姓氏`，見 [battlenet-api.md](battlenet-api.md#角色與公會)）
- 等級與專業點數：日期化紀錄；給建議前重新詢問
- 陣營與 ruleset：待設定（例：部落，亞服 PvP；對應的拍賣場 ID）
- 其他相關角色：選用（例：負責其他專業的朋友或小號）
- 公會：選用

## 安裝與帳號目錄

- 安裝根目錄：待設定（含 `_forever_` 的資料夾）
- WTF 帳號資料夾：待設定（`_forever_/WTF/Account/<帳號>`）

## Battle.net API 憑證位置（只記位置，不記值）

- GitHub repo Secrets：`BLIZZARD_CLIENT_ID`、`BLIZZARD_CLIENT_SECRET`、`FOREVER_PROBE_CHARACTER` 的設定狀態
- macOS 鑰匙圈 service：`wow-forever-battlenet`（已建立／未建立）
- Windows 的 DPAPI 憑證檔 `~/.config/wow-forever/battlenet.xml`（記錄是否已建立）。設定方式見 [本機查詢工具](battlenet-api.md#本機查詢工具)。

## 電腦

- 這台電腦的用途與作業系統；其他電腦另有自己的 local.md
