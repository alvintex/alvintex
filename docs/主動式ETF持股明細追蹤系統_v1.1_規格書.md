# 主動式 ETF 持股明細追蹤系統 v1.1 規格書

版本：v1.1  
日期：2026-05-15  
用途：作為本機 localhost MVP 開發、資料格式設計、前端頁面設計、後續 GitHub Pages / GitHub Actions 自動化的共同規格。

---

## 0. v1.1 定位

本系統不是單純顯示單檔 ETF 持股表，而是建立一個「主動式 ETF 持股變化雷達」。

核心目標是每天回答以下問題：

1. 哪些股票被多檔主動式 ETF 同時持有？
2. 哪些股票被多檔 ETF 同步加碼？
3. 哪些股票是新進持股？
4. 哪些股票被減碼或出清？
5. 單一 ETF 今日與前一日相比，持股結構如何變化？
6. 單一個股被哪些 ETF 持有、加碼、減碼、出清？
7. 是否出現「主動 ETF 共識加碼」、「擁擠持股」、「籌碼退潮」或「新題材進場」等交易觀察訊號？

---

## 1. 專案名稱

**主動式 ETF 持股明細追蹤系統**

英文代稱可暫定：

```text
Active ETF Holdings Tracker
```

---

## 2. 追蹤 ETF 範圍

v1.1 預設追蹤下列主動式 ETF：

| ETF 代號 | 狀態 | 備註 |
|---|---|---|
| 00980A | 追蹤 | 需建立資料來源 |
| 00981A | 追蹤 | 優先完成單檔資料驗證 |
| 00982A | 追蹤 | 需建立資料來源 |
| 00984A | 追蹤 | 需建立資料來源 |
| 00985A | 追蹤 | 需建立資料來源 |
| 00987A | 追蹤 | 需建立資料來源 |
| 00991A | 追蹤 | 需建立資料來源 |
| 00992A | 追蹤 | 優先作為 00981A 對照組 |
| 00994A | 追蹤 | 需建立資料來源 |
| 00995A | 追蹤 | 需建立資料來源 |
| 00403A | 預留追蹤 | 若尚未有穩定公開資料，先保留欄位與頁面支援 |

---

## 3. v1.1 開發範圍

### 3.1 MVP 必做

1. 建立每日持股資料標準格式。
2. 建立單檔 ETF 持股明細頁。
3. 建立每日異動分類：新增、加碼、減碼、出清、持平。
4. 建立跨 ETF 持股矩陣。
5. 建立個股被幾檔 ETF 持有的統計。
6. 建立加碼榜、新增榜、減碼榜、出清榜、持平榜。
7. 建立個股搜尋功能。
8. 本機 localhost 可執行，不先接 GitHub Actions。

### 3.2 v1.1 暫不做

1. 不做自動交易。
2. 不直接給買賣建議。
3. 不預測股價。
4. 不把 ETF 持股變化視為唯一交易依據。
5. 不先接完整雲端部署流程。
6. 不先做登入、會員、資料庫後端。

---

## 4. 核心資料欄位

每檔 ETF 每日應轉成同一份標準資料格式。

| 欄位名稱 | 型別 | 說明 | 範例 |
|---|---:|---|---|
| data_date | string | 持股資料日期 | 2026-05-14 |
| run_date | string | 程式執行日期 | 2026-05-15 |
| etf_code | string | ETF 代號 | 00981A |
| stock_id | string | 股號 | 2330 |
| stock_name | string | 股票名稱 | 台積電 |
| stock_display | string | 股票顯示名稱 | 台積電(2330) |
| weight_pct | number | 投資比例，單位 % | 10.26 |
| shares | integer | 持有股數 | 11657000 |
| shares_lot | number | 持有張數，shares / 1000 | 11657 |
| weight_change_pct | number | 比例增減，單位百分點 | 1.29 |
| shares_change | integer | 股數增減 | 1618000 |
| shares_change_lot | number | 張數增減 | 1618 |
| source_change_text | string | 原始資料提供的異動文字 | 加碼 |
| system_change_type | string | 系統重新判斷的異動分類 | 加碼 |
| source_url | string | 資料來源網址 | 待補 |
| source_status | string | 資料狀態 | updated |
| note | string | 異常或備註 | 原始值與系統判斷不一致 |

