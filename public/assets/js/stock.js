function findStock(rows, query) {
  const normalized = query.trim().toLowerCase();
  return rows.find((row) => row.keywords.some((keyword) => String(keyword).toLowerCase().includes(normalized)));
}

function renderStock(row) {
  ETF.setText("stockTitle", row.stock_display);
  ETF.setText("heldEtfCount", row.held_etf_count);
  ETF.setText("avgWeight", `${ETF.formatNumber(row.avg_weight_pct, 2)}%`);
  ETF.setText("totalLots", ETF.formatNumber(row.total_lots, 1));
  ETF.setText("changeSummary", `加碼 ${row.add_count} / 減碼 ${row.reduce_count} / 新增 ${row.new_count} / 出清 ${row.removed_count}`);

  const entries = Object.entries(row.etfs).sort(([a], [b]) => a.localeCompare(b));
  document.getElementById("stockTable").innerHTML = `
    <div class="table-wrap">
      <table data-sortable>
        <thead><tr><th>ETF 代號</th><th>比例</th><th>持有張數</th><th>比例增減</th><th>張數增減</th><th>異動</th><th>備註</th></tr></thead>
        <tbody>
          ${entries
            .map(
              ([code, item]) => `
                <tr>
                  <td>${ETF.etfLink(code)}</td>
                  <td data-value="${item.weight_pct}">${ETF.formatNumber(item.weight_pct, 2)}%</td>
                  <td data-value="${item.shares_lot}">${ETF.formatNumber(item.shares_lot, 1)}</td>
                  <td data-value="${item.weight_change_pct}">${ETF.formatSigned(item.weight_change_pct, 2)}%</td>
                  <td data-value="${item.shares_change_lot}">${ETF.formatSigned(item.shares_change_lot, 1)}</td>
                  <td>${ETF.makeBadge(item.change_type)}</td>
                  <td class="warning-note">${item.note || ""}</td>
                </tr>`,
            )
            .join("")}
        </tbody>
      </table>
    </div>`;
  ETF.enableTableSorting(document.getElementById("stockTable"));
}

function pointScale(points, width, height, padding) {
  const values = points.map((point) => Number(point.total_lots || 0));
  const min = Math.min(...values);
  const max = Math.max(...values);
  const span = max - min || 1;
  return points.map((point, index) => {
    const x = padding + (points.length === 1 ? 0 : (index * (width - padding * 2)) / (points.length - 1));
    const y = height - padding - ((Number(point.total_lots || 0) - min) / span) * (height - padding * 2);
    return { ...point, x, y };
  });
}

function renderHistory(stockHistory, fromDate, toDate) {
  const chart = document.getElementById("historyChart");
  const compareBox = document.getElementById("rangeCompare");
  if (!stockHistory || !stockHistory.history || stockHistory.history.length === 0) {
    chart.innerHTML = '<div class="empty">尚無歷史曲線資料</div>';
    compareBox.innerHTML = "";
    ETF.setText("historySummary", "尚無可比較的歷史快照");
    return;
  }

  const points = pointScale(stockHistory.history, 680, 220, 30);
  const path = points.map((point) => `${point.x},${point.y}`).join(" ");
  ETF.setText("historySummary", `${points[0].date} 至 ${points[points.length - 1].date}`);
  chart.innerHTML = `
    <svg class="history-svg" viewBox="0 0 680 220" role="img" aria-label="近 5 個交易日持股張數變化">
      <polyline class="history-line" points="${path}" />
      ${points
        .map(
          (point) => `
            <g>
              <circle class="history-dot" cx="${point.x}" cy="${point.y}" r="4"></circle>
              <text x="${point.x}" y="206" text-anchor="middle">${point.date.slice(5)}</text>
              <text x="${point.x}" y="${Math.max(18, point.y - 10)}" text-anchor="middle">${ETF.formatNumber(point.total_lots, 1)}</text>
            </g>`,
        )
        .join("")}
    </svg>`;

  const start = fromDate || points[0].date;
  const end = toDate || points[points.length - 1].date;
  const startPoint = stockHistory.history.find((point) => point.date === start) || stockHistory.history[0];
  const endPoint = stockHistory.history.find((point) => point.date === end) || stockHistory.history[stockHistory.history.length - 1];
  const lotsChange = Number(endPoint.total_lots || 0) - Number(startPoint.total_lots || 0);
  const weightChange = Number(endPoint.avg_weight_pct || 0) - Number(startPoint.avg_weight_pct || 0);
  compareBox.innerHTML = `
    <div class="compare-stat"><strong>${startPoint.date}</strong><span>${ETF.formatNumber(startPoint.total_lots, 1)} 張</span></div>
    <div class="compare-stat"><strong>${endPoint.date}</strong><span>${ETF.formatNumber(endPoint.total_lots, 1)} 張</span></div>
    <div class="compare-stat"><strong>${ETF.formatSigned(lotsChange, 1)}</strong><span>區間張數變化</span></div>
    <div class="compare-stat"><strong>${ETF.formatSigned(weightChange, 2)}%</strong><span>區間平均權重變化</span></div>`;
}

async function initStock() {
  const query = ETF.queryParam("q", "2330");
  const [payload, historyPayload] = await Promise.all([
    ETF.fetchJson("stock_index.json"),
    ETF.fetchJson("stock_history.json").catch(() => ({ stocks: {} })),
  ]);
  const input = document.getElementById("stockSearchInput");
  const compareStart = document.getElementById("compareStartInput");
  const compareEnd = document.getElementById("compareEndInput");
  input.value = query;
  compareStart.value = ETF.queryParam("from", "");
  compareEnd.value = ETF.queryParam("to", "");
  const stock = findStock(payload.rows, query);
  if (!stock) {
    document.getElementById("stockTable").innerHTML = '<div class="empty">查無此成分股，請改用股號或股票名稱搜尋。</div>';
    return;
  }
  renderStock(stock);
  renderHistory(historyPayload.stocks?.[stock.stock_id], compareStart.value, compareEnd.value);
  document.getElementById("compareButton").addEventListener("click", () => {
    const params = new URLSearchParams({ q: input.value.trim() || stock.stock_id });
    if (compareStart.value) params.set("from", compareStart.value);
    if (compareEnd.value) params.set("to", compareEnd.value);
    window.location.href = `stock.html?${params.toString()}`;
  });
  document.getElementById("stockSearchButton").addEventListener("click", () => {
    if (input.value.trim()) window.location.href = `stock.html?q=${encodeURIComponent(input.value.trim())}`;
  });
  input.addEventListener("keydown", (event) => {
    if (event.key === "Enter" && input.value.trim()) {
      window.location.href = `stock.html?q=${encodeURIComponent(input.value.trim())}`;
    }
  });
}

initStock().catch((error) => {
  document.getElementById("stockTable").innerHTML = `<div class="empty">${error.message}</div>`;
});
