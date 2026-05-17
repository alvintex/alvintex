from __future__ import annotations

import argparse
import json
import sys
from collections import Counter
from datetime import date, datetime, timedelta
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_matrix import write_matrices
from scripts.build_rankings import write_rankings_from_data
from scripts.build_search_index import write_search_index
from scripts.build_stock_history import write_stock_history
from scripts.compute_diff import apply_diff, previous_payload
from scripts.etfinfo_source import discover_active_etfs, fetch_holdings
from scripts.normalize_holdings import PROJECT_ROOT
from scripts.reference_source import import_reference
from scripts.run_daily_local import copy_to_public


def write_json(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def write_discovered_config(project_root: Path, etfs: list[dict]) -> None:
    config_dir = project_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    write_json(config_dir / "etfs.json", {"etfs": etfs})


def load_config_etfs(project_root: Path) -> list[dict]:
    path = project_root / "config" / "etfs.json"
    if not path.exists():
        return []
    return json.loads(path.read_text(encoding="utf-8")).get("etfs", [])


def parse_data_date(value: str) -> date:
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError as exc:
        raise argparse.ArgumentTypeError(f"Invalid date '{value}', expected YYYY-MM-DD.") from exc


def backfill_dates(start_date: str, end_date: str) -> list[str]:
    start = parse_data_date(start_date)
    end = parse_data_date(end_date)
    if start > end:
        raise argparse.ArgumentTypeError("--backfill-start must be earlier than or equal to --backfill-end.")
    total_days = (end - start).days
    return [(start + timedelta(days=offset)).isoformat() for offset in range(total_days + 1)]


def apply_storage_data_date(payload: dict, data_date: str | None) -> dict:
    if not data_date:
        return payload
    payload = {**payload}
    payload["meta"] = {**payload.get("meta", {})}
    source_data_date = payload["meta"].get("data_date", "")
    if source_data_date and source_data_date != data_date:
        payload["meta"]["source_data_date"] = source_data_date
    payload["meta"]["data_date"] = data_date
    return payload


def fetch_all(project_root: Path = PROJECT_ROOT, *, discover: bool = True, limit: int | None = None, data_date: str | None = None, force_data_date: bool = False) -> str:
    etfs = discover_active_etfs() if discover else load_config_etfs(project_root)
    if limit:
        etfs = etfs[:limit]
    if discover and not limit:
        write_discovered_config(project_root, etfs)

    fetched_dates: list[str] = []
    seen_dates: list[str] = []
    for etf in etfs:
        if not etf.get("enabled", True):
            continue
        code = etf["etf_code"]
        print(f"Fetching {code} {etf.get('etf_name', '')}...", flush=True)
        try:
            payload = fetch_holdings(code)
        except Exception as exc:
            error_payload = {
                "meta": {
                    "etf_code": code,
                    "etf_name": etf.get("etf_name", ""),
                    "data_date": "",
                    "run_date": "",
                    "source_status": "failed",
                    "source_url": etf.get("source_url", ""),
                    "holdings_count": 0,
                    "error": str(exc),
                },
                "holdings": [],
            }
            write_json(project_root / "data" / "errors" / f"{code}.json", error_payload)
            print(f"  failed: {exc}", flush=True)
            continue

        if not payload.get("holdings"):
            payload["meta"]["error"] = "No holdings parsed from source page."
            write_json(project_root / "data" / "errors" / f"{code}.json", payload)
            print("  skipped: no holdings parsed", flush=True)
            continue

        source_data_date = payload["meta"]["data_date"]
        seen_dates.append(source_data_date)
        if data_date and source_data_date != data_date and not force_data_date:
            print(f"  using source date {source_data_date}; requested {data_date} was not available", flush=True)
            data_date_to_store = source_data_date
        else:
            data_date_to_store = data_date
        payload = apply_storage_data_date(payload, data_date_to_store)
        payload_data_date = payload["meta"]["data_date"]
        previous = previous_payload(project_root, data_date=payload_data_date, etf_code=code)
        payload = apply_diff(payload, previous)
        write_json(project_root / "data" / "normalized" / payload_data_date / f"{code}.json", payload)
        fetched_dates.append(payload_data_date)
        print(f"  ok: {payload_data_date} {len(payload['holdings'])} holdings", flush=True)

    if not fetched_dates:
        if seen_dates:
            return Counter(seen_dates).most_common(1)[0][0]
        raise RuntimeError("No ETF holdings were fetched successfully.")

    latest_date = Counter(fetched_dates).most_common(1)[0][0]
    write_matrices(project_root, data_date=latest_date)
    write_rankings_from_data(project_root, data_date=latest_date)
    write_search_index(project_root, data_date=latest_date)
    write_stock_history(project_root, data_date=latest_date)
    copy_to_public(project_root, data_date=latest_date)
    return latest_date


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover active ETFs and fetch daily holdings automatically.")
    parser.add_argument("--source", choices=["etfinfo", "reference"], default="etfinfo", help="Choose ETFInfo crawler or the reference Blogspot/GAS data source.")
    parser.add_argument("--no-discover", action="store_true", help="Use config/etfs.json instead of discovering ETFInfo list.")
    parser.add_argument("--limit", type=int, help="Fetch only the first N ETFs, useful for smoke tests.")
    parser.add_argument("--data-date", type=parse_data_date, help="Expected source snapshot date in YYYY-MM-DD format.")
    parser.add_argument("--force-data-date", action="store_true", help="Force storing the crawled snapshot under --data-date even when the source snapshot date differs.")
    parser.add_argument("--backfill-start", type=parse_data_date, help="First YYYY-MM-DD date to backfill with the crawler.")
    parser.add_argument("--backfill-end", type=parse_data_date, help="Last YYYY-MM-DD date to backfill with the crawler.")
    args = parser.parse_args()

    if args.source == "reference":
        if args.data_date or args.backfill_start or args.backfill_end:
            parser.error("--data-date, --force-data-date and --backfill-* are only supported with --source etfinfo.")
        latest_date = import_reference(PROJECT_ROOT)
    elif args.backfill_start or args.backfill_end:
        if not args.backfill_start or not args.backfill_end:
            parser.error("--backfill-start and --backfill-end must be used together.")
        dates = backfill_dates(args.backfill_start.isoformat(), args.backfill_end.isoformat())
        latest_date = ""
        for target_date in dates:
            latest_date = fetch_all(PROJECT_ROOT, discover=not args.no_discover, limit=args.limit, data_date=target_date, force_data_date=args.force_data_date)
    else:
        latest_date = fetch_all(PROJECT_ROOT, discover=not args.no_discover, limit=args.limit, data_date=args.data_date.isoformat() if args.data_date else None, force_data_date=args.force_data_date)
    print(f"Daily auto pipeline complete for {latest_date}")


if __name__ == "__main__":
    main()
