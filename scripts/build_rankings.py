from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.docx_utils import parse_number, parse_stock_display, read_docx_cells
from scripts.normalize_holdings import DEFAULT_DATA_DATE, PROJECT_ROOT


RANKING_FILES = {
    "add_rank": "加碼榜.docx",
    "new_rank": "新增榜.docx",
    "reduce_rank": "減碼榜.docx",
    "removed_rank": "出清榜.docx",
    "unchanged_rank": "持平榜.docx",
    "most_held_rank": "持有總覽.docx",
}


def base_stock(value: str) -> dict[str, str]:
    stock_name, stock_id, stock_display = parse_stock_display(value)
    return {"stock_name": stock_name, "stock_id": stock_id, "stock_display": stock_display}


def group_rows(cells: list[str], columns: int) -> list[list[str]]:
    body = cells[columns:]
    return [body[index : index + columns] for index in range(0, len(body), columns) if len(body[index : index + columns]) == columns]


def parse_add_rank(path: Path) -> list[dict[str, Any]]:
    rows = []
    for stock, count, avg_weight, lots, flag in group_rows(read_docx_cells(path), 5):
        rows.append(
            {
                **base_stock(stock),
                "add_etf_count": parse_number(count, as_int=True),
                "avg_weight_pct": parse_number(avg_weight),
                "total_shares_change_lot": parse_number(lots),
                "strong_add_flag": "強力加碼" in flag,
                "flag_text": flag,
            }
        )
    return rows


def parse_new_rank(path: Path) -> list[dict[str, Any]]:
    rows = []
    for stock, weight, shares, weight_change, lots_change, flag in group_rows(read_docx_cells(path), 6):
        rows.append(
            {
                **base_stock(stock),
                "total_weight_pct": parse_number(weight),
                "total_shares": parse_number(shares, as_int=True),
                "total_weight_change_pct": parse_number(weight_change),
                "total_shares_change_lot": parse_number(lots_change),
                "strong_new_flag": "強力" in flag,
                "flag_text": flag,
            }
        )
    return rows


def parse_reduce_rank(path: Path) -> list[dict[str, Any]]:
    rows = []
    for stock, weight, shares, weight_change, shares_change, flag in group_rows(read_docx_cells(path), 6):
        rows.append(
            {
                **base_stock(stock),
                "total_weight_pct": parse_number(weight),
                "total_shares": parse_number(shares, as_int=True),
                "total_weight_change_pct": parse_number(weight_change),
                "total_shares_change": parse_number(shares_change, as_int=True),
                "total_shares_change_lot": parse_number(shares_change) / 1000,
                "dump_warning_flag": "倒貨" in flag,
                "flag_text": flag,
            }
        )
    return rows


def parse_removed_rank(path: Path) -> list[dict[str, Any]]:
    rows = []
    for stock, count in group_rows(read_docx_cells(path), 2):
        rows.append({**base_stock(stock), "removed_etf_count": parse_number(count, as_int=True)})
    return rows


def parse_unchanged_rank(path: Path) -> list[dict[str, Any]]:
    rows = []
    for stock, count, avg_weight, lots, flag in group_rows(read_docx_cells(path), 5):
        rows.append(
            {
                **base_stock(stock),
                "unchanged_etf_count": parse_number(count, as_int=True),
                "avg_weight_pct": parse_number(avg_weight),
                "total_lots": parse_number(lots),
                "core_holding_flag": "核心" in flag,
                "flag_text": flag,
            }
        )
    return rows


def parse_most_held_rank(path: Path) -> list[dict[str, Any]]:
    rows = []
    for stock, count, avg_weight, total_shares, total_lots in group_rows(read_docx_cells(path), 5):
        rows.append(
            {
                **base_stock(stock),
                "held_etf_count": parse_number(count, as_int=True),
                "avg_weight_pct": parse_number(avg_weight),
                "total_shares": parse_number(total_shares, as_int=True),
                "total_lots": parse_number(total_lots),
            }
        )
    return rows


def build_rankings(project_root: Path = PROJECT_ROOT, *, data_date: str = DEFAULT_DATA_DATE) -> dict[str, Any]:
    add_rank = parse_add_rank(project_root / RANKING_FILES["add_rank"])
    new_rank = parse_new_rank(project_root / RANKING_FILES["new_rank"])
    reduce_rank = parse_reduce_rank(project_root / RANKING_FILES["reduce_rank"])
    removed_rank = parse_removed_rank(project_root / RANKING_FILES["removed_rank"])
    unchanged_rank = parse_unchanged_rank(project_root / RANKING_FILES["unchanged_rank"])
    most_held_rank = parse_most_held_rank(project_root / RANKING_FILES["most_held_rank"])

    rankings = {
        "add_rank": add_rank,
        "new_rank": new_rank,
        "reduce_rank": reduce_rank,
        "removed_rank": removed_rank,
        "unchanged_rank": unchanged_rank,
        "most_held_rank": most_held_rank,
        "consensus_buy_rank": [row for row in add_rank if row["add_etf_count"] >= 3],
        "crowded_holding_rank": [row for row in most_held_rank if row["held_etf_count"] >= 7],
        "risk_reduce_rank": [row for row in reduce_rank if row["dump_warning_flag"]],
    }
    return {
        "meta": {
            "data_date": data_date,
            "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
        },
        "rankings": rankings,
    }