---

## 5. 日期邏輯

因為主動式 ETF 通常公布前一交易日持股，系統必須分清楚三種日期。

| 欄位 | 說明 |
|---|---|
| run_date | 程式實際執行日期 |
| data_date | ETF 官方資料日期 |
| compare_date | 用來比較的上一筆有效資料日期 |

範例：

```json
{
  "run_date": "2026-05-15",
  "data_date": "2026-05-14",
  "compare_date": "2026-05-13"
}
```

### 日期判斷規則

1. 若今日執行但 ETF 尚未更新，標示 `pending`。
2. 若官網資料日期與前一日相同，標示 `unchanged_source`。
3. 若抓取失敗，標示 `failed`。
4. 若資料成功轉換，標示 `updated`。
5. 若某 ETF 尚未上市或尚無資料，標示 `not_available`。

---

## 6. 異動分類規則

### 6.1 系統主判斷原則

v1.1 採用：

```text
股數變化 = 主判斷
比例變化 = 輔助判斷
```

原因：

1. 投資比例會受到股價漲跌影響。
2. 投資比例會受到 ETF 淨值與規模變化影響。
3. 股數變化較能代表 ETF 是否實際買進或賣出。

### 6.2 分類優先順序

| 優先順序 | 分類 | 判斷條件 | 說明 |
|---:|---|---|---|
| 1 | 新增 | 今日有持股，昨日無持股 | 新進持股 |
| 2 | 出清 | 昨日有持股，今日無持股 | 完全賣出 |
| 3 | 加碼 | 今日 shares > 昨日 shares | 實際持股股數增加 |
| 4 | 減碼 | 今日 shares < 昨日 shares | 實際持股股數減少 |
| 5 | 持平 | 今日 shares = 昨日 shares | 股數未變 |

### 6.3 與原始資料異動文字不一致時

有時官方或整理資料會出現：

- 比例增加但股數減少
- 比例減少但股數增加
- 股數不變但比例變動

系統處理方式：

1. 保留原始異動欄位：`source_change_text`
2. 另建立系統判斷欄位：`system_change_type`
3. 若兩者不同，新增 `note`
4. 前端可顯示「比例與股數方向不一致」提示

範例：

```json
{
  "stock_display": "聯發科(2454)",
  "weight_change_pct": 0.63,
  "shares_change": -100000,
  "source_change_text": "減碼",
  "system_change_type": "減碼",
  "note": "比例增加但股數減少，判斷以股數為準"
}
```

---

## 7. 資料分層設計

v1.1 建議分成 6 層資料。

### 7.1 Raw Layer：原始資料層

保存原始下載或爬取內容，不做過度清洗。

用途：

1. 除錯。
2. 追蹤官方格式變動。
3. 未來可重新轉換資料。

建議路徑：

```text
data/raw/{data_date}/{etf_code}.csv
```

### 7.2 Normalized Layer：標準化資料層

將不同 ETF 來源轉成統一欄位。

建議路徑：

```text
data/normalized/{data_date}/{etf_code}.json
```

### 7.3 Diff Layer：異動資料層

將今日資料與前一有效資料比較。

建議路徑：

```text
data/diff/{data_date}/{etf_code}_diff.json
```

### 7.4 Matrix Layer：跨 ETF 矩陣層

產生股票 × ETF 的持有與異動矩陣。

建議路徑：

```text
data/matrix/{data_date}/holding_matrix.json
_data/matrix/{data_date}/change_matrix.json
```

> 注意：上方 `_data` 若用於 Jekyll/GitHub Pages 可保留；若純靜態前端，建議統一放 `data/matrix`。

