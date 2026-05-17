from pathlib import Path

from scripts.normalize_holdings import (
    build_holding,
    normalize_change_type,
    parse_number,
    parse_stock_display,
    read_holdings_text,
)


def test_parse_stock_display_splits_name_and_stock_id():
    stock = parse_stock_display("台積電(2330)")

    assert stock == {
        "stock_name": "台積電",
        "stock_id": "2330",
        "stock_display": "台積電(2330)",
    }


def test_parse_number_removes_commas_and_supports_negative_values():
    assert parse_number("11,657,000", as_int=True) == 11657000
    assert parse_number("-100,000", as_int=True) == -100000
    assert parse_number("10.26") == 10.26


def test_normalize_change_type_maps_source_text_to_allowed_values():
    assert normalize_change_type("新增持有") == "新增"
    assert normalize_change_type("加碼") == "加碼"
    assert normalize_change_type("減碼") == "減碼"
    assert normalize_change_type("出清") == "出清"
    assert normalize_change_type("持平") == "持平"


def test_build_holding_keeps_warning_when_weight_and_shares_conflict():
    row = {
        "個股名稱": "聯發科(2454)",
        "投資比例(%)": "5.4",
        "持有股數": "4,263,000",
        "比例增減(%)": "0.63",
        "股數增減": "-100,000",
        "股數異動": "減碼",
    }

    holding = build_holding(row)

    assert holding["stock_id"] == "2454"
    assert holding["shares"] == 4263000
    assert holding["shares_lot"] == 4263
    assert holding["shares_change"] == -100000
    assert holding["shares_change_lot"] == -100
    assert holding["system_change_type"] == "減碼"
    assert "比例增加但股數減少" in holding["note"]


def test_read_holdings_text_parses_full_width_comma_file():
    source = Path("00981A_單檔持股清單.txt")

    holdings = read_holdings_text(source)

    assert holdings[0]["stock_display"] == "台積電(2330)"
    assert holdings[0]["shares"] == 11657000
    assert holdings[0]["system_change_type"] == "加碼"
