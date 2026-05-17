from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.docx_utils import parse_number, parse_stock_display, read_docx_cells
from scripts.normalize_holdings import DEFAULT_DATA_DATE, DEFAULT_ETF_CODE, PROJECT_ROOT


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_search_index(project_root: Path = PROJECT_ROOT, *, data_date: str = DEFAULT_DATA_DATE) -> dict[str, Any]:
    normalized_dir = project_root / "data" / "normalized" / data_date
    rows: dict[str, dict[str, Any]] = {}

    for path in normalized_dir.glob("*.json"):
        payload = load_json(path)
        etf_code = payload["meta"].get("etf_code", path.stem)
        for holding in payload.get("holdings", []):
            stock_id = holding["stock_id"]
            item = rows.setdefault(
                stock_id,
                {
                    "stock_id": stock_id,
                    "stock_name": holding["stock_name"],
                    "stock_display": holding["stock_display"],
                    "keywords": [],
                    "etfs": {},
                },
            )
            item["etfs"][etf_code] = {
                "weight_pct": holding["weight_pct"],
                "shares": holding["shares"],
                "shares_lot": holding["shares_lot"],
                "weight_change_pct": holding["weight_change_pct"],
                "shares_change": holding["shares_change"],
                "shares_change_lot": holding["shares_change_lot"],
                "change_type": holding["system_change_type"],
                "note": holding["note"],
            }

    stock_docx = project_root / "2330_個股搜尋.docx"
    if stock_docx.exists():
        cells = read_docx_cells(stock_docx)
        body = cells[4:]
        for index in range(0, len(body), 4):
            group = body[index : index + 4]
            if len(group) != 4:
                continue
            etf_code, stock_display, weight, change = group
            stock_name, stock_id, normalized_display = parse_stock_display(stock_display)
            if not stock_id:
                continue
            item = rows.setdefault(
                stock_id,
                {
                    "stock_id": stock_id,
                    "stock_name": stock_name,
                    "stock_display": normalized_display,
                    "keywords": [],
                    "etfs": {},
                },
            )
            item["etfs"].setdefault(
                etf_code,
                {
                    "weight_pct": parse_number(weight),
                    "shares": 0,
                    "shares_lot": 0,
                    "weight_change_pct": 0,
                    "shares_change": 0,
                    "shares_change_lot": 0,
                    "change_type": change.strip(),
                    "note": "來源：2330_個股搜尋.docx，第一版未含股數",
                },
            )

    for item in rows.values():
        item["held_etf_count"] = len(item["etfs"])
        weights = [etf["weight_pct"] for etf in item["etfs"].values()]
        item["avg_weight_pct"] = round(sum(weights) / len(weights), 2) if weights else 0
        item["total_lots"] = round(sum(etf["shares_lot"] for etf in item["etfs"].values()), 1)
        item["add_count"] = sum(1 for etf in item["etfs"].values() if etf["change_type"] == "加碼")
        item["reduce_count"] = sum(1 for etf in item["etfs"].values() if etf["change_type"] == "減碼")
        item["new_count"] = sum(1 for etf in item["etfs"].values() if etf["change_type"] == "新增")
        item["removed_count"] = sum(1 for etf in item["etfs"].values() if etf["change_type"] == "出清")
        item["keywords"] = [item["stock_id"], item["stock_name"], item["stock_display"]]

    return {
        "meta": {"data_date": data_date, "stock_count": len(rows), "etf_code": DEFAULT_ETF_CODE},
        "rows": sorted(rows.values(), key=lambda row: row["stock_id"]),
    }


def write_search_index(project_root: Path = PROJECT_ROOT, *, data_date: str = DEFAULT_DATA_DATE) -> Path:
    payload = build_search_index(project_root, data_date=data_date)
    output_dir = project_root / "data" / "search" / data_date
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / "stock_index.json"
    output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return output_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build stock search index JSON.")
    parser.add_argument("--data-date", default=DEFAULT_DATA_DATE)
    args = parser.parse_args()

    print(write_search_index(PROJECT_ROOT, data_date=args.data_date))


if __name__ == "__main__":
    main()
