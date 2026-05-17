function renderHolding(rows) {
  const container = document.getElementById("matrixTable");
  container.innerHTML = `
    <div class="table-wrap">
      <table data-sortable>
        <thead><tr><th>個股</th><th>持有 ETF</th><th>平均比例</th><th>合計張數</th><th>ETF 明細</th></tr></thead>
        <tbody>
          ${rows
            .slice(0, 80)
            .map(
              (row) => `
                <tr>
                  <td>${ETF.stockLink(row)}</td>
                  <td data-value="${row.held_etf_count}">${row.held_etf_count}</td>
                  <td data-value="${row.avg_weight_pct}">${ETF.formatNumber(row.avg_weight_pct, 2)}%</td>
                  <td data-value="${row.total_lots}">${ETF.formatNumber(row.total_lots, 1)}</td>
                  <td>${Object.entries(row.etfs)
                    .map(([code, item]) => `${ETF.etfLink(code)} ${ETF.formatNumber(item.weight_pct, 2)}%`)
                    .join("、")}</td>
                </tr>`,
            )
            .join("")}
        </tbody>
      </table>
    </div>`;
  ETF.enableTableSorting(container);
}

function renderChange(rows) {
  const container = document.getElementById("matrixTable");
  container.innerHTML = `
    <div class="table-wrap">
      <table data-sortable>
        <thead><tr><th>個股</th><th>加碼</th><th>新增</th><th>減碼</th><th>出清</th><th>股數增減</th><th>主訊號</th><th>ETF 異動</th></tr></thead>
        <tbody>
          ${rows
            .slice(0, 80)
            .map(
              (row) => `
                <tr>
                  <td>${ETF.stockLink(row)}</td>
                  <td data-value="${row.add_count}">${row.add_count}</td>
                  <td data-value="${row.new_count}">${row.new_count}</td>
                  <td data-value="${row.reduce_count}">${row.reduce_count}</td>
                  <td data-value="${row.removed_count}">${row.removed_count}</td>
                  <td data-value="${row.total_shares_change}">${ETF.formatSigned(row.total_shares_change)}</td>
                  <td>${row.dominant_signal}</td>
                  <td>${Object.entries(row.etfs)
                    .map(([code, change]) => `${ETF.etfLink(code)} ${ETF.makeBadge(change)}`)
                    .join(" ")}</td>
                </tr>`,
            )
            .join("")}
        </tbody>
      </table>
    </div>`;
  ETF.enableTableSorting(container);
}

async function initMatrix() {
  const [holding, change] = await Promise.all([ETF.fetchJson("holding_matrix.json"), ETF.fetchJson("change_matrix.json")]);
  ETF.setText("matrixDate", holding.meta.data_date);
  ETF.setText("matrixStocks", holding.meta.stock_count);
  ETF.setText("matrixEtfs", holding.meta.etf_count);
  const buttons = document.querySelectorAll("[data-matrix]");
  const activate = (mode) => {
    buttons.forEach((button) => button.classList.toggle("is-active", button.dataset.matrix === mode));
    if (mode === "change") renderChange(change.rows);
    else renderHolding(holding.rows);
  };
  buttons.forEach((button) => button.addEventListener("click", () => activate(button.dataset.matrix)));
  activate("holding");
}

initMatrix().catch((error) => {
  document.getElementById("matrixTable").innerHTML = `<div class="empty">${error.message}</div>`;
});