### 7.5 Ranking Layer：排行榜資料層

產生加碼榜、新增榜、減碼榜、出清榜、持平榜、持有 ETF 數排行。

建議路徑：

```text
data/rankings/{data_date}/rankings.json
```

### 7.6 Search Index Layer：搜尋索引層

支援前端快速搜尋個股。

建議路徑：

```text
data/search/{data_date}/stock_index.json
```

---

## 8. JSON 格式規格

### 8.1 單檔 ETF 持股 JSON

檔案：

```text
data/normalized/2026-05-14/00981A.json
```

格式：

```json
{
  "meta": {
    "etf_code": "00981A",
    "data_date": "2026-05-14",
    "run_date": "2026-05-15",
    "source_status": "updated",
    "source_url": "",
    "holdings_count": 46
  },
  "holdings": [
    {
      "stock_id": "2330",
      "stock_name": "台積電",
      "stock_display": "台積電(2330)",
      "weight_pct": 10.26,
      "shares": 11657000,
      "shares_lot": 11657,
      "weight_change_pct": 1.29,
      "shares_change": 1618000,
      "shares_change_lot": 1618,
      "source_change_text": "加碼",
      "system_change_type": "加碼",
      "note": ""
    }
  ]
}
```

---

### 8.2 跨 ETF 持有矩陣 JSON

檔案：

```text
data/matrix/2026-05-14/holding_matrix.json
```

格式：

```json
{
  "meta": {
    "data_date": "2026-05-14",
    "etf_count": 11,
    "stock_count": 180
  },
  "rows": [
    {
      "stock_id": "2330",
      "stock_name": "台積電",
      "stock_display": "台積電(2330)",
      "held_etf_count": 10,
      "avg_weight_pct": 11.58,
      "total_shares": 21671999,
      "total_lots": 21672,
      "etfs": {
        "00980A": { "weight_pct": 7.97, "shares": 1761000, "change_type": "加碼" },
        "00981A": { "weight_pct": 10.26, "shares": 11657000, "change_type": "加碼" },
        "00992A": { "weight_pct": 7.97, "shares": 1761000, "change_type": "持平" }
      }
    }
  ]
}
```

---

### 8.3 異動矩陣 JSON

檔案：

```text
data/matrix/2026-05-14/change_matrix.json
```

格式：

```json
{
  "meta": {
    "data_date": "2026-05-14"
  },
  "rows": [
    {
      "stock_id": "2330",
      "stock_name": "台積電",
      "stock_display": "台積電(2330)",
      "add_count": 7,
      "reduce_count": 1,
      "new_count": 0,
      "removed_count": 0,
      "unchanged_count": 1,
      "net_etf_change_score": 6,
      "total_shares_change": 2111000,
      "dominant_signal": "多檔加碼",
      "etfs": {
        "00980A": "加碼",
        "00981A": "加碼",
        "00984A": "減碼",
        "00992A": "持平"
      }
    }
  ]
}
```

---

### 8.4 排行榜 JSON

檔案：

```text
data/rankings/2026-05-14/rankings.json
```

格式：

```json
{
  "meta": {
    "data_date": "2026-05-14",
    "generated_at": "2026-05-15T18:00:00+08:00"
  },
  "rankings": {
    "add_rank": [],
    "new_rank": [],
    "reduce_rank": [],
    "removed_rank": [],
    "unchanged_rank": [],
    "most_held_rank": [],
    "consensus_buy_rank": [],
    "crowded_holding_rank": [],
    "risk_reduce_rank": []
  }
}
```

---

## 9. 排行榜設計

### 9.1 加碼榜

目的：找出多檔 ETF 同步增加持股的股票。

排序建議：

1. 加碼 ETF 數量由多到少。
2. 合計加碼張數由多到少。
3. 平均持股比例由高到低。

欄位：

