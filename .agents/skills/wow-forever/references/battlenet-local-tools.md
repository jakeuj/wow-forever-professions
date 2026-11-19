# 永恆 Battle.net API 本機工具與憑證

設定本機憑證或用腳本查角色情況時讀本檔。端點與 namespace 規則見 [Battle.net API（永恆）](battlenet-api.md)。

## 本機查詢工具

`scripts/forever_api.py` 只用標準庫，依路徑自動選 namespace（`/profile/` 與公會用 profile，ruleset 與拍賣用 dynamic，其餘 static），`--ns` 可覆寫。預設 TW 區、`zh_TW`；`--locale all` 回傳所有語系。

`BLIZZARD_CLIENT_ID` 和 `BLIZZARD_CLIENT_SECRET` 都有設定時優先採用。否則 Windows 會讀取家目錄的 `.config/wow-forever/battlenet.xml`，macOS 會讀取鑰匙圈 service `wow-forever-battlenet`（帳號為 Client ID，密碼為 Secret）。各台電腦的設定方式記在 `local.md` 的「Battle.net API 憑證位置」，只記位置和狀態。

首次設定時，在 **API Access → Manage Client** 取得 Client ID 和 Secret。若更換 Actions 使用的同一組 Secret，同步更新 repo 的 `BLIZZARD_CLIENT_SECRET`。 [Battle.net API Access](https://community.developer.battle.net/access/clients)

**macOS**：存一次即可。提示輸入的 password 兩次都貼 client secret；第一次讀取若跳出鑰匙圈存取詢問，選「永遠允許」。

```sh
security add-generic-password -s wow-forever-battlenet -a '<client id>' -w
security find-generic-password -s wow-forever-battlenet  # 確認有這筆，不會顯示 secret
```

在 **Windows** 上已有 `battlenet.xml` 時，從 repo 根目錄直接執行 `python '.agents\skills\wow-forever\scripts\forever_api.py' get /data/wow/ruleset/index`。腳本會用 `Import-Clixml` 載入憑證，成功時會看到 `HTTP 200 dynamic-forever-tw`。同一台電腦、同一個 Windows 帳號的新對話可直接執行這個指令。 [Microsoft 的 Windows 憑證加密說明](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.utility/export-clixml#example-3-encrypt-an-exported-credential-object-on-windows)

首次在 Windows 設定時，由使用者在 PowerShell 執行以下指令。Secret 輸入時會遮蔽，`Export-Clixml` 以 DPAPI 加密 Secret 後儲存在 repo 外。

```powershell
$credentialPath = Join-Path $env:USERPROFILE '.config\wow-forever\battlenet.xml'
$clientId = (Read-Host 'Client ID').Trim()
$clientSecret = Read-Host 'Client Secret' -AsSecureString
$credential = [pscredential]::new($clientId, $clientSecret)
New-Item -ItemType Directory -Force -Path (Split-Path -Parent $credentialPath) | Out-Null
$credential | Export-Clixml -LiteralPath $credentialPath -NoClobber
```

- Windows 出現 `No Battle.net credentials` 時，檢查 `battlenet.xml` 是否存在。若出現 `Could not load the Windows Battle.net credential`，確認目前使用建立該檔的 Windows 帳號及電腦。
- 中文角色名在 PowerShell 直接輸入即可。輸出是 UTF-8；導向檔案或管線時中文變亂碼，先執行 `[Console]::OutputEncoding = [Text.Encoding]::UTF8`。

查詢範例中的 `<skill-dir>` 是 `.agents/skills/wow-forever`。Windows 可用 `python` 或 `py` 執行。

```sh
python3 '<skill-dir>/scripts/forever_api.py' get /data/wow/ruleset/index
python3 '<skill-dir>/scripts/forever_api.py' get /data/wow/search/item --param name.zh_TW=亞麻布 --param _pageSize=5
python3 '<skill-dir>/scripts/forever_api.py' character '<name>-<surname>' --part professions
```

- 狀態行（HTTP、namespace、`Last-Modified`）印到 stderr，JSON 印到 stdout；預設去掉 `_links`，`--links` 保留。非 200 時結束碼為 1。
- Token 只在記憶體與標頭中，不寫檔、不印出。
- 角色資料只輸出到終端機回答當次問題，不寫進 repo、技能或測試資料（見 SKILL.md 的公開 repo 規則）。
