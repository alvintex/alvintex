import json
import shutil
from pathlib import Path

from scripts.run_daily_local import run


SOURCE_FILES = [
    "00981A_單檔持股清單.txt",
    "加碼榜.docx",
    "新增榜.docx",
    "減碼榜.docx",
    "出清榜.docx",
    "持平榜.docx",
    "持有總覽.docx",
    "2330_個股搜尋.docx",
]


def test_run_daily_local_writes_data_layers_and_public_latest(tmp_path):
    for filename in SOURCE_FILES:
        shutil.copyfile(Path(filename), tmp_path / filename)

    run(tmp_path, data_date="2026-05-14")

    normalized = json.loads((tmp_path / "data/normalized/2026-05-14/00981A.json").read_text(encoding="utf-8"))
    rankings = json.loads((tmp_path / "public/data/latest/rankings.json").read_text(encoding="utf-8"))
    matrix = json.loads((tmp_path / "public/data/latest/holding_matrix.json").read_text(encoding="utf-8"))
    search = json.loads((tmp_path / "public/data/latest/stock_index.json").read_text(encoding="utf-8"))

    assert normalized["meta"]["holdings_count"] == 46
    assert rankings["rankings"]["add_rank"][0]["stock_display"] == "聯電(2303)"
    assert matrix["rows"][0]["held_etf_count"] >= 1
    stock_2330 = next(row for row in search["rows"] if row["stock_id"] == "2330")
    assert stock_2330["held_etf_count"] >= 10
    assert (tmp_path / "config/etfs.json").exists()
    assert (tmp_path / "config/rules.json").exists()
