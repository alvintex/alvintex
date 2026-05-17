from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.build_matrix import write_matrices
from scripts.build_rankings import write_rankings
from scripts.build_search_index import write_search_index
from scripts.build_stock_history import write_stock_history
from scripts.normalize_holdings import DEFAULT_DATA_DATE, DEFAULT_ETF_CODE, PROJECT_ROOT, write_normalized


CONFIG_ETFS = {
    "etfs": [
        {"etf_code": "00980A", "etf_name": "00980A 野村", "issuer": "野村", "enabled": True, "priority": 1, "source_type": "manual_or_web", "source_url": "", "parser": "pending", "note": "待建立資料來源"},
        {"etf_code": "00981A", "etf_name": "00981A 統一", "issuer": "統一", "enabled": True, "priority": 2, "source_type": "manual_file", "source_url": "", "parser": "manual_text_parser", "note": "v1.1 優先驗證"},
        {"etf_code": "00982A", "etf_name": "00982A 群益", "issuer": "群益", "enabled": True, "priority": 3, "source_type": "manual_or_web", "source_url": "", "parser": "pending", "note": "待建立資料來源"},
        {"etf_code": "00984A", "etf_name": "00984A 安聯", "issuer": "安聯", "enabled": True, "priority": 4, "source_type": "manual_or_web", "source_url": "", "parser": "pending", "note": "待建立資料來源"},
        {"etf_code": "00985A", "etf_name": "00985A 復華", "issuer": "復華", "enabled": True, "priority": 5, "source_type": "manual_or_web", "source_url": "", "parser": "pending", "note": "待建立資料來源"},
        {"etf_code": "00987A", "etf_name": "00987A 國泰", "issuer": "國泰", "enabled": True, "priority": 6, "source_type": "manual_or_web", "source_url": "", "parser": "pending", "note": "待建立資料來源"},
        {"etf_code": "00991A", "etf_name": "00991A 台新", "issuer": "台新", "enabled": True, "priority": 7, "source_type": "manual_or_web", "source_url": "", "parser": "pending", "note": "待建立資料來源"},
        {"etf_code": "00992A", "etf_name": "00992A 第一金", "issuer": "第一金", "enabled": True, "priority": 8, "source_type": "manual_or_web", "source_url": "", "parser": "pending", "note": "00981A 對照組"},
        {"etf_code": "00994A", "etf_name": "00994A 兆豐", "issuer": "兆豐", "enabled": True, "priority": 9, "source_type": "manual_or_web", "source_url": "", "parser": "pending", "note": "待建立資料來源"},
        {"etf_code": "00995A", "etf_name": "00995A 中信", "issuer": "中信", "enabled": True, "priority": 10, "source_type": "manual_or_web", "source_url": "", "parser": "pending", "note": "待建立資料來源"},
        {"etf_code": "00403A", "etf_name": "00403A", "issuer": "待補", "enabled": False, "priority": 11, "source_type": "pending", "source_url": "", "parser": "pending", "note": "預留追蹤"},
    ]
}

CONFIG_RULES = {
    "change_rules": {"primary_basis": "shares_change", "use_weight_change_as_secondary": True},
    "ranking_rules": {
        "strong_add_lot_threshold": 500,
        "strong_new_lot_threshold": 500,
        "dump_warning_lot_threshold": 300,
        "core_weight_pct_threshold": 3,
        "crowded_holding_etf_count_threshold": 7,
        "consensus_add_etf_count_threshold": 3,
    },
    "display_rules": {"decimal_places_weight": 2, "decimal_places_lot": 1, "show_inconsistent_warning": True},
}


def write_config(project_root: Path) -> None:
    config_dir = project_root / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "etfs.json").write_text(json.dumps(CONFIG_ETFS, ensure_ascii=False, indent=2), encoding="utf-8")
    (config_dir / "rules.json").write_text(json.dumps(CONFIG_RULES, ensure_ascii=False, indent=2), encoding="utf-8")


def copy_to_public(project_root: Path, *, data_date: str, etf_code: str = DEFAULT_ETF_CODE) -> None:
    latest_dir = project_root / "public" / "data" / "latest"
    latest_dir.mkdir(parents=True, exist_ok=True)
    for old_json in latest_dir.glob("*.json"):
        old_json.unlink()
    normalized_dir = project_root / "data" / "normalized" / data_date
    if normalized_dir.exists():
        for normalized_file in normalized_dir.glob("*.json"):
            shutil.copyfile(normalized_file, latest_dir / normalized_file.name)
    config_path = project_root / "config" / "etfs.json"
    if config_path.exists():
        config = json.loads(config_path.read_text(encoding="utf-8"))
        available_codes = {path.stem for path in normalized_dir.glob("*.json")} if normalized_dir.exists() else set()
        for etf in config.get("etfs", []):
            etf["source_status"] = "updated" if etf.get("etf_code") in available_codes else "not_available"
        (latest_dir / "etfs.json").write_text(json.dumps(config, ensure_ascii=False, indent=2), encoding="utf-8")

    copies = {
        project_root / "data" / "rankings" / data_date / "rankings.json": latest_dir / "rankings.json",
        project_root / "data" / "matrix" / data_date / "holding_matrix.json": latest_dir / "holding_matrix.json",
        project_root / "data" / "matrix" / data_date / "change_matrix.json": latest_dir / "change_matrix.json",
        project_root / "data" / "search" / data_date / "stock_index.json": latest_dir / "stock_index.json",
        project_root / "data" / "history" / data_date / "stock_history.json": latest_dir / "stock_history.json",
    }
    for source, target in copies.items():
        if source.exists():
            shutil.copyfile(source, target)

    manifest = {"data_date": data_date, "default_etf": etf_code, "latest_path": "data/latest"}
    (latest_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")


def run(project_root: Path = PROJECT_ROOT, *, data_date: str = DEFAULT_DATA_DATE) -> None:
    write_config(project_root)
    write_normalized(
        project_root / "00981A_單檔持股清單.txt",
        data_date=data_date,
        etf_code=DEFAULT_ETF_CODE,
        output_root=project_root / "data" / "normalized",
    )
    write_rankings(project_root, data_date=data_date)
    write_matrices(project_root, data_date=data_date)
    write_search_index(project_root, data_date=data_date)
    write_stock_history(project_root, data_date=data_date)
    copy_to_public(project_root, data_date=data_date)


def main() -> None:
    parser = argparse.ArgumentParser(description="Run local manual-data MVP pipeline.")
    parser.add_argument("--data-date", default=DEFAULT_DATA_DATE)
    args = parser.parse_args()

    run(PROJECT_ROOT, data_date=args.data_date)
    print(f"Local data pipeline complete for {args.data_date}")


if __name__ == "__main__":
    main()
