import json

from scripts.compute_diff import apply_diff, previous_payload


def payload(date, holdings):
    return {
        "meta": {"etf_code": "00981A", "data_date": date, "holdings_count": len(holdings)},
        "holdings": holdings,
    }


def holding(stock_id, shares, weight=1.0, name="測試"):
    return {
        "stock_id": stock_id,
        "stock_name": name,
        "stock_display": f"{name}({stock_id})",
        "weight_pct": weight,
        "shares": shares,
        "shares_lot": shares / 1000,
        "weight_change_pct": 0,
        "shares_change": 0,
        "shares_change_lot": 0,
        "source_change_text": "持平",
        "system_change_type": "持平",
        "note": "",
    }


def test_apply_diff_classifies_new_add_reduce_flat_and_removed():
    previous = payload("2026-05-13", [
        holding("2330", 1000, 10, "台積電"),
        holding("2454", 2000, 5, "聯發科"),
        holding("2308", 3000, 4, "台達電"),
        holding("9999", 500, 1, "舊股"),
    ])
    current = payload("2026-05-14", [
        holding("2330", 1500, 11, "台積電"),
        holding("2454", 1000, 6, "聯發科"),
        holding("2308", 3000, 3.5, "台達電"),
        holding("2383", 800, 2, "台光電"),
    ])

    result = apply_diff(current, previous)
    rows = {row["stock_id"]: row for row in result["holdings"]}

    assert rows["2330"]["system_change_type"] == "加碼"
    assert rows["2330"]["shares_change"] == 500
    assert rows["2454"]["system_change_type"] == "減碼"
    assert rows["2454"]["note"] == "比例增加但股數減少，判斷以股數為準"
    assert rows["2308"]["system_change_type"] == "持平"
    assert rows["2383"]["system_change_type"] == "新增"
    assert rows["9999"]["system_change_type"] == "出清"
    assert rows["9999"]["shares"] == 0
    assert result["meta"]["compare_date"] == "2026-05-13"


def test_previous_payload_skips_weekend_snapshots(tmp_path):
    base = tmp_path / "data" / "normalized"
    for data_date in ["2026-05-15", "2026-05-16"]:
        path = base / data_date / "00981A.json"
        path.parent.mkdir(parents=True)
        path.write_text(
            json.dumps(payload(data_date, [holding("2330", 1000)]), ensure_ascii=False),
            encoding="utf-8",
        )

    result = previous_payload(tmp_path, data_date="2026-05-18", etf_code="00981A")

    assert result["meta"]["data_date"] == "2026-05-15"
