from __future__ import annotations

import argparse
import json
import re
import sys
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.docx_utils import parse_number, parse_stock_display
from scripts.build_matrix import write_matrices
from scripts.normalize_holdings import PROJECT_ROOT, round_lot
from scripts.run_daily_local import copy_to_public


API_URL = "https://script.google.com/macros/s/AKfycbz9NY3pwbllAGLFsiUa35K75SpcXwJrJIhqzQD0kpBGIGFRbBGned69qMze77cha0V9/exec"
API_KEY = "ETF_Tracker_888_Security"
REFERENCE_ETFS = ["00980A", "00981A", "00982A", "00984A", "00985A", "00987A", "00992A", "00991A", "00994A", "00995A"]


def fetch_reference_payload(kind: str) -> dict[str, Any]:
    query = urllib.parse.urlencode({"type": kind, "key": API_KEY})
    with urllib.request.urlopen(f"{API_URL}?{query}", timeout=45) as response:
        return json.loads(response.read().decode("utf-8"))


def data_date_from_update_time(update_time: str | None) -> str:
    text = update_time or ""
    match = re.search(r"(20\d{2})/(\d{2})/(\d{2})", text)
    if match:
        return f"{match.group(1)}-{match.group(2)}-{match.group(3)}"
    return date.today().isoformat()


def choose_reference_data_date(search_payload: dict[str, Any], ranking_payloads: dict[str, dict[str, Any]]) -> str:
    for payload in (ranking_payloads.get("all", {}), search_payload):
        update_time = payload.get("updateTime")
        if update_time and re.search(r"20\d{2}/\d{2}/\d{2}", update_time):
            return data_date_from_update_time(update_time)
    return date.today().isoformat()


def normalize_change_type(text: str) -> str:
    if text == "新增持有":
        return "新增"
    if text == "刪除":
        return "出清"
    return text or "持平"


def normalize_reference_search_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    normalized = []
    for row in rows:
        stock_name, stock_id, stock_display = parse_stock_display(str(row.get("個股名稱", "")))
        if not stock_id:
            continue
        shares = parse_number(row.get("持有股數", 0), as_int=True)
        shares_change = parse_number(row.get("股數增減", 0), as_int=True)
        change_type = normalize_change_type(str(row.get("股數異動", "")))
        normalized.append(
            {
                "etf_code": str(row.get("ETF代號", "")).strip(),
                "stock_id": stock_id,
                "stock_name": stock_name,
                "stock_display": stock_display,
                "weight_pct": parse_number(row.get("投資比例(%)", 0)),
                "shares": shares,
                "shares_lot": round_lot(shares),
                "weight_change_pct": parse_number(row.get("比例增減(%)", 0)),
                "shares_change": shares_change,
                "shares_change_lot": round_lot(shares_change),
                "source_change_text": change_type,
                "system_change_type": change_type,
                "note": "來源：參考站 Google Apps Script API",
            }
        )
    return normalized


def build_search_index_from_reference(rows: list[dict[str, Any]], *, data_date: str) -> dict[str, Any]:
    stock_map: dict[str, dict[str, Any]] = {}
    for row in normalize_reference_search_rows(rows):
        item = stock_map.setdefault(
            row["stock_id"],
            {
                "stock_id": row["stock_id"],
                "stock_name": row["stock_name"],
                "stock_display": row["stock_display"],
                "keywords": [],
                "etfs": {},
            },
        )
        item["etfs"][row["etf_code"]] = {
            "weight_pct": row["weight_pct"],
            "shares": row["shares"],
            "shares_lot": row["shares_lot"],
            "weight_change_pct": row["weight_change_pct"],
            "shares_change": row["shares_change"],
            "shares_change_lot": row["shares_change_lot"],
            "change_type": row["system_change_type"],
            "note": row["note"],
        }

    for item in stock_map.values():
        etfs = item["etfs"].values()
        weights = [etf["weight_pct"] for etf in etfs]
        item["held_etf_count"] = len(item["etfs"])
        item["avg_weight_pct"] = round(sum(weights) / len(weights), 2) if weights else 0
        item["total_lots"] = round(sum(etf["shares_lot"] for etf in item["etfs"].values()), 1)
        item["add_count"] = sum(1 for etf in item["etfs"].values() if etf["change_type"] == "加碼")
        item["reduce_count"] = sum(1 for etf in item["etfs"].values() if etf["change_type"] == "減碼")
        item["new_count"] = sum(1 for etf in item["etfs"].values() if etf["change_type"] == "新增")
        item["removed_count"] = sum(1 for etf in item["etfs"].values() if etf["change_type"] == "出清")
        item["keywords"] = [item["stock_id"], item["stock_name"], item["stock_display"]]

    return {"meta": {"data_date": data_date, "stock_count": len(stock_map), "source": "reference_api"}, "rows": sorted(stock_map.values(), key=lambda row: row["stock_id"])}