| 欄位 | 說明 |
|---|---|
| stock_display | 個股名稱 |
| add_etf_count | 加碼 ETF 數 |
| avg_weight_pct | 平均比例 |
| total_shares_change_lot | 合計加碼張數 |
| strong_add_flag | 是否強力加碼 |

強力加碼預設規則：

```text
total_shares_change_lot >= 500
```

---

### 9.2 新增榜

目的：找出新進入主動 ETF 的股票。

排序建議：

1. 新增 ETF 數量。
2. 合計新增張數。
3. 合計新增權重。

強力新增預設規則：

```text
total_new_lot >= 500
```

---

### 9.3 減碼榜

目的：找出 ETF 降低持股的股票。

排序建議：

1. 減碼 ETF 數量。
2. 合計減碼張數絕對值。
3. 平均持股比例是否仍高。

倒貨警示預設規則：

```text
abs(total_shares_change_lot) >= 300
```

---

### 9.4 出清榜

目的：找出被 ETF 完全移除的股票。

排序建議：

1. 出清 ETF 數量。
2. 前一日合計持有張數。
3. 前一日平均權重。

---

### 9.5 持平榜 / 續抱榜

目的：找出 ETF 仍持有但未變動的核心部位。

排序建議：

1. 續抱 ETF 數量。
2. 平均持股比例。
3. 合計持有張數。

核心重倉預設規則：

```text
avg_weight_pct >= 3
```

---

### 9.6 最多 ETF 持有榜

目的：找出共識持股與擁擠交易標的。

排序建議：

1. 持有 ETF 數量。
2. 平均權重。
3. 合計持有張數。

擁擠持股預設規則：

```text
held_etf_count >= 7
```

---

## 10. 交易觀察訊號，不等於買賣建議

v1.1 可加入「觀察訊號」，但必須避免直接變成買賣建議。

### 10.1 訊號分類

| 訊號 | 判斷邏輯 | 可能解讀 |
|---|---|---|
| 多檔加碼 | add_etf_count >= 3 | ETF 共識升溫 |
| 強力加碼 | total_shares_change_lot >= 500 | 主動 ETF 實質買盤增加 |
| 新題材進場 | new_etf_count >= 1 且新增張數大 | 新進持股值得追蹤 |
| 擁擠持股 | held_etf_count >= 7 | 已成為主流共識股 |
| 擁擠轉弱 | held_etf_count 高但 reduce_etf_count 增加 | 籌碼可能退潮 |
| 高權重減碼 | avg_weight_pct >= 3 且減碼 | 核心部位調節 |
| 股數加碼但權重下降 | shares_change > 0 且 weight_change_pct < 0 | 可能股價下跌但 ETF 仍買進 |
| 股數減碼但權重上升 | shares_change < 0 且 weight_change_pct > 0 | 可能股價上漲但 ETF 調節 |

### 10.2 訊號強度分數

可建立 `signal_score`，作為排序參考。

範例：

```text
signal_score = 
  add_etf_count * 3
  + new_etf_count * 4
  + held_etf_count * 1
  + min(abs(total_shares_change_lot) / 500, 5)
  - reduce_etf_count * 2
  - removed_etf_count * 4
```

v1.1 僅作觀察排序，不直接代表投資評等。

---

## 11. 前端頁面規格

### 11.1 首頁 Dashboard

首頁目的：一打開就看到今日主動 ETF 的資金方向。

區塊建議：

1. 今日資料狀態卡片
2. 今日加碼榜
3. 今日新增榜
4. 今日減碼 / 出清警示榜
5. 最多 ETF 持有榜
6. 個股搜尋框
7. ETF 快速切換入口

### 11.2 單檔 ETF 頁

路徑範例：

```text
/etf.html?code=00981A
```

功能：

1. 顯示 ETF 持股列表。
2. 可依權重排序。
3. 可依股數增減排序。
4. 可篩選新增、加碼、減碼、持平、出清。
5. 顯示今日與前一日資料日期。
6. 顯示資料是否已更新。

欄位：

