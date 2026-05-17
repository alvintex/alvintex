from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from scripts.normalize_holdings import build_note, round_lot


def apply_diff(current: dict[str, Any], previous: dict[str, Any] | None) -> dict[str, Any]:
    if not previous:
        for holding in current.get("holdings", []):
            holding["source_change_text"] = holding.get("source_change_text") or "持平"
            holding["system_change_type"] = holding.get("system_change_type") or "持平"
        return current

    previous_by_id = {row["stock_id"]: row for row in previous.get("holdings", [])}
    current_by_id = {row["stock_id"]: row for row in current.get("holdings", [])}
    output = []

    for holding in current.get("holdings", []):
        old = previous_by_id.get(holding["stock_id"])
        if not old:
            shares_change = holding["shares"]
            weight_change = holding["weight_pct"]
            change_type = "新增"
        else:
            shares_change = holding["shares"] - old["shares"]
            weight_change = round(holding["weight_pct"] - old["weight_pct"], 2)
            if shares_change > 0:
                change_type = "加碼"
            elif shares_change < 0:
                change_type = "減碼"
            else:
                change_type = "持平"
        holding = {**holding}
        holding["weight_change_pct"] = weight_change
        holding["shares_change"] = shares_change
        holding["shares_change_lot"] = round_lot(shares_change)
        holding["source_change_text"] = change_type
        holding["system_change_type"] = change_type
        holding["note"] = build_note(weight_change, shares_change, change_type, change_type)
        output.append(holding)

    for stock_id, old in previous_by_id.items():
        if stock_id in current_by_id:
            continue
        removed = {**old}
        removed["weight_pct"] = 0
        removed["shares"] = 0
        removed["shares_lot"] = 0
        removed["weight_change_pct"] = round(0 - old["weight_pct"], 2)
        removed["shares_change"] = -old["shares"]
        removed["shares_change_lot"] = round_lot(-old["shares"])
        removed["source_change_text"] = "出清"
        removed["system_change_type"] = "出清"
        removed["note"] = ""
        output.append(removed)

    current = {**current}
    current["meta"] = {**current.get("meta", {})}
    current["meta"]["compare_date"] = previous.get("meta", {}).get("data_date")
    current["meta"]["holdings_count"] = len(output)
    current["holdings"] = sorted(output, key=lambda row: (-row["weight_pct"], row["stock_id"]))
    return current


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def previous_payload(project_root: Path, *, data_date: str, etf_code: str) -> dict[str, Any] | None:
    base = project_root / "data" / "normalized"
    dates = sorted(path.name for path in base.iterdir() if path.is_dir() and path.name < data_date) if base.exists() else []
    for candidate in reversed(dates):
        path = base / candidate / f"{etf_code}.json"
        if path.exists():
            return load_json(path)
    return None


def apply_diff_to_file(project_root: Path, *, data_date: str, etf_code: str) -> Path:
    path = project_root / "data" / "normalized" / data_date / f"{etf_code}.json"
    current = load_json(path)
    previous = previous_payload(project_root, data_date=data_date, etf_code=etf_code)
    write_json(path, apply_diff(current, previous))
    return path