def build_normalized_by_etf(rows: list[dict[str, Any]], *, data_date: str) -> dict[str, dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in normalize_reference_search_rows(rows):
        grouped.setdefault(row["etf_code"], []).append({key: value for key, value in row.items() if key != "etf_code"})
    return {
        code: {
            "meta": {
                "etf_code": code,
                "data_date": data_date,
                "run_date": date.today().isoformat(),
                "source_status": "updated",
                "source_url": API_URL,
                "holdings_count": len(holdings),
            },
            "holdings": holdings,
        }
        for code, holdings in grouped.items()
    }


def stock_base(value: str) -> dict[str, str]:
    stock_name, stock_id, stock_display = parse_stock_display(value)
    return {"stock_id": stock_id, "stock_name": stock_name, "stock_display": stock_display}


def reference_rankings_from_api_payloads(payloads: dict[str, dict[str, Any]], *, data_date: str) -> dict[str, Any]:
    all_rows = [
        {
            **stock_base(row["個股名稱"]),
            "held_etf_count": parse_number(row.get("持有ETF數量", 0), as_int=True),
            "avg_weight_pct": parse_number(row.get("平均比例(%)", 0)),
            "total_shares": parse_number(row.get("合計總股數", 0), as_int=True),
            "total_lots": parse_number(row.get("合計總張數", 0)),
        }
        for row in payloads.get("all", {}).get("data", [])
    ]
    add_rows = [
        {
            **stock_base(row["個股名稱"]),
            "add_etf_count": parse_number(row.get("加碼基金數", 0), as_int=True),
            "avg_weight_pct": parse_number(row.get("平均比例", 0)),
            "total_shares_change_lot": parse_number(row.get("合計加碼張數", 0)),
            "strong_add_flag": bool(row.get("強力加碼")),
            "flag_text": row.get("強力加碼", ""),
        }
        for row in payloads.get("plus", {}).get("data", [])
    ]
    new_rows = [
        {
            **stock_base(row["個股名稱"]),
            "total_weight_pct": parse_number(row.get("合計比例", 0)),
            "total_shares": parse_number(row.get("合計股數", 0), as_int=True),
            "total_weight_change_pct": parse_number(row.get("合計比例增減", 0)),
            "total_shares_change_lot": parse_number(row.get("合計張數增減", 0)),
            "strong_new_flag": bool(row.get("強力新寵") or row.get("強力新增")),
            "flag_text": row.get("強力新寵") or row.get("強力新增", ""),
        }
        for row in payloads.get("new", {}).get("data", [])
    ]
    reduce_rows = [
        {
            **stock_base(row["個股名稱"]),
            "total_weight_pct": parse_number(row.get("合計比例", 0)),
            "total_shares": parse_number(row.get("合計股數", 0), as_int=True),
            "total_weight_change_pct": parse_number(row.get("合計比例增減", 0)),
            "total_shares_change": parse_number(row.get("合計股數增減", 0), as_int=True),
            "total_shares_change_lot": round_lot(parse_number(row.get("合計股數增減", 0), as_int=True)),
            "dump_warning_flag": bool(row.get("倒貨警示")),
            "flag_text": row.get("倒貨警示", ""),
        }
        for row in payloads.get("minus", {}).get("data", [])
    ]
    removed_rows = [{**stock_base(row["個股名稱"]), "removed_etf_count": parse_number(row.get("出清基金數", 0), as_int=True)} for row in payloads.get("exit", {}).get("data", [])]
    unchanged_rows = [
        {
            **stock_base(row["個股名稱"]),
            "unchanged_etf_count": parse_number(row.get("續抱基金數", 0), as_int=True),
            "avg_weight_pct": parse_number(row.get("平均佔比", 0)),
            "total_lots": parse_number(row.get("合計持有張數", 0)),
            "core_holding_flag": bool(row.get("核心重倉")),
            "flag_text": row.get("核心重倉", ""),
        }
        for row in payloads.get("hold", {}).get("data", [])
    ]
    rankings = {
        "add_rank": add_rows,
        "new_rank": new_rows,
        "reduce_rank": reduce_rows,
        "removed_rank": removed_rows,
        "unchanged_rank": unchanged_rows,
        "most_held_rank": all_rows,
        "consensus_buy_rank": [row for row in add_rows if row["add_etf_count"] >= 3],
        "crowded_holding_rank": [row for row in all_rows if row["held_etf_count"] >= 7],
        "risk_reduce_rank": [row for row in reduce_rows if row["dump_warning_flag"]],
    }
    return {"meta": {"data_date": data_date, "source": "reference_api"}, "rankings": rankings}


def import_reference(project_root: Path = PROJECT_ROOT) -> str:
    search_payload = fetch_reference_payload("search")
    ranking_payloads = {kind: fetch_reference_payload(kind) for kind in ["all", "plus", "new", "minus", "exit", "hold"]}
    data_date = choose_reference_data_date(search_payload, ranking_payloads)
    rows = search_payload.get("data", [])
    for code, payload in build_normalized_by_etf(rows, data_date=data_date).items():
        output = project_root / "data" / "normalized" / data_date / f"{code}.json"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    write_matrices(project_root, data_date=data_date)

    rankings = reference_rankings_from_api_payloads(ranking_payloads, data_date=data_date)
    ranking_path = project_root / "data" / "rankings" / data_date / "rankings.json"
    ranking_path.parent.mkdir(parents=True, exist_ok=True)
    ranking_path.write_text(json.dumps(rankings, ensure_ascii=False, indent=2), encoding="utf-8")

    search_index = build_search_index_from_reference(rows, data_date=data_date)
    search_path = project_root / "data" / "search" / data_date / "stock_index.json"
    search_path.parent.mkdir(parents=True, exist_ok=True)
    search_path.write_text(json.dumps(search_index, ensure_ascii=False, indent=2), encoding="utf-8")

    etfs = [{"etf_code": code, "etf_name": code, "issuer": "", "enabled": True, "source_status": "updated", "priority": i + 1, "source_type": "reference_api", "source_url": API_URL, "parser": "reference_api"} for i, code in enumerate(REFERENCE_ETFS)]
    config_path = project_root / "config" / "etfs.json"
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(json.dumps({"etfs": etfs}, ensure_ascii=False, indent=2), encoding="utf-8")

    copy_to_public(project_root, data_date=data_date)
    return data_date


def main() -> None:
    parser = argparse.ArgumentParser(description="Import reference Blogspot/GAS active ETF data.")
    parser.parse_args()
    data_date = import_reference(PROJECT_ROOT)
    print(f"Reference data imported for {data_date}")


if __name__ == "__main__":
    main()