def write_rankings(project_root: Path = PROJECT_ROOT, *, data_date: str = DEFAULT_DATA_DATE) -> Path:
    payload = build_rankings(project_root, data_date=data_date)
    output_dir = project_root / "data" / "rankings" / data_date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "rankings.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def build_rankings_from_data(project_root: Path = PROJECT_ROOT, *, data_date: str = DEFAULT_DATA_DATE) -> dict[str, Any]:
    matrix_dir = project_root / "data" / "matrix" / data_date
    holding = json.loads((matrix_dir / "holding_matrix.json").read_text(encoding="utf-8"))
    change = json.loads((matrix_dir / "change_matrix.json").read_text(encoding="utf-8"))

    change_rows = change.get("rows", [])
    holding_rows = holding.get("rows", [])

    def total_lot(row: dict[str, Any]) -> float:
        return round(row.get("total_shares_change", 0) / 1000, 1)

    add_rank = [
        {
            "stock_id": row["stock_id"],
            "stock_name": row["stock_name"],
            "stock_display": row["stock_display"],
            "add_etf_count": row["add_count"],
            "avg_weight_pct": next((h["avg_weight_pct"] for h in holding_rows if h["stock_id"] == row["stock_id"]), 0),
            "total_shares_change_lot": total_lot(row),
            "strong_add_flag": total_lot(row) >= 500,
            "flag_text": "🚀 強力加碼 >500張" if total_lot(row) >= 500 else "",
        }
        for row in change_rows
        if row["add_count"] > 0
    ]
    add_rank.sort(key=lambda row: (-row["add_etf_count"], -row["total_shares_change_lot"], -row["avg_weight_pct"]))

    new_rank = [
        {
            "stock_id": row["stock_id"],
            "stock_name": row["stock_name"],
            "stock_display": row["stock_display"],
            "new_etf_count": row["new_count"],
            "total_shares_change_lot": total_lot(row),
            "strong_new_flag": total_lot(row) >= 500,
            "flag_text": "🔥 強力搶進 >500張" if total_lot(row) >= 500 else "",
        }
        for row in change_rows
        if row["new_count"] > 0
    ]
    new_rank.sort(key=lambda row: (-row["new_etf_count"], -row["total_shares_change_lot"]))

    reduce_rank = [
        {
            "stock_id": row["stock_id"],
            "stock_name": row["stock_name"],
            "stock_display": row["stock_display"],
            "reduce_etf_count": row["reduce_count"],
            "total_shares_change": row["total_shares_change"],
            "total_shares_change_lot": total_lot(row),
            "dump_warning_flag": abs(total_lot(row)) >= 300,
            "flag_text": "🚨 倒貨大於300張" if abs(total_lot(row)) >= 300 else "",
        }
        for row in change_rows
        if row["reduce_count"] > 0
    ]
    reduce_rank.sort(key=lambda row: (-row["reduce_etf_count"], row["total_shares_change_lot"]))

    removed_rank = [
        {
            "stock_id": row["stock_id"],
            "stock_name": row["stock_name"],
            "stock_display": row["stock_display"],
            "removed_etf_count": row["removed_count"],
        }
        for row in change_rows
        if row["removed_count"] > 0
    ]
    removed_rank.sort(key=lambda row: -row["removed_etf_count"])

    unchanged_rank = [
        {
            "stock_id": row["stock_id"],
            "stock_name": row["stock_name"],
            "stock_display": row["stock_display"],
            "unchanged_etf_count": row["unchanged_count"],
            "avg_weight_pct": next((h["avg_weight_pct"] for h in holding_rows if h["stock_id"] == row["stock_id"]), 0),
            "core_holding_flag": next((h["avg_weight_pct"] for h in holding_rows if h["stock_id"] == row["stock_id"]), 0) >= 3,
            "flag_text": "💎 核心續抱 >3%" if next((h["avg_weight_pct"] for h in holding_rows if h["stock_id"] == row["stock_id"]), 0) >= 3 else "",
        }
        for row in change_rows
        if row["unchanged_count"] > 0
    ]
    unchanged_rank.sort(key=lambda row: (-row["unchanged_etf_count"], -row["avg_weight_pct"]))

    most_held_rank = [
        {
            "stock_id": row["stock_id"],
            "stock_name": row["stock_name"],
            "stock_display": row["stock_display"],
            "held_etf_count": row["held_etf_count"],
            "avg_weight_pct": row["avg_weight_pct"],
            "total_shares": row["total_shares"],
            "total_lots": row["total_lots"],
        }
        for row in holding_rows
    ]
    most_held_rank.sort(key=lambda row: (-row["held_etf_count"], -row["avg_weight_pct"], -row["total_lots"]))

    rankings = {
        "add_rank": add_rank,
        "new_rank": new_rank,
        "reduce_rank": reduce_rank,
        "removed_rank": removed_rank,
        "unchanged_rank": unchanged_rank,
        "most_held_rank": most_held_rank,
        "consensus_buy_rank": [row for row in add_rank if row["add_etf_count"] >= 3],
        "crowded_holding_rank": [row for row in most_held_rank if row["held_etf_count"] >= 7],
        "risk_reduce_rank": [row for row in reduce_rank if row["dump_warning_flag"]],
    }
    return {
        "meta": {
            "data_date": data_date,
            "generated_at": datetime.now(timezone(timedelta(hours=8))).isoformat(timespec="seconds"),
            "source": "matrix",
        },
        "rankings": rankings,
    }


def write_rankings_from_data(project_root: Path = PROJECT_ROOT, *, data_date: str = DEFAULT_DATA_DATE) -> Path:
    payload = build_rankings_from_data(project_root, data_date=data_date)
    output_dir = project_root / "data" / "rankings" / data_date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "rankings.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build rankings JSON from manual docx files.")
    parser.add_argument("--data-date", default=DEFAULT_DATA_DATE)
    args = parser.parse_args()

    print(write_rankings(PROJECT_ROOT, data_date=args.data_date))


if __name__ == "__main__":
    main()
