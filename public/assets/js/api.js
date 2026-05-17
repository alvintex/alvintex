const DATA_ROOT = "data/latest";

async function fetchJson(path) {
  const response = await fetch(`${DATA_ROOT}/${path}`);
  if (!response.ok) {
    throw new Error(`無法讀取 ${path}`);
  }
  return response.json();
}

function formatNumber(value, digits = 0) {
  const number = Number(value || 0);
  return new Intl.NumberFormat("zh-TW", {
    maximumFractionDigits: digits,
    minimumFractionDigits: digits,
  }).format(number);
}

function formatSigned(value, digits = 0) {
  const number = Number(value || 0);
  const sign = number > 0 ? "+" : "";
  return `${sign}${formatNumber(number, digits)}`;
}

function queryParam(name, fallback = "") {
  return new URLSearchParams(window.location.search).get(name) || fallback;
}

function badgeClass(changeType) {
  if (changeType === "加碼") return "badge badge-add";
  if (changeType === "新增") return "badge badge-new";
  if (changeType === "減碼") return "badge badge-reduce";
  if (changeType === "出清") return "badge badge-removed";
  return "badge badge-flat";
}

function makeBadge(changeType) {
  return `<span class="${badgeClass(changeType)}">${changeType || "持平"}</span>`;
}

function stockLink(row) {
  return `<a href="stock.html?q=${encodeURIComponent(row.stock_id || row.stock_display)}"><strong>${row.stock_display}</strong></a>`;
}

function etfLink(code) {
  return `<a href="etf.html?code=${encodeURIComponent(code)}"><strong>${code}</strong></a>`;
}

function sortTable(table, columnIndex) {
  const body = table.tBodies[0];
  const rows = Array.from(body.rows);
  const current = table.dataset.sort === `${columnIndex}:asc` ? "desc" : "asc";
  rows.sort((a, b) => {
    const av = a.cells[columnIndex]?.dataset.value || a.cells[columnIndex]?.textContent.trim() || "";
    const bv = b.cells[columnIndex]?.dataset.value || b.cells[columnIndex]?.textContent.trim() || "";
    const an = Number(String(av).replace(/,/g, ""));
    const bn = Number(String(bv).replace(/,/g, ""));
    const result = Number.isFinite(an) && Number.isFinite(bn) ? an - bn : av.localeCompare(bv, "zh-Hant");
    return current === "asc" ? result : -result;
  });
  table.dataset.sort = `${columnIndex}:${current}`;
  rows.forEach((row) => body.appendChild(row));
}

function enableTableSorting(scope = document) {
  scope.querySelectorAll("table[data-sortable] th").forEach((th, index) => {
    th.addEventListener("click", () => sortTable(th.closest("table"), index));
  });
}

function setText(id, value) {
  const element = document.getElementById(id);
  if (element) element.textContent = value;
}

window.ETF = {
  fetchJson,
  formatNumber,
  formatSigned,
  queryParam,
  makeBadge,
  stockLink,
  etfLink,
  enableTableSorting,
  setText,
};