| 欄位 | 說明 |
|---|---|
| 排名 | 依權重排序 |
| 個股 | 名稱與股號 |
| 投資比例 | 今日權重 |
| 持有張數 | 股數 / 1000 |
| 比例增減 | 百分點變化 |
| 張數增減 | 股數增減 / 1000 |
| 異動 | 系統分類 |
| 備註 | 比例與股數不一致提示 |

### 11.3 個股搜尋頁

路徑範例：

```text
/stock.html?q=2330
```

功能：

1. 輸入股號或名稱。
2. 顯示此股票被哪些 ETF 持有。
3. 顯示每檔 ETF 的比例、股數、異動。
4. 顯示跨 ETF 統計：持有 ETF 數、平均權重、合計張數、加碼 ETF 數、減碼 ETF 數。
5. 顯示歷史變化，v1.1 可先保留欄位，v1.2 再做圖表。

### 11.4 矩陣比較頁

路徑範例：

```text
/matrix.html
```

功能：

1. 股票 × ETF 持有矩陣。
2. 股票 × ETF 異動矩陣。
3. 可切換顯示：權重、股數、異動文字。
4. 可依持有 ETF 數排序。
5. 可依加碼 ETF 數排序。
6. 可只顯示 AI、半導體、電力、光通訊等主題標籤，v1.1 先保留標籤欄位。

---

## 12. 資料夾結構

建議專案結構：

```text
active-etf-tracker/
├── README.md
├── requirements.txt
├── pyproject.toml                    # 可選
├── config/
│   ├── etfs.json                     # ETF 清單與資料來源設定
│   ├── fields_map.json               # 各來源欄位對照表
│   └── rules.json                    # 分類門檻與訊號規則
├── data/
│   ├── raw/
│   │   └── YYYY-MM-DD/
│   ├── normalized/
│   │   └── YYYY-MM-DD/
│   ├── diff/
│   │   └── YYYY-MM-DD/
│   ├── matrix/
│   │   └── YYYY-MM-DD/
│   ├── rankings/
│   │   └── YYYY-MM-DD/
│   └── search/
│       └── YYYY-MM-DD/
├── scripts/
│   ├── fetch_holdings.py             # 抓取各 ETF 原始資料
│   ├── normalize_holdings.py         # 標準化欄位
│   ├── compute_diff.py               # 計算異動分類
│   ├── build_matrix.py               # 建立跨 ETF 矩陣
│   ├── build_rankings.py             # 建立各排行榜
│   ├── build_search_index.py         # 建立搜尋索引
│   ├── validate_data.py              # 檢查資料品質
│   └── run_daily_local.py            # 本機一鍵執行
├── public/
│   ├── index.html                    # 首頁
│   ├── etf.html                      # 單檔 ETF 頁
│   ├── stock.html                    # 個股搜尋頁
│   ├── matrix.html                   # 矩陣比較頁
│   ├── assets/
│   │   ├── css/
│   │   │   └── style.css
│   │   └── js/
│   │       ├── app.js
│   │       ├── api.js
│   │       ├── table.js
│   │       └── search.js
│   └── data/                         # 打包後給前端讀取的資料
├── tests/
│   ├── test_normalize.py
│   ├── test_diff.py
│   ├── test_matrix.py
│   └── fixtures/
└── docs/
    ├── spec_v1.1.md
    └── data_dictionary.md
```

---

## 13. Python 腳本職責

### 13.1 fetch_holdings.py

責任：

1. 依 `config/etfs.json` 抓取各 ETF 官方持股資料。
2. 儲存到 `data/raw/{data_date}/{etf_code}`。
3. 記錄資料來源狀態。

v1.1 可先支援手動放檔，不一定要完成全部爬蟲。

### 13.2 normalize_holdings.py

責任：

1. 讀取 raw 資料。
2. 統一欄位名稱。
3. 清理逗號、百分比、空白、特殊符號。
4. 拆出股名與股號。
5. 輸出 normalized JSON。

### 13.3 compute_diff.py

