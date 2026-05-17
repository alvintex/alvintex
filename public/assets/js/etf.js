function renderHoldings(rows) {
  const filter = document.getElementById("changeFilter").value;
  const query = document.getElementById("stockFilter").value.trim();
  const visible = rows.filter((row) => {
    const matchType = filter === "全部" || row.system_change_type === filter;
    const matchQuery = !query || row.stock_display.includes(query) || row.stock_id.includes(query);
    return matchType && matchQuery;
  });
  const container = document.getElementById("holdingsTable");
  if (!visible.length) {
    container.innerHTML = '<div class="empty">找不到符合條件的持股</div>';
    return;
  }
  container.innerHTML = `
    <div class="table-wrap">
      <table data-sortable>
        <thead>
          <tr>
            <th>排名</th><th>個股</th><th>投資比例</th><th>持有張數</th>
            <th>比例增減</th><th>張數增減</th><th>異動</th><th>備註</th>
          </tr>
        </thead>
        <tbody>
          ${visible
            .map(
              (row, index) => `
                <tr>
                  <td data-value="${index + 1}">${index + 1}</td>
                  <td>${ETF.stockLink(row)}</td>
                  <td data-value="${row.weight_pct}">${ETF.formatNumber(row.weight_pct, 2)}%</td>
                  <td data-value="${row.shares_lot}">${ETF.formatNumber(row.shares_lot, 1)}</td>
                  <td data-value="${row.weight_change_pct}">${ETF.formatSigned(row.weight_change_pct, 2)}%</td>
                  <td data-value="${row.shares_change_lot}">${ETF.formatSigned(row.shares_change_lot, 1)}</td>
                  <td>${ETF.makeBadge(row.system_change_type)}</td>
                  <td class="warning-note">${row.note || ""}</td>
                </tr>`,
            )
            .join("")}
        </tbody>
      </table>
    </div>`;
  ETF.enableTableSorting(container);
}

async function initEtf() {
  const code = ETF.queryParam("code", "00981A");
  const payload = await ETF.fetchJson(`${code}.json`);
  ETF.setText("etfCode", code);
  ETF.setText("etfDate", payload.meta.data_date);
  ETF.setText("holdingCount", payload.meta.holdings_count);
  ETF.setText("sourceStatus", payload.meta.source_status);
  const rows = payload.holdings.sort((a, b) => b.weight_pct - a.weight_pct);
  document.getElementById("changeFilter").addEventListener("change", () => renderHoldings(rows));
  document.getElementById("stockFilter").addEventListener("input", () => renderHoldings(rows));
  renderHoldings(rows);
}

initEtf().catch((error) => {
  document.getElementById("holdingsTable").innerHTML = `<div class="empty">${error.message}</div>`;
});
