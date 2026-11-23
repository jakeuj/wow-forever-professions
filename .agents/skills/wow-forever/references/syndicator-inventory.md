# Syndicator 跨角色庫存

Battle.net API 只給已穿裝備，背包、銀行與信箱要靠插件存檔。只想讓 agent 讀庫存、不換背包外觀時，單裝 Syndicator 即可；它只在提示框加各角色件數。[291，9632417](https://www.curseforge.com/wow/addons/syndicator/files/9632417)（2026-11-15）列 **Forever、1.60.1**，並修了 Forever 公會伺服器名稱。2026-11-20 站主單裝 291 後實測可讀；2026-11-23 本機已是 293，存檔照樣讀得到，也列在[插件清單](https://jakeuj.com/wow-forever-professions/addons/)上。

- **記錄時機**：新插件要完全重開遊戲才載入，`/reload` 不夠。每個角色登入一次才有背包；銀行、信箱要各開一次；公會銀行只記到「去過」與金錢，沒有物品。資料在 `/reload` 或登出時寫進帳號層 `SavedVariables/Syndicator.lua`。
- **讀取**：`python '<skill-dir>/scripts/syndicator_inventory.py' --root '<WoW 安裝根目錄>'`，可加 `--character`、`--item` 篩選或 `--json`。`SYNDICATOR_DATA.Characters["名 姓-PvP"]` 下的 `bags` 是各背包的格子陣列，Forever 銀行在 `bankTabs[n].slots`（`bank` 是空的），`mail` 是物品平鋪陣列；每格有 `itemID`、`itemCount`、`quality`、`itemLink`，空格是 `{}`。
- **用在哪**：`scripts/auction_brief.py` 讀同一份存檔，扣掉已有的再推薦買、找可以賣的，並寫出在哪個角色的背包、銀行或信箱，見[行情快訊](auction-market.md#行情快訊現在該買賣什麼)。[專業練等試算](leveling-route.md)也用庫存扣除已持有的材料與設計圖。
- **信箱**：拍賣場買到的物品先寄到信箱。站主說買到了、存檔裡卻還在信箱時，提醒去領；經典版信件 30 天後退回或刪除，永恆以遊戲內為準。
- 存檔含角色名稱，只在本機讀，不寫進 repo。
