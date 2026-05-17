import json
from pathlib import Path

from scripts.build_stock_history import available_dates, build_stock_history, trading_dates


def write_normalized(root: Path, data_date: str, etf_code: str, stock_id: str, shares: int, weight: float) -> None:
    path = root / "data" / "normalized" / data_date / f"{etf_code}.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "meta": {"etf_code": etf_code, "data_date": data_date, "holdings_count": 1},
                "holdings": [
                    {
                        "stock_id": stock_id,
                        "stock_name": "TSMC",
                        "stock_display": "TSMC(2330)",
                        "weight_pct": weight,
                        "shares": shares,
                        "shares_lot": shares / 1000,
                        "weight_change_pct": 0,
                        "shares_change": 0,
                        "shares_change_lot": 0,
                        "system_change_type": "flat",
                    }
                ],
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )


def test_stock_history_uses_saved_trading_dates_and_builds_five_day_curve(tmp_path):
    for index, data_date in enumerate(["2026-05-11", "2026-05-12", "2026-05-13", "2026-05-14", "2026-05-15"]):
        write_normalized(tmp_path, data_date, "00980A", "2330", 1000 + index * 100, 10 + index)

    payload = build_stock_history(tmp_path, data_date="2026-05-15", history_days=5)
    row = payload["stocks"]["2330"]

    assert available_dates(tmp_path) == ["2026-05-11", "2026-05-12", "2026-05-13", "2026-05-14", "2026-05-15"]
    assert payload["meta"]["dates"] == ["2026-05-11", "2026-05-12", "2026-05-13", "2026-05-14", "2026-05-15"]
    assert [point["total_shares"] for point in row["history"]] == [1000, 1100, 1200, 1300, 1400]


def test_stock_history_compares_requested_date_range(tmp_path):
    write_normalized(tmp_path, "2026-05-14", "00980A", "2330", 1000, 10)
    write_normalized(tmp_path, "2026-05-15", "00980A", "2330", 1600, 12)

    payload = build_stock_history(tmp_path, data_date="2026-05-15", history_days=5, compare_start_date="2026-05-14")
    compare = payload["stocks"]["2330"]["range_compare"]

    assert compare["start_date"] == "2026-05-14"
    assert compare["end_date"] == "2026-05-15"
    assert compare["shares_change"] == 600
    assert compare["weight_change_pct"] == 2


def test_stock_history_excludes_weekend_dates_from_comparison_choices(tmp_path):
    write_normalized(tmp_path, "2026-05-15", "00980A", "2330", 1000, 10)
    write_normalized(tmp_path, "2026-05-16", "00980A", "2330", 1600, 12)

    payload = build_stock_history(tmp_path, data_date="2026-05-16", history_days=5)

    assert available_dates(tmp_path) == ["2026-05-15", "2026-05-16"]
    assert trading_dates(tmp_path) == ["2026-05-15"]
    assert payload["meta"]["available_dates"] == ["2026-05-15"]
    assert payload["meta"]["stored_dates"] == ["2026-05-15", "2026-05-16"]
    assert payload["meta"]["data_date"] == "2026-05-15"
