from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import date
from pathlib import Path
from typing import Any


DEFAULT_DATA_DATE = "2026-05-14"
DEFAULT_ETF_CODE = "00981A"
PROJECT_ROOT = Path(__file__).resolve().parents[1]

CHANGE_ALIASES = {
    "新增持有": "新增",
    "新增": "新增",
    "加碼": "加碼",
    "減碼": "減碼",
    "出清": "出清",
    "刪除": "出清",
    "持平": "持平",
}


def parse_number(value: Any, *, as_int: bool = False) -> int | float:
    text = str(value).strip().replace(",", "").replace("%", "")
    if text in {"", "-", "—"}:
        return 0 if as_int else 0.0
    number = float(text)
    return int(round(number)) if as_int else number


def round_lot(shares: int) -> int | float:
    lots = shares / 1000
    return int(lots) if lots.is_integer() else round(lots, 1)


def parse_stock_display(value: str) -> dict[str, str]:
    text = value.strip()
    match = re.match(r"^(?P<name>.+?)\((?P<id>[0-9A-Za-z]+)\)$", text)
    if not match:
        return {"stock_name": text, "stock_id": "", "stock_display": text}

    stock_name = match.group("name").strip()
    stock_id = match.group("id").strip()
    return {
        "stock_name": stock_name,
        "stock_id": stock_id,
        "stock_display": f"{stock_name}({stock_id})",
    }


def normalize_change_type(value: str) -> str:
    text = str(value).strip()
    return CHANGE_ALIASES.get(text, text)


def infer_change_type(source_change: str, shares_change: int) -> str:
    normalized = normalize_change_type(source_change)
    if normalized in {"新增", "出清"}:
        return normalized
    if shares_change > 0:
        return "加碼"
    if shares_change < 0:
        return "減碼"
    return "持平"


def build_note(weight_change_pct: float, shares_change: int, source_change: str, system_change: str) -> str:
    notes: list[str] = []
    if weight_change_pct > 0 and shares_change < 0:
        notes.append("比例增加但股數減少，判斷以股數為準")
    elif weight_change_pct < 0 and shares_change > 0:
        notes.append("比例減少但股數增加，判斷以股數為準")
    elif weight_change_pct != 0 and shares_change == 0:
        notes.append("股數持平但比例變動")

    if normalize_change_type(source_change) != system_change:
        notes.append("原始異動與系統判斷不一致")
    return "；".join(notes)


def build_holding(row: dict[str, str]) -> dict[str, Any]:
    stock = parse_stock_display(row["個股名稱"])
    weight_pct = parse_number(row["投資比例(%)"])
    shares = parse_number(row["持有股數"], as_int=True)
    weight_change_pct = parse_number(row["比例增減(%)"])
    shares_change = parse_number(row["股數增減"], as_int=True)
    source_change = normalize_change_type(row["股數異動"])
    system_change = infer_change_type(source_change, shares_change)

    return {
        **stock,
        "weight_pct": weight_pct,
        "shares": shares,
        "shares_lot": round_lot(shares),
        "weight_change_pct": weight_change_pct,
        "shares_change": shares_change,
        "shares_change_lot": round_lot(shares_change),
        "source_change_text": source_change,
        "system_change_type": system_change,
        "note": build_note(weight_change_pct, shares_change, source_change, system_change),
    }


def read_holdings_text(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8-sig")
    reader = csv.DictReader(text.splitlines(), delimiter="，")
    return [build_holding(row) for row in reader if row.get("個股名稱")]


def build_normalized_payload(
    holdings: list[dict[str, Any]],
    *,
    data_date: str,
    etf_code: str,
    run_date: str | None = None,
    source_url: str = "",
) -> dict[str, Any]:
    return {
        "meta": {
            "etf_code": etf_code,
            "data_date": data_date,
            "run_date": run_date or date.today().isoformat(),
            "source_status": "updated",
            "source_url": source_url,
            "holdings_count": len(holdings),
        },
        "holdings": holdings,
    }


def write_normalized(
    source: Path,
    *,
    data_date: str = DEFAULT_DATA_DATE,
    etf_code: str = DEFAULT_ETF_CODE,
    output_root: Path | None = None,
) -> Path:
    holdings = read_holdings_text(source)
    payload = build_normalized_payload(holdings, data_date=data_date, etf_code=etf_code)
    output_dir = (output_root or PROJECT_ROOT / "data" / "normalized") / data_date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{etf_code}.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Normalize a manual ETF holdings text file.")
    parser.add_argument("--source", default=str(PROJECT_ROOT / "00981A_單檔持股清單.txt"))
    parser.add_argument("--data-date", default=DEFAULT_DATA_DATE)
    parser.add_argument("--etf-code", default=DEFAULT_ETF_CODE)
    args = parser.parse_args()

    output_path = write_normalized(Path(args.source), data_date=args.data_date, etf_code=args.etf_code)
    print(output_path)


if __name__ == "__main__":
    main()
