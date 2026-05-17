from __future__ import annotations

import argparse
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_matrix import write_matrices
from scripts.build_rankings import write_rankings_from_data
from scripts.build_search_index import write_search_index
from scripts.build_stock_history import trading_dates, write_stock_history
from scripts.compute_diff import apply_diff_to_file
from scripts.normalize_holdings import PROJECT_ROOT
from scripts.run_daily_local import copy_to_public


def available_dates(project_root: Path) -> list[str]:
    base = project_root / "data" / "normalized"
    if not base.exists():
        return []
    return sorted(path.name for path in base.iterdir() if path.is_dir())


def rebuild(project_root: Path = PROJECT_ROOT, *, compare_start_date: str | None = None, compare_end_date: str | None = None) -> list[str]:
    dates = available_dates(project_root)
    for data_date in dates:
        for path in (project_root / "data" / "normalized" / data_date).glob("*.json"):
            apply_diff_to_file(project_root, data_date=data_date, etf_code=path.stem)
        write_matrices(project_root, data_date=data_date)
        write_rankings_from_data(project_root, data_date=data_date)
        write_search_index(project_root, data_date=data_date)
        write_stock_history(project_root, data_date=data_date, compare_start_date=compare_start_date, compare_end_date=compare_end_date or data_date)
    public_dates = trading_dates(project_root)
    if public_dates:
        copy_to_public(project_root, data_date=public_dates[-1])
    return dates


def main() -> None:
    parser = argparse.ArgumentParser(description="Rebuild diffs, matrices, rankings and search indexes for stored historical snapshots.")
    parser.add_argument("--compare-start-date")
    parser.add_argument("--compare-end-date")
    args = parser.parse_args()
    dates = rebuild(PROJECT_ROOT, compare_start_date=args.compare_start_date, compare_end_date=args.compare_end_date)
    print(f"Rebuilt {len(dates)} historical date(s): {', '.join(dates)}")


if __name__ == "__main__":
    main()
