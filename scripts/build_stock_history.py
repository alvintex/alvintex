from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.normalize_holdings import DEFAULT_DATA_DATE, PROJECT_ROOT


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def available_dates(project_root: Path = PROJECT_ROOT) -> list[str]:
    base = project_root / "data" / "normalized"
    if not base.exists():
        return []
    return sorted(path.name for path in base.iterdir() if path.is_dir())


def trading_dates(project_root: Path = PROJECT_ROOT) -> list[str]:
    dates = []
    for data_date in available_dates(project_root):
        try:
            if datetime.strptime(data_date, "%Y-%m-%d").weekday() < 5:
                dates.append(data_date)
        except ValueError:
            continue
    return dates


def nearest_date(dates: list[str], requested: str) -> str | None:
    candidates = [data_date for data_date in dates if data_date <= requested]
    return candidates[-1] if candidates else None


def selected_history_dates(dates: list[str], *, data_date: str, history_days: int) -> list[str]:
    end_date = nearest_date(dates, data_date)
    if not end_date:
        return []
    end_index = dates.index(end_date)
    start_index = max(0, end_index - history_days + 1)
    return dates[start_index : end_index + 1]


def aggregate_stock_for_date(project_root: Path, data_date: str) -> dict[str, dict[str, Any]]:
    normalized_dir = project_root / "data" / "normalized" / data_date
    rows: dict[str, dict[str, Any]] = {}
    for path in normalized_dir.glob("*.json"):
        payload = load_json(path)
        etf_code = payload["meta"].get("etf_code", path.stem)
        for holding in payload.get("holdings", []):
            stock_id = holding["stock_id"]
            row = rows.setdefault(
                stock_id,
                {
                    "stock_id": stock_id,
                    "stock_name": holding["stock_name"],
                    "stock_display": holding["stock_display"],
                    "etfs": {},
                },
            )
            row["etfs"][etf_code] = {
                "weight_pct": holding["weight_pct"],
                "shares": holding["shares"],
                "shares_lot": holding["shares_lot"],
            }
    for row in rows.values():
        etfs = row["etfs"]
        weights = [item["weight_pct"] for item in etfs.values()]
        row["held_etf_count"] = len(etfs)
        row["avg_weight_pct"] = round(sum(weights) / len(weights), 2) if weights else 0
        row["total_shares"] = sum(item["shares"] for item in etfs.values())
        row["total_lots"] = round(sum(item["shares_lot"] for item in etfs.values()), 1)
    return rows


def compare_points(start: dict[str, Any] | None, end: dict[str, Any] | None, *, start_date: str, end_date: str) -> dict[str, Any]:
    start = start or {}
    end = end or {}
    return {
        "start_date": start_date,
        "end_date": end_date,
        "start_total_shares": start.get("total_shares", 0),
        "end_total_shares": end.get("total_shares", 0),
        "shares_change": end.get("total_shares", 0) - start.get("total_shares", 0),
        "start_total_lots": start.get("total_lots", 0),
        "end_total_lots": end.get("total_lots", 0),
        "lots_change": round(end.get("total_lots", 0) - start.get("total_lots", 0), 1),
        "start_avg_weight_pct": start.get("avg_weight_pct", 0),
        "end_avg_weight_pct": end.get("avg_weight_pct", 0),
        "weight_change_pct": round(end.get("avg_weight_pct", 0) - start.get("avg_weight_pct", 0), 2),
        "held_etf_count_change": end.get("held_etf_count", 0) - start.get("held_etf_count", 0),
    }


def build_stock_history(
    project_root: Path = PROJECT_ROOT,
    *,
    data_date: str = DEFAULT_DATA_DATE,
    history_days: int = 5,
    compare_start_date: str | None = None,
    compare_end_date: str | None = None,
) -> dict[str, Any]:
    stored_dates = available_dates(project_root)
    dates = trading_dates(project_root)
    history_dates = selected_history_dates(dates, data_date=data_date, history_days=history_days)
    output_data_date = nearest_date(dates, data_date)
    end_date = nearest_date(dates, compare_end_date or data_date)
    start_date = nearest_date(dates, compare_start_date) if compare_start_date else None
    by_date = {date_value: aggregate_stock_for_date(project_root, date_value) for date_value in sorted(set(history_dates + [date for date in [start_date, end_date] if date]))}

    stocks: dict[str, dict[str, Any]] = {}
    for date_value in history_dates:
        for stock_id, row in by_date.get(date_value, {}).items():
            stock = stocks.setdefault(
                stock_id,
                {
                    "stock_id": stock_id,
                    "stock_name": row["stock_name"],
                    "stock_display": row["stock_display"],
                    "history": [],
                },
            )
            stock["history"].append(
                {
                    "date": date_value,
                    "held_etf_count": row["held_etf_count"],
                    "avg_weight_pct": row["avg_weight_pct"],
                    "total_shares": row["total_shares"],
                    "total_lots": row["total_lots"],
                    "etfs": row["etfs"],
                }
            )

    if start_date and end_date:
        stock_ids = set(by_date.get(start_date, {})) | set(by_date.get(end_date, {})) | set(stocks)
        for stock_id in stock_ids:
            end_row = by_date.get(end_date, {}).get(stock_id)
            start_row = by_date.get(start_date, {}).get(stock_id)
            source_row = end_row or start_row or {}
            stock = stocks.setdefault(
                stock_id,
                {
                    "stock_id": stock_id,
                    "stock_name": source_row.get("stock_name", ""),
                    "stock_display": source_row.get("stock_display", stock_id),
                    "history": [],
                },
            )
            stock["range_compare"] = compare_points(start_row, end_row, start_date=start_date, end_date=end_date)

    return {
        "meta": {
            "data_date": output_data_date or data_date,
            "history_days": history_days,
            "stored_dates": stored_dates,
            "available_dates": dates,
            "dates": history_dates,
            "compare_start_date": start_date,
            "compare_end_date": end_date,
            "stock_count": len(stocks),
        },
        "stocks": stocks,
    }


def write_stock_history(
    project_root: Path = PROJECT_ROOT,
    *,
    data_date: str = DEFAULT_DATA_DATE,
    history_days: int = 5,
    compare_start_date: str | None = None,
    compare_end_date: str | None = None,
) -> Path:
    payload = build_stock_history(
        project_root,
        data_date=data_date,
        history_days=history_days,
        compare_start_date=compare_start_date,
        compare_end_date=compare_end_date,
    )
    output_dir = project_root / "data" / "history" / payload["meta"]["data_date"]
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "stock_history.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build per-stock holding history and range comparison JSON.")
    parser.add_argument("--data-date", default=DEFAULT_DATA_DATE)
    parser.add_argument("--history-days", type=int, default=5)
    parser.add_argument("--compare-start-date")
    parser.add_argument("--compare-end-date")
    args = parser.parse_args()

    print(
        write_stock_history(
            PROJECT_ROOT,
            data_date=args.data_date,
            history_days=args.history_days,
            compare_start_date=args.compare_start_date,
            compare_end_date=args.compare_end_date,
        )
    )


if __name__ == "__main__":
    main()
