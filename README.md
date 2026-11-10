# 自選股看盤(自架・每天自動更新)

## 一次性設定(約 10 分鐘)
1. 到 github.com 註冊/登入 → 右上 **+ → New repository**,名稱例如 `stock-watch`,選 **Public**,建立。
2. 在新 repo 頁面點 **uploading an existing file**,把本資料夾「全部內容」拖進去(含 `data` 資料夾與 `.github` 資料夾;若 `.github` 拖不進去,改用 Add file → Create new file,檔名輸入 `.github/workflows/update.yml` 再貼上內容)。按 **Commit changes**。
3. **Settings → Pages**:Source 選 *Deploy from a branch*,Branch 選 `main` / `(root)`,Save。約 1 分鐘後頁面上方會出現你的網址 `https://你的帳號.github.io/stock-watch/`,手機、電腦都能開,可加到主畫面。
4. **Settings → Actions → General → Workflow permissions** 選 **Read and write permissions**,Save。
5. **Actions** 分頁 → 左側 *update-data* → **Run workflow**,跑一次。綠勾代表成功,`data/data.json` 會被更新;之後每個交易日台灣時間 16:30 與 08:30 自動更新。

## 新增自選股
編輯 `stocks.json`,加一行,例如 `{"code":"2317","name":"鴻海","market":"TW"}`(上櫃股 market 用 `"TWO"`),存檔後手動 Run workflow 一次即可。

## 要先知道的限制
- 抓取程式(`update_data.py`)我在沙盒無法連到 Yahoo 做完整實測,只驗證過解析邏輯。第一次 Run workflow 請看 Actions 的 log:若 Yahoo 擋了 GitHub 的 IP 或頁面改版,該項會保留舊資料(不會整份壞掉),把 log 貼給我我再修。
- 0050 是 ETF,沒有河流圖。本益比/殖利率來自證交所、櫃買 openapi,當日沒資料就顯示「—」。
- 資料為收盤後資料,非即時報價;僅供個人研究參考,不構成投資建議。
