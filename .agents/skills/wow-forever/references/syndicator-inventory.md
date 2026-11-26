# Syndicator 跨角色庫存

Battle.net API 只給已穿裝備，背包、銀行與信箱要靠插件存檔。只想讓 agent 讀庫存、不換背包外觀時，單裝 Syndicator 即可；它只在提示框加各角色件數。[291，9632417](https://www.curseforge.com/wow/addons/syndicator/files/9632417)（2026-11-15）列 **Forever、1.60.1**，並修了 Forever 公會伺服器名稱。2026-11-20 站主單裝 291 後實測可讀；2026-11-23 本機已是 293，存檔照樣讀得到，也列在[插件清單](https://jakeuj.com/wow-forever-professions/addons/)上。

- **記錄時機**：新插件要完全重開遊戲才載入，`/reload` 不夠。每個角色登入一次才有背包；銀行、信箱要各開一次；公會銀行只記到「去過」與金錢，沒有物品。資料在 `/reload` 或登出時寫進帳號層 `SavedVariables/Syndicator.lua`。
- **讀取**：`python '<skill-dir>/scripts/syndicator_inventory.py' --root '<WoW 安裝根目錄>'`，可加 `--character`、`--item` 篩選或 `--json`。`SYNDICATOR_DATA.Characters["名 姓-PvP"]` 下的 `bags` 是各背包的格子陣列，Forever 銀行在 `bankTabs[n].slots`（`bank` 是空的），`mail` 是物品平鋪陣列；每格有 `itemID`、`itemCount`、`quality`、`itemLink`，空格是 `{}`。
- **用在哪**：`scripts/auction_brief.py` 讀同一份存檔，扣掉已有的再推薦買、找可以賣的，並寫出在哪個角色的背包、銀行或信箱，見[行情快訊](auction-market.md#行情快訊現在該買賣什麼)。[專業練等試算](leveling-route.md)也用庫存扣除已持有的材料與設計圖。
- **信箱**：拍賣場買到的物品先寄到信箱。站主說買到了、存檔裡卻還在信箱時，提醒去領；經典版信件 30 天後退回或刪除，永恆以遊戲內為準。
- 存檔含角色名稱，只在本機讀，不寫進 repo。

## 魚類庫存與物品 ID

1. 用 `syndicator_inventory.py --json` 讀完整庫存，可用 `--character` 指定角色。問包包就讀 `parts.bags.items`，問銀行、信箱或跨角色庫存就依題意納入 `bankTabs`、舊存檔的 `bank` 或 `mail`，並保留位置別的件數。回報使用的存檔時間，尚未記錄的位置標成未記錄。
2. 從[漁獲、來源與用途](public-data-sources.md#釣魚漁獲來源與用途)建立魚種的物品 ID 清單，再與庫存的 `id` 交集。盤點範圍包括已確認的生魚與任務魚。目錄缺項或有異名時，按物品 ID 補查永恆物品頁。魷魚、龍蝦、蚌類、箱子、荊棘藻等在問海鮮或全部漁獲時，按類別附列。料理用成品 ID 另外辨識。
3. 回報台服物品名、角色、位置和件數。需要補充來源與用途時，列可釣的區域或其他取得方式，以及確認過的配方成品或任務名稱。釣區資料說明去哪裡取得，背包紀錄提供持有數量。用途缺資料時標為待查。

用下列已核對的 ID 試查。盤點時依實際魚種清單擴充 `ids`。

```sh
python '<skill-dir>/scripts/syndicator_inventory.py' --root '<WoW 安裝根目錄>' --json |
  jq --argjson ids '[6289, 6359, 8365, 13422, 13757, 13760]' '
    .characters[] as $character
    | $character.parts.bags.items[]?
    | select(.id as $id | $ids | index($id) != null)
    | {character: $character.character, id, name, count}'
```
