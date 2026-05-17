const icons = {
  grid: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z"/></svg>',
  up: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 16l6-6 4 4 6-8"/><path d="M15 6h5v5"/></svg>',
  plus: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 5v14M5 12h14"/></svg>',
  down: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 8l6 6 4-4 6 8"/><path d="M15 18h5v-5"/></svg>',
  exit: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M9 5H5v14h4"/><path d="M13 8l4 4-4 4M17 12H8"/></svg>',
  equal: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 9h14M5 15h14"/></svg>',
  database: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M5 7c0-2 14-2 14 0v10c0 2-14 2-14 0z"/><path d="M5 7c0 2 14 2 14 0M5 12c0 2 14 2 14 0"/></svg>',
  refresh: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M20 6v5h-5"/><path d="M4 18v-5h5"/><path d="M19 11a7 7 0 0 0-12-4M5 13a7 7 0 0 0 12 4"/></svg>',
  edit: '<svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 20h5l10-10-5-5L4 15z"/><path d="M13 6l5 5"/></svg>',
};

const rankTabs = [
  ["most_held_rank", "持有總覽", "grid"],
  ["add_rank", "加碼榜", "up"],
  ["new_rank", "新增榜", "plus"],
  ["reduce_rank", "減碼榜", "down"],
  ["removed_rank", "出清榜", "exit"],
  ["unchanged_rank", "持平榜", "equal"],
];

const rankHints = {
  most_held_rank: "依持有 ETF 數排序，觀察主動 ETF 集中持有的股票。",
  add_rank: "依加碼 ETF 數與張數變化排序，觀察共識升溫。",
  new_rank: "觀察近期新進入 ETF 持股的股票。",
  reduce_rank: "觀察被多檔 ETF 減碼的股票。",
  removed_rank: "觀察已被 ETF 移出的股票。",
  unchanged_rank: "觀察仍被多檔 ETF 續抱的核心部位。",
};

let state = {
  manifest: null,
  rankings: null,
  searchRows: [],
  etfs: [],
  history: null,
  dates: [],
  selectedDate: "",
  compareStart: "",
  compareEnd: "",
};

function setText(id, value) {
  const el = document.getElementById(id);
  if (el) el.textContent = value;
}

function icon(name) {
  return icons[name] || icons.grid;
}

function rowStockLink(row) {
  return `<a href="stock.html?q=${encodeURIComponent(row.stock_id || row.stock_display)}"><strong>${row.stock_display}</strong></a>`;
}

function fillDateSelect(select, dates, selected) {
  select.innerHTML = dates.map((date) => `<option value="${date}" ${date === selected ? "selected" : ""}>${date}</option>`).join("");
}

function previousTradingDate(date) {
  const index = state.dates.indexOf(date);
  return index > 0 ? state.dates[index - 1] : state.dates[0] || date;
}

function refreshDateControls() {
  const latest = state.dates[state.dates.length - 1] || state.manifest.data_date;
  state.selectedDate = state.selectedDate || latest;
  state.compareEnd = state.compareEnd || state.selectedDate;
  state.compareStart = state.compareStart || previousTradingDate(state.compareEnd);
  fillDateSelect(document.getElementById("dataDateSelect"), state.dates, state.selectedDate);
  fillDateSelect(document.getElementById("compareStartSelect"), state.dates, state.compareStart);
  fillDateSelect(document.getElementById("compareEndSelect"), state.dates, state.compareEnd);
  setText("compareRange", `${state.compareStart} → ${state.compareEnd}`);
}

function renderTable(rows, columns) {
  const content = document.getElementById("dashboardContent");
  if (!rows.length) {
    content.innerHTML = '<div class="empty">目前沒有資料</div>';
    return;
  }
  content.innerHTML = `
    <div class="table-wrap">
      <table data-sortable>
        <thead><tr>${columns.map(([label]) => `<th>${label}</th>`).join("")}</tr></thead>
        <tbody>
          ${rows
            .slice(0, 120)
            .map((row) => `<tr>${columns.map(([, render, key]) => `<td data-value="${key ? row[key] ?? "" : ""}">${render(row)}</td>`).join("")}</tr>`)
            .join("")}
        </tbody>
      </table>
    </div>`;
  ETF.enableTableSorting(content);
}