責任：

1. 讀取今日與前一有效日期資料。
2. 依股數變化判斷新增、加碼、減碼、出清、持平。
3. 保留原始異動文字。
4. 建立異常提示。

### 13.4 build_matrix.py

責任：

1. 彙總所有 ETF normalized / diff 資料。
2. 建立股票 × ETF 持有矩陣。
3. 建立股票 × ETF 異動矩陣。
4. 計算持有 ETF 數、平均權重、合計張數。

### 13.5 build_rankings.py

責任：

1. 依矩陣建立加碼榜、新增榜、減碼榜、出清榜、持平榜。
2. 套用強力加碼、倒貨警示、核心重倉等規則。
3. 輸出 rankings JSON。

### 13.6 build_search_index.py

責任：

1. 建立股號 / 股名查詢索引。
2. 支援前端模糊搜尋。
3. 支援輸入 `2330`、`台積電`、`台積電(2330)`。

### 13.7 validate_data.py

責任：

1. 檢查 ETF 是否缺資料。
2. 檢查必要欄位是否缺漏。
3. 檢查持股比例是否異常。
4. 檢查股數是否為數字。
5. 檢查同一 ETF 是否有重複股號。
6. 輸出 validation report。

### 13.8 run_daily_local.py

責任：

本機一鍵執行完整流程：

```text
fetch -> normalize -> diff -> matrix -> rankings -> search_index -> copy_to_public
```

---

## 14. 前端技術規格

v1.1 建議使用最簡化的靜態網站：

| 項目 | 建議 |
|---|---|
| 前端 | HTML + CSS + JavaScript |
| 資料 | JSON |
| 本機測試 | Python http.server 或 VS Code Live Server |
| 部署 | GitHub Pages，v1.2 後再接 |
| 圖表 | v1.1 可不做，v1.2 再加 Chart.js |
| CSS | mobile-first |

本機啟動方式：

```bash
cd public
python -m http.server 8000
```

瀏覽器開啟：

```text
http://127.0.0.1:8000
```

---

## 15. UI 設計原則

1. 手機優先。
2. 首頁先給結論，再給表格。
3. 加碼用正向標籤，減碼 / 出清用警示標籤。
4. 每個表格都要可排序。
5. 每個股票名稱都可點入個股搜尋頁。
6. 每個 ETF 代號都可點入單檔 ETF 頁。
7. 資料日期與更新狀態必須明顯顯示。
8. 異常資料不可隱藏，應顯示提示。

---

## 16. 首頁資訊架構

首頁建議排序：

```text
1. 今日資料狀態
2. 今日主動 ETF 共識方向摘要
3. 多檔同步加碼榜
4. 新增持股榜
5. 減碼 / 出清警示榜
6. 最多 ETF 持有榜
7. 個股搜尋
8. ETF 快速入口
```

首頁摘要範例：

```text
資料日期：2026-05-14
已更新 ETF：10 / 11
今日多檔加碼：台積電、欣銓、日月光投控、台燿
今日新進持股：南茂、台表科、文曄
今日減碼警示：金像電、世芯-KY、富世達
```

---

## 17. 個股搜尋規格

### 17.1 搜尋輸入

支援：

1. 股號：`2330`
2. 股名：`台積電`
3. 顯示名稱：`台積電(2330)`
4. 部分字串：`台積`

### 17.2 搜尋結果

單一股票頁需顯示：

1. 股票名稱與股號。
2. 持有 ETF 數。
3. 平均持股比例。
4. 合計持有張數。
5. 今日加碼 ETF 數。
6. 今日減碼 ETF 數。
7. 今日新增 ETF 數。
8. 今日出清 ETF 數。
9. 每檔 ETF 明細。
10. 系統觀察訊號。

---

## 18. ETF 設定檔格式

檔案：

```text
config/etfs.json
```

格式：

