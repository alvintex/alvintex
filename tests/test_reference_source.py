from scripts.reference_source import (
    build_search_index_from_reference,
    choose_reference_data_date,
    normalize_reference_search_rows,
    reference_rankings_from_api_payloads,
)


SEARCH_ROWS = [
    {"ETF代號": "00980A", "個股名稱": "台達電(2308)", "投資比例(%)": 5.52, "持有股數": 459000, "比例增減(%)": -0.75, "股數增減": 40000, "股數異動": "加碼"},
    {"ETF代號": "00981A", "個股名稱": "台達電(2308)", "投資比例(%)": 5.3, "持有股數": 6572000, "比例增減(%)": -0.16, "股數增減": 548000, "股數異動": "加碼"},
    {"ETF代號": "00984A", "個股名稱": "台達電(2308)", "投資比例(%)": 0.85, "持有股數": 27000, "比例增減(%)": -0.12, "股數增減": -10000, "股數異動": "減碼"},
    {"ETF代號": "00987A", "個股名稱": "台達電(2308)", "投資比例(%)": 4.96, "持有股數": 80000, "比例增減(%)": 0, "股數增減": 0, "股數異動": "持平"},
]


def test_normalize_reference_search_rows_preserves_change_fields():
    rows = normalize_reference_search_rows(SEARCH_ROWS)

    assert rows[0]["etf_code"] == "00980A"
    assert rows[0]["stock_id"] == "2308"
    assert rows[0]["weight_change_pct"] == -0.75
    assert rows[0]["shares_change_lot"] == 40
    assert rows[0]["system_change_type"] == "加碼"


def test_build_search_index_from_reference_counts_stock_changes():
    payload = build_search_index_from_reference(SEARCH_ROWS, data_date="2026-05-16")
    row = payload["rows"][0]

    assert row["stock_display"] == "台達電(2308)"
    assert row["held_etf_count"] == 4
    assert row["add_count"] == 2
    assert row["reduce_count"] == 1
    assert row["new_count"] == 0
    assert row["removed_count"] == 0
    assert row["etfs"]["00980A"]["shares_change_lot"] == 40
    assert row["etfs"]["00984A"]["change_type"] == "減碼"


def test_reference_rankings_from_api_payloads_maps_blog_api_fields():
    payload = reference_rankings_from_api_payloads(
        {
            "all": {"data": [{"個股名稱": "台達電(2308)", "持有ETF數量": 10, "平均比例(%)": 3.9, "合計總股數": 12880500, "合計總張數": 12880.5}]},
            "plus": {"data": [{"個股名稱": "台達電(2308)", "加碼基金數": 3, "平均比例": 4.74, "合計加碼張數": 2360, "強力加碼": "🚀 強力加碼 >500張"}]},
            "new": {"data": []},
            "minus": {"data": []},
            "exit": {"data": []},
            "hold": {"data": []},
        },
        data_date="2026-05-16",
    )

    assert payload["rankings"]["most_held_rank"][0]["held_etf_count"] == 10
    assert payload["rankings"]["add_rank"][0]["add_etf_count"] == 3


def test_choose_reference_data_date_prefers_ranking_update_time():
    assert (
        choose_reference_data_date(
            {"updateTime": "即時追蹤中"},
            {"all": {"updateTime": "資料更新日期：2026/05/16 (監控 10 檔主動式 ETF)"}},
        )
        == "2026-05-16"
    )