function columnsForRank(key) {
  const cols = {
    most_held_rank: [
      ["個股", rowStockLink],
      ["持有 ETF", (row) => row.held_etf_count, "held_etf_count"],
      ["平均比例", (row) => `${ETF.formatNumber(row.avg_weight_pct, 2)}%`, "avg_weight_pct"],
      ["合計張數", (row) => ETF.formatNumber(row.total_lots, 1), "total_lots"],
    ],
    add_rank: [
      ["個股", rowStockLink],
      ["加碼 ETF", (row) => row.add_etf_count, "add_etf_count"],
      ["平均比例", (row) => `${ETF.formatNumber(row.avg_weight_pct, 2)}%`, "avg_weight_pct"],
      ["加碼張數", (row) => ETF.formatNumber(row.total_shares_change_lot, 1), "total_shares_change_lot"],
      ["訊號", (row) => row.flag_text || ""],
    ],
    new_rank: [
      ["個股", rowStockLink],
      ["新增 ETF", (row) => row.new_etf_count ?? "-"],
      ["張數變化", (row) => ETF.formatNumber(row.total_shares_change_lot, 1), "total_shares_change_lot"],
      ["訊號", (row) => row.flag_text || ""],
    ],
    reduce_rank: [
      ["個股", rowStockLink],
      ["減碼 ETF", (row) => row.reduce_etf_count, "reduce_etf_count"],
      ["股數變化", (row) => ETF.formatNumber(row.total_shares_change), "total_shares_change"],
      ["張數變化", (row) => ETF.formatNumber(row.total_shares_change_lot, 1), "total_shares_change_lot"],
      ["訊號", (row) => row.flag_text || ""],
    ],
    removed_rank: [
      ["個股", rowStockLink],
      ["出清 ETF", (row) => row.removed_etf_count, "removed_etf_count"],
    ],
    unchanged_rank: [
      ["個股", rowStockLink],
      ["持平 ETF", (row) => row.unchanged_etf_count, "unchanged_etf_count"],
      ["平均比例", (row) => `${ETF.formatNumber(row.avg_weight_pct, 2)}%`, "avg_weight_pct"],
      ["訊號", (row) => row.flag_text || ""],
    ],
  };
  return cols[key] || cols.most_held_rank;
}

function activateRank(key) {
  document.querySelectorAll("[data-rank]").forEach((button) => button.classList.toggle("is-active", button.dataset.rank === key));
  const label = rankTabs.find(([rankKey]) => rankKey === key)?.[1] || "排行榜";
  setText("panelTitle", label);
  setText("viewTitle", label);
  setText("panelHint", `${rankHints[key] || ""} 實際比較區間：${state.compareStart} → ${state.compareEnd}`);
  renderTable(state.rankings[key] || [], columnsForRank(key));
  closeMobileSidebar();
}

function setupRankNav() {
  const nav = document.getElementById("rankNav");
  nav.innerHTML = rankTabs
    .map(
      ([key, label, iconName], index) => `
        <button class="nav-item ${index === 0 ? "is-active" : ""}" type="button" data-rank="${key}" data-tooltip="${label}" title="${label}">
          <span class="nav-svg">${icon(iconName)}</span>
          <span>${label}</span>
        </button>`,
    )
    .join("");
  nav.addEventListener("click", (event) => {
    const button = event.target.closest("[data-rank]");
    if (button) activateRank(button.dataset.rank);
  });
}

function findStock(query) {
  const normalized = String(query || "").trim().toLowerCase();
  if (!normalized) return null;
  return state.searchRows.find((row) => row.keywords.some((keyword) => String(keyword).toLowerCase().includes(normalized)));
}

function renderStock(row) {
  setText("viewTitle", row.stock_display);
  setText("panelTitle", row.stock_display);
  setText("panelHint", `加碼 ${row.add_count} / 減碼 ${row.reduce_count} / 新增 ${row.new_count} / 出清 ${row.removed_count}`);
  const rows = Object.entries(row.etfs).sort(([a], [b]) => a.localeCompare(b)).map(([code, item]) => ({ code, ...item }));
  renderTable(rows, [
    ["ETF 代號", (item) => ETF.etfLink(item.code), "code"],
    ["比例", (item) => `${ETF.formatNumber(item.weight_pct, 2)}%`, "weight_pct"],
    ["持有張數", (item) => ETF.formatNumber(item.shares_lot, 1), "shares_lot"],
    ["比例增減", (item) => `${ETF.formatSigned(item.weight_change_pct, 2)}%`, "weight_change_pct"],
    ["張數增減", (item) => ETF.formatSigned(item.shares_change_lot, 1), "shares_change_lot"],
    ["異動", (item) => ETF.makeBadge(item.change_type), "change_type"],
  ]);
  closeMobileSidebar();
}

