const tabs = [
  ["most_held_rank", "持有總覽"],
  ["add_rank", "加碼榜"],
  ["new_rank", "新增榜"],
  ["reduce_rank", "減碼榜"],
  ["removed_rank", "出清榜"],
  ["unchanged_rank", "持平榜"],
];

const rankingHints = {
  most_held_rank: "依持有 ETF 數排序，快速看哪些個股被主動式 ETF 集中持有。",
  add_rank: "依加碼基金數與合計加碼張數排序。",
  new_rank: "新進持有名單，觀察近期新增進入 ETF 的個股。",
  reduce_rank: "減碼名單，呈現合計股數與張數變化。",
  removed_rank: "出清名單，追蹤已被 ETF 移出的個股。",
  unchanged_rank: "持平名單，觀察仍被多檔 ETF 續抱的核心部位。",
};

function rankingColumns(key) {
  const cols = {
    add_rank: [
      ["個股", (row) => ETF.stockLink(row)],
      ["加碼 ETF", (row) => row.add_etf_count, "add_etf_count"],
      ["平均比例", (row) => `${ETF.formatNumber(row.avg_weight_pct, 2)}%`, "avg_weight_pct"],
      ["合計加碼張數", (row) => ETF.formatNumber(row.total_shares_change_lot, 1), "total_shares_change_lot"],
      ["提示", (row) => row.flag_text || ""],
    ],
    new_rank: [
      ["個股", (row) => ETF.stockLink(row)],
      ["合計比例", (row) => `${ETF.formatNumber(row.total_weight_pct, 2)}%`, "total_weight_pct"],
      ["合計股數", (row) => ETF.formatNumber(row.total_shares), "total_shares"],
      ["張數增減", (row) => ETF.formatNumber(row.total_shares_change_lot, 1), "total_shares_change_lot"],
      ["提示", (row) => row.flag_text || ""],
    ],
    reduce_rank: [
      ["個股", (row) => ETF.stockLink(row)],
      ["合計比例", (row) => `${ETF.formatNumber(row.total_weight_pct, 2)}%`, "total_weight_pct"],
      ["股數增減", (row) => ETF.formatNumber(row.total_shares_change), "total_shares_change"],
      ["張數增減", (row) => ETF.formatNumber(row.total_shares_change_lot, 1), "total_shares_change_lot"],
      ["提示", (row) => row.flag_text || ""],
    ],
    removed_rank: [
      ["個股", (row) => ETF.stockLink(row)],
      ["出清 ETF", (row) => row.removed_etf_count, "removed_etf_count"],
    ],
    unchanged_rank: [
      ["個股", (row) => ETF.stockLink(row)],
      ["續抱 ETF", (row) => row.unchanged_etf_count, "unchanged_etf_count"],
      ["平均比例", (row) => `${ETF.formatNumber(row.avg_weight_pct, 2)}%`, "avg_weight_pct"],
      ["合計張數", (row) => ETF.formatNumber(row.total_lots, 1), "total_lots"],
      ["提示", (row) => row.flag_text || ""],
    ],
    most_held_rank: [
      ["個股", (row) => ETF.stockLink(row)],
      ["持有 ETF", (row) => row.held_etf_count, "held_etf_count"],
      ["平均比例", (row) => `${ETF.formatNumber(row.avg_weight_pct, 2)}%`, "avg_weight_pct"],
      ["合計張數", (row) => ETF.formatNumber(row.total_lots, 1), "total_lots"],
    ],
  };
  return cols[key];
}

function renderTable(container, rows, columns) {
  if (!rows.length) {
    container.innerHTML = '<div class="empty">目前沒有資料</div>';
    return;
  }
  container.innerHTML = `
    <div class="table-wrap">
      <table data-sortable>
        <thead><tr>${columns.map(([label]) => `<th>${label}</th>`).join("")}</tr></thead>
        <tbody>
          ${rows
            .slice(0, 80)
            .map(
              (row) => `<tr>${columns
                .map(([, renderer, key]) => `<td data-value="${key ? row[key] ?? "" : ""}">${renderer(row)}</td>`)
                .join("")}</tr>`,
            )
            .join("")}
        </tbody>
      </table>
    </div>`;
  ETF.enableTableSorting(container);
}

function setContentTitle(title, hint) {
  ETF.setText("contentTitle", title);
  ETF.setText("contentHint", hint);
}

function clearEtfActive() {
  document.querySelectorAll("[data-etf]").forEach((button) => button.classList.remove("is-active"));
}

function clearRankActive() {
  document.querySelectorAll("[data-rank]").forEach((button) => button.classList.remove("is-active"));
}

function renderRankingTabs(rankings) {
  const tabBar = document.getElementById("rankTabs");
  const table = document.getElementById("rankingTable");
  tabBar.innerHTML = tabs.map(([key, label], index) => `<button class="chip ${index === 0 ? "is-active" : ""}" data-rank="${key}">${label}</button>`).join("");

  function activate(key) {
    clearEtfActive();
    tabBar.querySelectorAll(".chip").forEach((button) => button.classList.toggle("is-active", button.dataset.rank === key));
    setContentTitle(tabs.find(([tabKey]) => tabKey === key)?.[1] || "今日排行榜", rankingHints[key] || "");
    renderTable(table, rankings[key] || [], rankingColumns(key));
  }

  tabBar.addEventListener("click", (event) => {
    const button = event.target.closest("[data-rank]");
    if (button) activate(button.dataset.rank);
  });
  activate("most_held_rank");
}

