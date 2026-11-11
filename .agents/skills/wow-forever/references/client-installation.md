# 永恆客戶端與版本管理

查核日期：2026-11-11。適用於只保留 Forever、停用 CurseForge Retail 管理，以及 Battle.net 解除安裝問題。

## CurseForge 停用 Retail

[CurseForge 官方 FAQ](https://support.curseforge.com/support/solutions/articles/9000198422-addons-faq) 說明：遊戲安裝項目無法完全從 App 刪除，但可以停用其插件管理。

操作路徑：設定齒輪 → **World of Warcraft** → **Game Instance 選 Retail** → 關閉 **Manage addons for this instance**。Forever 的管理保持開啟，並核對其路徑為 `_forever_`。

此設定停用的是 Retail 插件管理，不會解除安裝 Retail 遊戲。官方說明沒有保證所有安裝對話框都會隱藏該項目；操作後依實際畫面確認效果。

## Battle.net 只保留永恆

永恆有自己的客戶端，可只安裝 Forever，無須保留 Retail 正式服作為主程式。[暴雪官方安裝步驟](https://worldofwarcraft.blizzard.com/en-gb/news/24303866/sichert-euch-eure-charakternamen-in-world-of-warcraft-forever) 是在 Battle.net 的 Game Version 選 **World of Warcraft: Forever**，再按 Install。

需要移除已安裝的 Retail 時，先正常退出所有 WoW 客戶端，包括永恆；再於 Battle.net 選 **魔獸世界／Retail 正式服**，從開始遊戲旁的齒輪選 **解除安裝**。確認目標是 Retail，保留 Forever。暴雪客服的[按遊戲版本解除安裝說明](https://us.forums.blizzard.com/en/wow/t/how-to-uninstall-classic-and-keep-retail/309374) 以 Classic 為例；當前介面仍須依實際版本名稱核對。

同根目錄的 WoW 版本會使用共用 `Data`。移除單一版本交由 Battle.net 處理，保留 `_forever_`、其中的 `Interface`／`WTF` 及根目錄共用 `Data`；不能把整個 `World of Warcraft` 或 `Data` 當作 Retail 專屬檔案刪除。共用資料的存在不等於必須保留 Retail 客戶端，也不能用 `_retail_` 資料夾大小推算解除安裝可回收的容量。

## 「永恆執行中，無法解除安裝魔獸世界」

遇到「抱歉，你無法在《魔獸世界：永恆》執行中時解除安裝《魔獸世界》」與 `BLZBNTAGT0000096A` 時，核對執行中的 `Wow.exe` 是否來自 `_forever_`。

遇到相同訊息，依完整文字確認是哪個版本仍在執行，請使用者正常離開遊戲後重試；若已退出仍受阻，再檢查程序是否殘留。執行中阻擋本身不能證明永恆依賴 Retail；此錯誤碼亦曾用於其他安裝／更新衝突，不能只憑代碼推定原因。

操作完成後回讀管理器、程序與安裝狀態，分別回報已完成的動作；建議步驟不代表實際已停用管理或解除安裝。