async function renderEtf(code) {
  const payload = await ETF.fetchJson(`${code}.json`);
  const holdings = payload.holdings || [];
  setText("viewTitle", `${code} ETF 明細`);
  setText("panelTitle", `${code} ETF 明細`);
  setText("panelHint", `持股 ${holdings.length} 檔；資料日 ${payload.meta?.data_date || state.manifest.data_date}`);
  renderTable(holdings, [
    ["個股", rowStockLink],
    ["比例", (row) => `${ETF.formatNumber(row.weight_pct, 2)}%`, "weight_pct"],
    ["持有張數", (row) => ETF.formatNumber(row.shares_lot, 1), "shares_lot"],
    ["比例增減", (row) => `${ETF.formatSigned(row.weight_change_pct, 2)}%`, "weight_change_pct"],
    ["張數增減", (row) => ETF.formatSigned(row.shares_change_lot, 1), "shares_change_lot"],
    ["異動", (row) => ETF.makeBadge(row.system_change_type), "system_change_type"],
  ]);
  closeMobileSidebar();
}

function renderDataView() {
  setText("viewTitle", "數據資料");
  setText("panelTitle", "數據資料");
  setText("panelHint", "目前公開資料與本機已保存的有效資料日。");
  document.getElementById("dashboardContent").innerHTML = `
    <div class="data-grid">
      <div class="data-card"><span>目前選擇資料日</span><strong>${state.selectedDate}</strong></div>
      <div class="data-card"><span>最近資料日</span><strong>${state.dates[state.dates.length - 1] || state.manifest.data_date}</strong></div>
      <div class="data-card"><span>可選資料日</span><strong>${state.dates.join("、")}</strong></div>
      <div class="data-card"><span>比較期間</span><strong>${state.compareStart} → ${state.compareEnd}</strong></div>
      <div class="data-card"><span>歷史資料量</span><strong>${state.dates.length} 個有效資料日</strong></div>
      <div class="data-card"><span>提醒</span><strong>若只有少數資料日，加碼/新增/減碼/出清/持平的趨勢解讀會偏短期。</strong></div>
    </div>`;
  closeMobileSidebar();
}

function renderUpdateView() {
  const savedTime = localStorage.getItem("activeEtfUpdateTime") || "18:30";
  setText("viewTitle", "數據更新");
  setText("panelTitle", "數據更新");
  setText("panelHint", "靜態網頁無法直接執行 Python；此區先提供本機指令與雲端排程設定草稿。");
  document.getElementById("dashboardContent").innerHTML = `
    <div class="update-panel">
      <button class="primary-button" id="manualUpdateButton" type="button">產生手動更新指令</button>
      <pre id="manualUpdateCommand" class="command-box">python scripts\\run_daily_auto.py --no-discover</pre>
      <div class="schedule-row">
        <label><span>自動更新時間</span><input id="autoUpdateTime" type="time" value="${savedTime}" /></label>
        <button class="primary-button" id="saveScheduleButton" type="button">儲存時間</button>
      </div>
      <pre id="scheduleHint" class="command-box">GitHub Actions cron 需換算 UTC；台灣 ${savedTime} 約為 UTC ${toUtcTime(savedTime)}。</pre>
    </div>`;
  document.getElementById("manualUpdateButton").addEventListener("click", () => {
    document.getElementById("manualUpdateCommand").textContent = [
      "python scripts\\run_daily_auto.py --no-discover",
      "python scripts\\rebuild_history.py",
      "python -m http.server 8000 -d public",
    ].join("\n");
  });
  document.getElementById("saveScheduleButton").addEventListener("click", () => {
    const value = document.getElementById("autoUpdateTime").value || "18:30";
    localStorage.setItem("activeEtfUpdateTime", value);
    document.getElementById("scheduleHint").textContent = `已儲存 ${value}。GitHub Actions cron 需換算 UTC；台灣 ${value} 約為 UTC ${toUtcTime(value)}。`;
  });
  closeMobileSidebar();
}

function toUtcTime(taipeiTime) {
  const [hour, minute] = taipeiTime.split(":").map(Number);
  const utcHour = (hour + 16) % 24;
  return `${String(utcHour).padStart(2, "0")}:${String(minute || 0).padStart(2, "0")}`;
}

function renderLogView() {
  setText("viewTitle", "開發日誌");
  setText("panelTitle", "開發日誌");
  setText("panelHint", "記錄近期功能調整與資料處理規則。");
  document.getElementById("dashboardContent").innerHTML = `
    <div class="log-list">
      <article><time>2026-05-17</time><strong>修正 dashboard 側欄</strong><p>收合按鈕移到收合欄內置中，icon-only 狀態加入提示文字。</p></article>
      <article><time>2026-05-17</time><strong>加入日期與區間控制</strong><p>資料日與比較起迄日改為使用本機有效資料日，不用週末或一般日曆日比較。</p></article>
      <article><time>2026-05-17</time><strong>新增數據更新頁</strong><p>提供手動更新指令與自動更新時間設定草稿，後續可接 GitHub Actions。</p></article>
    </div>`;
  closeMobileSidebar();
}