```json
{
  "etfs": [
    {
      "etf_code": "00981A",
      "etf_name": "主動 ETF 名稱待補",
      "issuer": "投信名稱待補",
      "enabled": true,
      "priority": 1,
      "source_type": "manual_or_web",
      "source_url": "",
      "parser": "default_csv_parser",
      "note": "v1.1 優先驗證"
    },
    {
      "etf_code": "00403A",
      "etf_name": "待補",
      "issuer": "待補",
      "enabled": false,
      "priority": 2,
      "source_type": "pending",
      "source_url": "",
      "parser": "pending",
      "note": "若尚未有公開持股資料，先保留支援"
    }
  ]
}
```

---

## 19. 規則設定檔格式

檔案：

```text
config/rules.json
```

格式：

```json
{
  "change_rules": {
    "primary_basis": "shares_change",
    "use_weight_change_as_secondary": true
  },
  "ranking_rules": {
    "strong_add_lot_threshold": 500,
    "strong_new_lot_threshold": 500,
    "dump_warning_lot_threshold": 300,
    "core_weight_pct_threshold": 3,
    "crowded_holding_etf_count_threshold": 7,
    "consensus_add_etf_count_threshold": 3
  },
  "display_rules": {
    "decimal_places_weight": 2,
    "decimal_places_lot": 1,
    "show_inconsistent_warning": true
  }
}
```

---

## 20. 資料品質檢查

### 20.1 必要檢查

| 檢查項目 | 規則 |
|---|---|
| ETF 資料是否存在 | 每檔 enabled ETF 應有資料或狀態 |
| 日期是否一致 | data_date 不可空白 |
| 股號是否可解析 | stock_id 不可空白 |
| 權重是否可解析 | weight_pct 應為 number |
| 股數是否可解析 | shares 應為 integer |
| 同一 ETF 是否重複股號 | 不應重複 |
| 異動分類是否有效 | 只允許新增、加碼、減碼、出清、持平 |

### 20.2 警示檢查

| 警示 | 條件 |
|---|---|
| 權重總和異常 | 單檔 ETF 權重總和過高或過低 |
| 股數異常 | 股數小於 0 |
| 比例與股數方向不一致 | shares_change 與 weight_change_pct 方向不同 |
| 官方異動與系統異動不一致 | source_change_text != system_change_type |
| 資料日期未更新 | 今日抓到昨日以前資料 |

---

## 21. 本機開發流程

### 21.1 第一階段：資料樣板與假資料

1. 建立資料夾結構。
2. 建立 `config/etfs.json`。
3. 建立 `config/rules.json`。
4. 建立 00981A 範例 normalized JSON。
5. 建立前端可讀取 JSON 的首頁。

驗收：

```text
http://127.0.0.1:8000 可顯示 00981A 持股資料
```

### 21.2 第二階段：使用已整理資料

1. 將目前已有的單檔持股清單轉成 normalized JSON。
2. 將加碼榜、新增榜、減碼榜、出清榜、持平榜轉成 rankings JSON。
3. 前端顯示首頁排行榜。

驗收：

```text
首頁可顯示加碼榜 / 新增榜 / 減碼榜 / 出清榜 / 持平榜
```

### 21.3 第三階段：建立矩陣

1. 建立 holding_matrix.json。
2. 建立 change_matrix.json。
3. 建立 matrix.html。
4. 可依持有 ETF 數排序。
5. 可依加碼 ETF 數排序。

驗收：

```text
可看出台積電、台光電、智邦等被幾檔 ETF 持有
```

### 21.4 第四階段：建立個股搜尋

1. 建立 stock_index.json。
2. 建立 stock.html。
3. 支援股號 / 股名搜尋。
4. 搜尋結果顯示所有 ETF 持有與異動。

驗收：

```text
搜尋 2330 可看到台積電被哪些 ETF 持有與異動
```

### 21.5 第五階段：接真實資料

1. 逐一確認各 ETF 官方持股來源。
2. 先支援手動下載 / 貼上檔案。
3. 再逐步加入爬蟲。
4. 每次抓取後先進 raw，再轉 normalized。

