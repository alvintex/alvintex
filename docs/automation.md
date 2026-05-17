# 主動式 ETF 每日自動更新

## 立即抓取

在專案根目錄執行：

```powershell
python scripts/run_daily_auto.py
```

流程會自動：

1. 從 ETF資訊網主動式 ETF 清單搜尋目前收錄的主動 ETF。
2. 逐檔抓取 `https://www.etfinfo.tw/etf/{ETF_CODE}/holdings` 的持股 payload。
3. 依快照日期寫入 `data/normalized/{data_date}/{etf_code}.json`。
4. 與上一個有效日期比較，產生新增、加碼、減碼、出清、持平。
5. 重建 matrix、rankings、search index。
6. 更新 `public/data/latest/` 給前端讀取。

無持股頁或解析不到資料的 ETF 會寫入 `data/errors/{etf_code}.json`，不會中斷整批更新。

## 安裝 Windows 每日排程

建議台灣時間 18:30 後執行，避開多數 ETF 尚未更新的時間。

```powershell
powershell -ExecutionPolicy Bypass -File scripts/install_daily_task.ps1 -Time "18:30"
```

排程名稱預設為 `ActiveETFTrackerDaily`。

查看排程：

```powershell
Get-ScheduledTask -TaskName ActiveETFTrackerDaily
```

手動觸發：

```powershell
Start-ScheduledTask -TaskName ActiveETFTrackerDaily
```

移除排程：

```powershell
Unregister-ScheduledTask -TaskName ActiveETFTrackerDaily -Confirm:$false
```

## 歷史資料策略

公開持股頁提供的是每日快照。系統會保留每次抓到的快照資料夾，因此只要每日排程持續執行，就會累積可比較的歷史資料。

若某檔 ETF 今天尚未更新，該檔會保留在它自己的快照日期資料夾，不會混入最新日期矩陣。

重建已保存的歷史快照：

```powershell
python scripts/rebuild_history.py
```

## 資料來源注意

ETF資訊網頁面明確說明，持股異動是以公開快照差異推估，並不等同基金實際成交紀錄。本站也只呈現觀察資料，不做買賣建議。
