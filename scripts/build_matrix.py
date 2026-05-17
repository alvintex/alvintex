from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.normalize_holdings import DEFAULT_DATA_DATE, PROJECT_ROOT


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def build_matrices(project_root: Path = PROJECT_ROOT, *, data_date: str = DEFAULT_DATA_DATE) -> tuple[dict[str, Any], dict[str, Any]]:
    normalized_dir = project_root / "data" / "normalized" / data_date
    stock_rows: dict[str, dict[str, Any]] = {}
    etf_codes: set[str] = set()

    for path in normalized_dir.glob("*.json"):
        payload = load_json(path)
        etf_code = payload["meta"].get("etf_code", path.stem)
        etf_codes.add(etf_code)
        for holding in payload.get("holdings", []):
            stock_id = holding["stock_id"]
            row = stock_rows.setdefault(
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
                "shares_change": holding["shares_change"],
                "shares_change_lot": holding["shares_change_lot"],
                "change_type": holding["system_change_type"],
            }

    holding_rows = []
    change_rows = []
    for row in stock_rows.values():
        etfs = row["etfs"]
        weights = [item["weight_pct"] for item in etfs.values()]
        holding_rows.append(
            {
                **row,
                "held_etf_count": len(etfs),
                "avg_weight_pct": round(sum(weights) / len(weights), 2) if weights else 0,
                "total_shares": sum(item["shares"] for item in etfs.values()),
                "total_lots": round(sum(item["shares_lot"] for item in etfs.values()), 1),
            }
        )

        counts = {
            "add_count": sum(1 for item in etfs.values() if item["change_type"] == "加碼"),
            "reduce_count": sum(1 for item in etfs.values() if item["change_type"] == "減碼"),
            "new_count": sum(1 for item in etfs.values() if item["change_type"] == "新增"),
            "removed_count": sum(1 for item in etfs.values() if item["change_type"] == "出清"),
            "unchanged_count": sum(1 for item in etfs.values() if item["change_type"] == "持平"),
        }
        dominant_signal = "持平"
        if counts["add_count"] >= 3:
            dominant_signal = "多檔加碼"
        elif counts["new_count"] > 0:
            dominant_signal = "新進持股"
        elif counts["reduce_count"] > 0:
            dominant_signal = "減碼觀察"
        change_rows.append(
            {
                "stock_id": row["stock_id"],
                "stock_name": row["stock_name"],
                "stock_display": row["stock_display"],
                **counts,
                "net_etf_change_score": counts["add_count"] + counts["new_count"] - counts["reduce_count"] - counts["removed_count"],
                "total_shares_change": sum(item["shares_change"] for item in etfs.values()),
                "dominant_signal": dominant_signal,
                "etfs": {etf_code: item["change_type"] for etf_code, item in etfs.items()},
            }
        )

    holding_payload = {
        "meta": {"data_date": data_date, "etf_count": len(etf_codes), "stock_count": len(holding_rows)},
        "rows": sorted(holding_rows, key=lambda row: (-row["held_etf_count"], -row["avg_weight_pct"], row["stock_id"])),
    }
    change_payload = {
        "meta": {"data_date": data_date, "etf_count": len(etf_codes), "stock_count": len(change_rows)},
        "rows": sorted(change_rows, key=lambda row: (-row["add_count"], -row["new_count"], row["stock_id"])),
    }
    return holding_payload, change_payload


def write_matrices(project_root: Path = PROJECT_ROOT, *, data_date: str = DEFAULT_DATA_DATE) -> tuple[Path, Path]:
    holding, change = build_matrices(project_root, data_date=data_date)
    output_dir = project_root / "data" / "matrix" / data_date
    output_dir.mkdir(parents=True, exist_ok=True)
    holding_path = output_dir / "holding_matrix.json"
    change_path = output_dir / "change_matrix.json"
    holding_path.write_text(json.dumps(holding, ensure_ascii=False, indent=2), encoding="utf-8")
    change_path.write_text(json.dumps(change, ensure_ascii=False, indent=2), encoding="utf-8")
    return holding_path, change_path


def main() -> None:
    parser = argparse.ArgumentParser(description="Build holding and change matrix JSON.")
    parser.add_argument("--data-date", default=DEFAULT_DATA_DATE)
    args = parser.parse_args()

    for path in write_matrices(PROJECT_ROOT, data_date=args.data_date):
        print(path)


if __name__ == "__main__":
    main()
