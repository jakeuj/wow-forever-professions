# wow-forever 本機設定範本

複製到家目錄 `.config/wow-forever/local.md`（Windows：`%USERPROFILE%\.config\wow-forever\local.md`），依需要填寫。這是給 agent 讀的 Markdown，不執行；不提交 local.md，也不填密碼、client secret 或 token。每台電腦各自一份。

只記不常變的事實、決定，以及工具看不到的事。等級、專業點數、庫存數量、物品放在哪個角色、裝備這類會變的數字不寫進來：舊數字比 API 與存檔舊，照著用會給錯建議。每次照「最新資料去哪查」即時查，回答時寫出資料時間。

## 最新資料去哪查

- 等級與專業點數：`scripts/forever_api.py character <slug> --part professions`（角色登出後才更新，可能落後一兩天）
- 背包、銀行、信箱：`scripts/syndicator_inventory.py`（`--item`、`--character` 篩選）；`/reload` 或登出後才更新。某角色的銀行或信箱沒資料時，請玩家上那隻角色開一次再 `/reload`
- 拍賣價格：`scripts/auction_brief.py`、`scripts/auction_changes.py --live` 自動取官方 API 和完整掃描中較新的
- 練等路線與材料：同資料夾的 `route.json`（格式見 [route.example.json](route.example.json)），`scripts/auction_brief.py` 據此加一段路線檢查；換路線用 `scripts/leveling_route.py --me --to <上限> --save-route`

## 角色

- 主角色：待設定（名字 姓氏、職業、專業）。問題沒指明角色時，以這個角色規劃回應，等級與專業照上一段即時查
- API 角色 slug：待設定（`名字-姓氏`，見 [battlenet-api.md](battlenet-api.md#角色與公會)）。`scripts/leveling_route.py --me` 會讀這一行反引號裡的值，保持 `API 角色 slug：` 加反引號的格式
- 陣營與 ruleset：待設定（例：部落，亞服 PvP；對應的拍賣場 ID 與阿莫比 realm 名）
- 其他相關角色：選用（例：負責其他專業的朋友、小號的名字與職業）。小號等級與專業同樣即時查；API 要 Lv10 以上並登出過才查得到，查不到就問玩家
- 公會：選用

## 決定與目標

- 選用：目前的目標（例：鍛造衝 300），以及玩家做過的選擇（例：某段練等選哪種路線、附日期）。這些不會因庫存變化而失效

## 存檔看不到的東西

- 選用：工具查不到、但給建議時要知道的事，附日期。例：已寄給某隻小號但對方還沒開信箱的設計圖。已在背包、銀行或信箱的東西不用記，`auction_brief.py` 讀存檔會自動排除

## 安裝與帳號目錄

- 安裝根目錄：待設定（含 `_forever_` 的資料夾）。客戶端版本與插件清單用 `scripts/inspect_install.py` 查，不記在這裡
- WTF 帳號資料夾：待設定（`_forever_/WTF/Account/<帳號>`）

## Battle.net API 憑證位置（只記位置，不記值）

- GitHub repo Secrets：`BLIZZARD_CLIENT_ID`、`BLIZZARD_CLIENT_SECRET`、`FOREVER_PROBE_CHARACTER` 的設定狀態
- macOS 鑰匙圈 service：`wow-forever-battlenet`（已建立／未建立）
- Windows 的 DPAPI 憑證檔 `~/.config/wow-forever/battlenet.xml`（記錄是否已建立）。設定方式見 [本機查詢工具](battlenet-local-tools.md#本機查詢工具)。

## 電腦

- 這台電腦的用途與作業系統，以及遊戲存檔是否在這台；其他電腦另有自己的 local.md
