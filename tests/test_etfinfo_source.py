from scripts.etfinfo_source import (
    discover_active_etfs_from_html,
    extract_snapshot_date,
    parse_holdings_page,
    parse_nuxt_payload,
)


ACTIVE_HTML = """
<html><body>
<h1>主動式 ETF 清單與持股異動</h1>
<a href="/etf/00991A">00991A</a>
<div>主動復華未來50 復華・半年配</div>
<a href="/etf/00986A">00986A</a>
<div>主動台新龍頭成長 台新・年配</div>
<a href="/etf/00403A">00403A</a>
<div>主動統一升級50 統一・—</div>
<a href="/etf/00981A">00981A</a>
<div>主動統一台股增長 統一・季配</div>
</body></html>
"""


HOLDINGS_HTML = """
<html><body>
<h1>主動中信台灣卓越</h1>
<div>00995A 主動型</div>
<div>中國信託台灣卓越成長主動式ETF證券投資信託基金</div>
<h2>完整持股明細</h2>
<p>共 55 檔持股・快照 2026-05-14</p>
<div>代號 ↕ 名稱 ↕ 漲跌幅 ↕收盤價 權重 ↓ 股數 ↕ 貢獻度 ⓘ ↕</div>
<a href="/stock/2330">2330</a><span>台灣積體電路製造</span>
<span>+2.25%2270</span><span>9.16%226,000</span><span>+0.20%</span>
<a href="/stock/2383">2383</a><span>台光電子材料</span>
<span>-0.2%4920</span><span>6.50%74,000</span><span>-0.01%</span>
<p>成分股明細常見問題</p>
</body></html>
"""


def test_discover_active_etfs_from_html_extracts_codes_names_and_issuers():
    etfs = discover_active_etfs_from_html(ACTIVE_HTML)

    assert [item["etf_code"] for item in etfs] == ["00991A", "00986A", "00403A", "00981A"]
    assert etfs[0]["etf_name"] == "主動復華未來50"
    assert etfs[0]["issuer"] == "復華"
    assert etfs[2]["enabled"] is True


def test_parse_holdings_page_extracts_snapshot_and_holdings():
    payload = parse_holdings_page(HOLDINGS_HTML, etf_code="00995A", source_url="https://www.etfinfo.tw/etf/00995A/holdings")

    assert payload["meta"]["etf_code"] == "00995A"
    assert payload["meta"]["data_date"] == "2026-05-14"
    assert payload["meta"]["holdings_count"] == 2
    assert payload["holdings"][0]["stock_id"] == "2330"
    assert payload["holdings"][0]["stock_name"] == "台灣積體電路製造"
    assert payload["holdings"][0]["stock_display"] == "台灣積體電路製造(2330)"
    assert payload["holdings"][0]["weight_pct"] == 9.16
    assert payload["holdings"][0]["shares"] == 226000
    assert payload["holdings"][0]["source_status"] == "updated"


def test_parse_nuxt_payload_extracts_complete_holdings_array():
    payload_text = """
    [{"data":1},{"info":2},{"name":3,"holdings":4},"主動中信台灣卓越",
    [{"code":5,"name":6,"weight":7,"shares":8,"unit":9,"industry":10},"2330","台灣積體電路製造",9.59,226000,"股",null,
    {"code":11,"name":12,"weight":13,"shares":14,"unit":9,"industry":10},"2383","台光電子材料",6.39,74000],
    {"snapshotDate":15},"2026-05-15"]
    """

    payload = parse_nuxt_payload(payload_text, etf_code="00995A", source_url="https://www.etfinfo.tw/etf/00995A/holdings")

    assert payload["meta"]["data_date"] == "2026-05-15"
    assert payload["meta"]["holdings_count"] == 2
    assert payload["holdings"][1]["stock_id"] == "2383"
    assert payload["holdings"][1]["shares"] == 74000


def test_extract_snapshot_date_prefers_holdings_snapshot_text():
    assert extract_snapshot_date("<p>持股快照：2026-05-15</p>") == "2026-05-15"
def test_parse_holdings_page_prefers_visible_latest_snapshot_date_over_other_dates():
    html = """
    <meta name="description" content="00980A 成分股明細：最新持股快照（2026-05-15），目前揭露 48 檔成分股">
    [{"code":5,"name":6,"weight":7,"shares":8},"2330","TSMC",9.59,226000,{"snapshotDate":15},"2025-05-05"]
    """

    payload = parse_holdings_page(html, etf_code="00980A", source_url="https://www.etfinfo.tw/etf/00980A/holdings")

    assert payload["meta"]["data_date"] == "2026-05-15"