驗收：

```text
新日期資料可被完整轉換，並與前一有效日期比較
```

---

## 22. 後續 GitHub Actions 規劃，v1.2 以後

v1.1 不先接 GitHub Actions，但保留設計。

未來流程：

```text
每日排程
  -> 抓取 ETF 官方資料
  -> 標準化
  -> 計算異動
  -> 產生矩陣
  -> 產生排行榜
  -> 產生搜尋索引
  -> 更新 public/data
  -> commit & push
  -> GitHub Pages 自動更新
```

建議排程：

```yaml
schedule:
  - cron: "30 10 * * 1-5"
```

台灣時間約 18:30 執行。實際時間需依各 ETF 公布時間調整。

---

## 23. MVP 驗收標準

v1.1 MVP 完成時，應滿足：

1. 本機可用 `127.0.0.1` 開啟網站。
2. 首頁可顯示資料日期與更新狀態。
3. 首頁可顯示加碼榜、新增榜、減碼榜、出清榜、持平榜。
4. 單檔 ETF 頁可查看 00981A 持股明細。
5. 矩陣頁可查看股票被幾檔 ETF 持有。
6. 個股搜尋可搜尋 2330 / 台積電。
7. 系統異動分類以股數變化為準。
8. 若比例與股數方向不一致，前端可顯示提示。
9. 資料與前端分離，前端只讀 JSON。
10. 不依賴後端伺服器即可瀏覽。

---

## 24. v1.1 風險與待確認事項

### 24.1 資料來源風險

不同投信的資料格式可能不同，可能有：

1. HTML 表格。
2. CSV。
3. Excel。
4. PDF。
5. JavaScript 動態載入。
6. 公布時間不一致。

處理方式：

1. 先手動資料匯入。
2. 再為每個 ETF 建立 parser。
3. 保留 raw 檔案方便除錯。

### 24.2 ETF 名單變動風險

新 ETF 上市或代號異動時，需更新：

```text
config/etfs.json
```

### 24.3 權重與股數衝突

系統以股數為主，但仍需顯示權重變化，避免漏看淨值或價格造成的權重變化。

### 24.4 交易解讀風險

主動 ETF 加碼不一定代表股價會上漲，可能只是再平衡、規模變化、產業配置調整或短期操作。

---

## 25. v1.2 延伸方向

1. 歷史趨勢圖。
2. 個股被 ETF 持有比例時間序列。
3. ETF 加碼與股價報酬對照。
4. ETF 加碼與三大法人買賣超對照。
5. ETF 擁擠持股風險指標。
6. 主題分類：AI、ASIC、CPO、電力、散熱、ABF、IC 設計、金融、傳產。
7. 主動 ETF 與被動 ETF 比較。
8. 匯出 CSV / Excel。
9. GitHub Actions 自動更新。
10. 每日自動產生 Markdown 報告。

---

## 26. v1.3 延伸方向

1. 建立「主動 ETF 過度反應追蹤模型」。
2. 加入股價、成交量、法人買賣超。
3. 建立 ETF 買盤與股價反應的事件研究。
4. 建立過熱 / 退潮訊號。
5. 建立產業鏈主題 Dashboard。
6. 加入 AI 摘要：每日 ETF 資金流向解讀。

---

## 27. 開發優先順序建議

建議順序：

```text
1. 規格固定
2. JSON schema 固定
3. 00981A 單檔頁完成
4. 排行榜首頁完成
5. 跨 ETF 矩陣完成
6. 個股搜尋完成
7. 接入更多 ETF
8. 接真實資料來源
9. 本機穩定後再接 GitHub Pages
10. 最後再接 GitHub Actions
```

---

## 28. 總結

v1.1 的核心精神：

```text
先把資料標準化，再做異動分類；
先讓本機網站穩定，再接自動化；
先做持股雷達，再做交易模型。
```

本規格書可作為下一步開始寫程式的依據。
