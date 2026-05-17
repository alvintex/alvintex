from __future__ import annotations

import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree


WORD_NS = {"w": "http://schemas.openxmlformats.org/wordprocessingml/2006/main"}


def read_docx_cells(path: Path) -> list[str]:
    with zipfile.ZipFile(path) as archive:
        xml_text = archive.read("word/document.xml")
    root = ElementTree.fromstring(xml_text)
    cells: list[str] = []
    for paragraph in root.findall(".//w:p", WORD_NS):
        text = "".join(node.text or "" for node in paragraph.findall(".//w:t", WORD_NS)).strip()
        if text:
            cells.append(text)
    return cells


def parse_stock_display(value: str) -> tuple[str, str, str]:
    text = value.strip()
    match = re.match(r"^(?P<name>.+?)\((?P<id>[0-9A-Za-z]+)\)$", text)
    if not match:
        return text, "", text
    stock_name = match.group("name").strip()
    stock_id = match.group("id").strip()
    return stock_name, stock_id, f"{stock_name}({stock_id})"


def parse_number(value: str, *, as_int: bool = False) -> int | float:
    text = str(value).replace(",", "").replace("%", "").strip()
    if text in {"", "-", "—"}:
        return 0 if as_int else 0.0
    number = float(text)
    return int(round(number)) if as_int else number


def round_lot(shares: int | float) -> int | float:
    lots = float(shares) / 1000
    return int(lots) if lots.is_integer() else round(lots, 1)