function setupSystemNav() {
  document.querySelectorAll("[data-view]").forEach((item) => {
    item.querySelector(".nav-svg").innerHTML = icon(item.querySelector(".nav-svg").dataset.icon);
  });
  window.addEventListener("hashchange", renderHashView);
}

function renderHashView() {
  const view = window.location.hash.replace("#", "");
  if (view === "data") renderDataView();
  if (view === "update") renderUpdateView();
  if (view === "log") renderLogView();
}

function setupSelectors() {
  const etfSelect = document.getElementById("etfSelect");
  const stockSelect = document.getElementById("stockSelect");
  etfSelect.innerHTML = state.etfs.map((item) => `<option value="${item.etf_code}">${item.etf_code} ${item.etf_name || ""}</option>`).join("");
  stockSelect.innerHTML = state.searchRows
    .slice()
    .sort((a, b) => b.held_etf_count - a.held_etf_count)
    .slice(0, 120)
    .map((row) => `<option value="${row.stock_id}">${row.stock_display}</option>`)
    .join("");

  document.getElementById("etfSearchButton").addEventListener("click", () => {
    const value = document.getElementById("etfInput").value.trim() || etfSelect.value;
    if (value) renderEtf(value.toUpperCase());
  });
  document.getElementById("stockSearchButton").addEventListener("click", () => {
    const value = document.getElementById("stockInput").value.trim() || stockSelect.value;
    const stock = findStock(value);
    if (stock) renderStock(stock);
  });
  document.getElementById("applyDateButton").addEventListener("click", () => {
    state.selectedDate = document.getElementById("dataDateSelect").value;
    state.compareStart = document.getElementById("compareStartSelect").value;
    state.compareEnd = document.getElementById("compareEndSelect").value;
    if (state.compareStart > state.compareEnd) {
      [state.compareStart, state.compareEnd] = [state.compareEnd, state.compareStart];
    }
    refreshDateControls();
    setText("viewHint", `使用有效資料日：${state.selectedDate}；比較區間：${state.compareStart} → ${state.compareEnd}`);
    if (window.location.hash === "#data") renderDataView();
  });
}

function setupSidebar() {
  const shell = document.getElementById("dashboardShell");
  document.getElementById("collapseButton").addEventListener("click", () => shell.classList.toggle("is-collapsed"));
  document.getElementById("mobileMenuButton").addEventListener("click", () => shell.classList.add("is-mobile-open"));
  document.getElementById("sidebarBackdrop").addEventListener("click", closeMobileSidebar);
}

function closeMobileSidebar() {
  document.getElementById("dashboardShell").classList.remove("is-mobile-open");
}

async function initDashboard() {
  const [manifest, rankingsPayload, searchPayload, etfPayload, historyPayload] = await Promise.all([
    ETF.fetchJson("manifest.json"),
    ETF.fetchJson("rankings.json"),
    ETF.fetchJson("stock_index.json"),
    ETF.fetchJson("etfs.json"),
    ETF.fetchJson("stock_history.json").catch(() => null),
  ]);
  const dates = historyPayload?.meta?.available_dates || historyPayload?.meta?.dates || [manifest.data_date];
  state = {
    manifest,
    rankings: rankingsPayload.rankings,
    searchRows: searchPayload.rows,
    etfs: (etfPayload.etfs || []).filter((item) => item.enabled !== false && item.source_status === "updated"),
    history: historyPayload,
    dates,
    selectedDate: dates[dates.length - 1] || manifest.data_date,
    compareEnd: dates[dates.length - 1] || manifest.data_date,
    compareStart: dates.length > 1 ? dates[dates.length - 2] : dates[0] || manifest.data_date,
  };
  setText("etfCount", state.etfs.length);
  setText("stockCount", searchPayload.meta.stock_count);
  setText("addCount", rankingsPayload.rankings.add_rank.length);
  refreshDateControls();
  setupSidebar();
  setupRankNav();
  setupSystemNav();
  setupSelectors();
  if (window.location.hash) {
    renderHashView();
  } else {
    activateRank("most_held_rank");
  }
}

initDashboard().catch((error) => {
  document.getElementById("dashboardContent").innerHTML = `<div class="empty">${error.message}</div>`;
});