function findStock(rows, query) {
  const normalized = query.trim().toLowerCase();
  if (!normalized) return null;
  return rows.find((row) => row.keywords.some((keyword) => String(keyword).toLowerCase().includes(normalized)));
}

function renderStockResult(row) {
  const table = document.getElementById("rankingTable");
  clearEtfActive();
  clearRankActive();
  setContentTitle(row.stock_display, `加碼 ${row.add_count} / 減碼 ${row.reduce_count} / 新增 ${row.new_count} / 出清 ${row.removed_count}`);
  const rows = Object.entries(row.etfs)
    .sort(([a], [b]) => a.localeCompare(b))
    .map(([code, item]) => ({ code, ...item }));
  renderTable(table, rows, [
    ["ETF 代號", (item) => ETF.etfLink(item.code), "code"],
    ["比例", (item) => `${ETF.formatNumber(item.weight_pct, 2)}%`, "weight_pct"],
    ["持有張數", (item) => ETF.formatNumber(item.shares_lot, 1), "shares_lot"],
    ["比例增減", (item) => `${ETF.formatSigned(item.weight_change_pct, 2)}%`, "weight_change_pct"],
    ["張數增減", (item) => ETF.formatSigned(item.shares_change_lot, 1), "shares_change_lot"],
    ["異動", (item) => ETF.makeBadge(item.change_type), "change_type"],
    ["備註", (item) => item.note || ""],
  ]);
}

function setupSearch(searchRows) {
  const select = document.getElementById("stockSelect");
  const input = document.getElementById("stockInput");
  const button = document.getElementById("searchButton");
  select.innerHTML = searchRows
    .sort((a, b) => b.held_etf_count - a.held_etf_count)
    .slice(0, 80)
    .map((row) => `<option value="${row.stock_id}">${row.stock_display}</option>`)
    .join("");

  const go = () => {
    const value = input.value.trim() || select.value;
    const stock = findStock(searchRows, value);
    if (stock) {
      renderStockResult(stock);
    } else {
      document.getElementById("rankingTable").innerHTML = '<div class="empty">找不到符合的個股</div>';
      setContentTitle("查詢結果", `未找到：${value}`);
    }
  };
  button.addEventListener("click", go);
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter") go();
  });
}

function renderEtfs(etfPayload) {
  const etfs = (etfPayload.etfs || []).filter((item) => item.enabled !== false && item.source_status === "updated");
  ETF.setText("etfCount", etfs.length);
  const grid = document.getElementById("etfGrid");
  grid.innerHTML = etfs
    .map((item) => {
      const issuer = item.issuer || (item.etf_name && item.etf_name !== item.etf_code ? item.etf_name.replace(/^主動/, "").slice(0, 2) : "");
      const featured = item.etf_code === "00982A" || item.etf_code === "00981A" ? " is-featured" : "";
      return `<button class="etf-link${featured}" type="button" data-etf="${item.etf_code}">${item.etf_code}${issuer ? ` ${issuer}` : ""}</button>`;
    })
    .join("");
  grid.addEventListener("click", async (event) => {
    const button = event.target.closest("[data-etf]");
    if (!button) return;
    const code = button.dataset.etf;
    clearRankActive();
    grid.querySelectorAll("[data-etf]").forEach((item) => item.classList.toggle("is-active", item.dataset.etf === code));
    const payload = await ETF.fetchJson(`${code}.json`);
    const holdings = payload.holdings || [];
    setContentTitle(`${code} ETF 明細`, `持股 ${holdings.length} 檔；可點欄位排序。`);
    renderTable(document.getElementById("rankingTable"), holdings, [
      ["個股", (row) => ETF.stockLink(row)],
      ["比例", (row) => `${ETF.formatNumber(row.weight_pct, 2)}%`, "weight_pct"],
      ["持有張數", (row) => ETF.formatNumber(row.shares_lot, 1), "shares_lot"],
      ["比例增減", (row) => `${ETF.formatSigned(row.weight_change_pct, 2)}%`, "weight_change_pct"],
      ["張數增減", (row) => ETF.formatSigned(row.shares_change_lot, 1), "shares_change_lot"],
      ["異動", (row) => ETF.makeBadge(row.system_change_type), "system_change_type"],
      ["備註", (row) => row.note || ""],
    ]);
  });
}

async function init() {
  const [manifest, rankingsPayload, searchPayload, etfPayload] = await Promise.all([
    ETF.fetchJson("manifest.json"),
    ETF.fetchJson("rankings.json"),
    ETF.fetchJson("stock_index.json"),
    ETF.fetchJson("etfs.json"),
  ]);
  ETF.setText("dataDate", manifest.data_date);
  ETF.setText("stockCount", searchPayload.meta.stock_count);
  ETF.setText("addCount", rankingsPayload.rankings.add_rank.length);
  ETF.setText("newCount", rankingsPayload.rankings.new_rank.length);
  ETF.setText("crowdedCount", rankingsPayload.rankings.crowded_holding_rank.length);
  renderEtfs(etfPayload);
  renderRankingTabs(rankingsPayload.rankings);
  setupSearch(searchPayload.rows);
}

init().catch((error) => {
  document.getElementById("rankingTable").innerHTML = `<div class="empty">${error.message}</div>`;
});
