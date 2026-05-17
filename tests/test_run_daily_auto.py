import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scripts.run_daily_auto as run_daily_auto


def sample_payload(code):
    return {
        "meta": {
            "etf_code": code,
            "etf_name": code,
            "data_date": "2026-05-16",
            "run_date": "2026-05-16",
            "source_status": "updated",
            "source_url": f"https://example.test/{code}",
            "holdings_count": 1,
        },
        "holdings": [
            {
                "stock_id": "2330",
                "stock_name": "TSMC",
                "stock_display": "TSMC(2330)",
                "weight_pct": 10.5,
                "shares": 1000,
                "shares_lot": 1,
                "weight_change_pct": 0,
                "shares_change": 0,
                "shares_change_lot": 0,
                "source_change_text": "",
                "system_change_type": "",
                "source_status": "updated",
                "note": "",
            }
        ],
    }


def test_fetch_all_can_store_crawled_snapshot_under_backfill_date(tmp_path, monkeypatch):
    monkeypatch.setattr(
        run_daily_auto,
        "discover_active_etfs",
        lambda: [{"etf_code": "00980A", "etf_name": "00980A", "enabled": True}],
    )
    monkeypatch.setattr(run_daily_auto, "fetch_holdings", sample_payload)
    monkeypatch.setattr(run_daily_auto, "write_matrices", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_daily_auto, "write_rankings_from_data", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_daily_auto, "write_search_index", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_daily_auto, "copy_to_public", lambda *args, **kwargs: None)

    latest_date = run_daily_auto.fetch_all(tmp_path, data_date="2026-05-14", force_data_date=True)

    output = tmp_path / "data" / "normalized" / "2026-05-14" / "00980A.json"
    payload = json.loads(output.read_text(encoding="utf-8"))

    assert latest_date == "2026-05-14"
    assert output.exists()
    assert payload["meta"]["data_date"] == "2026-05-14"
    assert payload["meta"]["source_data_date"] == "2026-05-16"


def test_backfill_dates_includes_each_day_in_range():
    assert run_daily_auto.backfill_dates("2026-05-14", "2026-05-16") == [
        "2026-05-14",
        "2026-05-15",
        "2026-05-16",
    ]


def test_fetch_all_skips_non_matching_backfill_date_without_faking_trading_day(tmp_path, monkeypatch):
    monkeypatch.setattr(
        run_daily_auto,
        "discover_active_etfs",
        lambda: [{"etf_code": "00980A", "etf_name": "00980A", "enabled": True}],
    )
    monkeypatch.setattr(run_daily_auto, "fetch_holdings", sample_payload)
    monkeypatch.setattr(run_daily_auto, "write_matrices", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_daily_auto, "write_rankings_from_data", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_daily_auto, "write_search_index", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_daily_auto, "write_stock_history", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_daily_auto, "copy_to_public", lambda *args, **kwargs: None)

    latest_date = run_daily_auto.fetch_all(tmp_path, data_date="2026-05-17")

    assert latest_date == "2026-05-16"
    assert not (tmp_path / "data" / "normalized" / "2026-05-17" / "00980A.json").exists()
    assert (tmp_path / "data" / "normalized" / "2026-05-16" / "00980A.json").exists()


def test_fetch_all_with_no_discover_limit_does_not_overwrite_config(tmp_path, monkeypatch):
    config_path = tmp_path / "config" / "etfs.json"
    config_path.parent.mkdir(parents=True)
    config_path.write_text(
        json.dumps(
            {
                "etfs": [
                    {"etf_code": "00980A", "etf_name": "00980A", "enabled": True},
                    {"etf_code": "00981A", "etf_name": "00981A", "enabled": True},
                ]
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(run_daily_auto, "fetch_holdings", sample_payload)
    monkeypatch.setattr(run_daily_auto, "write_matrices", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_daily_auto, "write_rankings_from_data", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_daily_auto, "write_search_index", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_daily_auto, "write_stock_history", lambda *args, **kwargs: None)
    monkeypatch.setattr(run_daily_auto, "copy_to_public", lambda *args, **kwargs: None)

    run_daily_auto.fetch_all(tmp_path, discover=False, limit=1)

    config = json.loads(config_path.read_text(encoding="utf-8"))
    assert [item["etf_code"] for item in config["etfs"]] == ["00980A", "00981A"]
