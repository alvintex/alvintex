from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.normalize_holdings import PROJECT_ROOT, round_lot


BASE_URL = "https://www.etfinfo.tw"
ACTIVE_URL = f"{BASE_URL}/active?tab=etfs"
HEADERS = {"User-Agent": "Mozilla/5.0 active-etf-tracker/1.0"}


def html_to_lines(html_text: str) -> list[str]:
    text = re.sub(r"(?is)<(script|style).*?</\1>", "\n", html_text)
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"<[^>]+>", "\n", text)
    text = html.unescape(text)
    return [line.strip() for line in text.splitlines() if line.strip()]


def fetch_text(url: str, *, timeout: int = 12) -> str:
    request = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read().decode("utf-8", errors="replace")


def discover_active_etfs_from_html(html_text: str) -> list[dict[str, Any]]:
    lines = html_to_lines(html_text)
    etfs: list[dict[str, Any]] = []
    seen: set[str] = set()

    for index, line in enumerate(lines):
        match = re.fullmatch(r"(00[0-9]{3}[A-Z])", line)
        if not match:
            continue
        code = match.group(1)
        if code in seen:
            continue

        name_line = ""
        for candidate in lines[index + 1 : index + 5]:
            if candidate.startswith("主動"):
                name_line = candidate
                break
        if not name_line:
            continue

        name_part, issuer_part = split_name_issuer(name_line)
        if not issuer_part:
            issuer_part = infer_issuer(lines[index + 1 : index + 6])
        etfs.append(
            {
                "etf_code": code,
                "etf_name": name_part,
                "issuer": issuer_part,
                "enabled": True,
                "priority": len(etfs) + 1,
                "source_type": "etfinfo",
                "source_url": f"{BASE_URL}/etf/{code}/holdings",
                "parser": "etfinfo_holdings",
                "note": "由 ETF資訊網主動式 ETF 清單自動發現",
            }
        )
        seen.add(code)
    return etfs


def split_name_issuer(line: str) -> tuple[str, str]:
    text = re.sub(r"・.*$", "", line).strip()
    parts = text.split()
    if len(parts) >= 2:
        return " ".join(parts[:-1]).strip(), parts[-1].strip()
    return text, ""


def infer_issuer(lines: list[str]) -> str:
    issuer_map = ["中國信託", "第一金", "統一", "野村", "群益", "安聯", "復華", "台新", "兆豐", "摩根", "元大", "富邦", "國泰", "聯博"]
    for line in lines:
        clean = re.sub(r"[+−\-▼▲].*$", "", line).strip()
        clean = re.sub(r"・.*$", "", clean).strip()
        if clean in issuer_map:
            return clean
    for issuer in issuer_map:
        if any(line.startswith(issuer) for line in lines):
            return issuer
    return ""


def parse_number(text: str) -> float:
    return float(str(text).replace(",", "").replace("%", "").strip())


def parse_int(text: str) -> int:
    return int(round(parse_number(text)))


def parse_holdings_page(html_text: str, *, etf_code: str, source_url: str) -> dict[str, Any]:
    payload = parse_nuxt_payload(html_text, etf_code=etf_code, source_url=source_url)
    if payload:
        snapshot_date = extract_snapshot_date(html_text)
        if snapshot_date:
            payload["meta"]["data_date"] = snapshot_date
        return payload

    lines = html_to_lines(html_text)
    snapshot_date = ""
    etf_name = ""
    holdings: list[dict[str, Any]] = []

    for line in lines:
        if not etf_name and line.startswith("主動"):
            etf_name = line
        match = re.search(r"快照\s*(\d{4}-\d{2}-\d{2})", line)
        if match:
            snapshot_date = match.group(1)
            break
    if not snapshot_date:
        snapshot_date = date.today().isoformat()

    index = 0
    while index < len(lines):
        stock_match = re.fullmatch(r"(\d{4}[A-Z]?)", lines[index])
        if not stock_match:
            index += 1
            continue
        stock_id = stock_match.group(1)
        if index + 1 >= len(lines):
            break
        stock_name = lines[index + 1].strip()
        if not stock_name or re.search(r"常見問題|上一頁|下一頁|ETF資訊網", stock_name):
            index += 1
            continue

        weight = None
        shares = None
        lookaheads = lines[index + 2 : index + 10]
        for offset, lookahead in enumerate(lookaheads):
            weight_match = re.search(r"^(\d+(?:\.\d+)?)%\s*([0-9,]+)$", lookahead)
            if weight_match:
                weight = parse_number(weight_match.group(1))
                shares = parse_int(weight_match.group(2))
                break
            split_weight_match = re.fullmatch(r"(\d+(?:\.\d+)?)%", lookahead)
            if split_weight_match and offset + 1 < len(lookaheads):
                shares_match = re.fullmatch(r"[0-9,]+", lookaheads[offset + 1])
                if shares_match:
                    weight = parse_number(split_weight_match.group(1))
                    shares = parse_int(lookaheads[offset + 1])
                    break
        if weight is None or shares is None:
            index += 1
            continue

        holdings.append(
            {
                "stock_id": stock_id,
                "stock_name": stock_name,
                "stock_display": f"{stock_name}({stock_id})",
                "weight_pct": weight,
                "shares": shares,
                "shares_lot": round_lot(shares),
                "weight_change_pct": 0,
                "shares_change": 0,
                "shares_change_lot": 0,
                "source_change_text": "持平",
                "system_change_type": "持平",
                "source_status": "updated",
                "note": "",
            }
        )
        index += 2

    return {
        "meta": {
            "etf_code": etf_code,
            "etf_name": etf_name,
            "data_date": snapshot_date,
            "run_date": date.today().isoformat(),
            "source_status": "updated" if holdings else "failed",
            "source_url": source_url,
            "holdings_count": len(holdings),
        },
        "holdings": holdings,
    }


def extract_snapshot_date(html_text: str) -> str | None:
    latest_match = re.search(r"最新持股快照[（(](20\d{2}-\d{2}-\d{2})[）)]", html_text)
    if latest_match:
        return latest_match.group(1)
    lines = html_to_lines(html_text)
    for line in lines:
        match = re.search(r"(?:持股)?快照[：\s]*(20\d{2}-\d{2}-\d{2})", line)
        if match:
            return match.group(1)
    return None


def parse_nuxt_payload(payload_text: str, *, etf_code: str, source_url: str) -> dict[str, Any] | None:
    if '"weight"' not in payload_text or '"shares"' not in payload_text:
        return None
    data_date_match = re.search(r'"snapshotDate":\d+,"etfCode":\d+,"holdings":\d+|snapshotDate', payload_text)
    date_match = re.search(r'"(20\d{2}-\d{2}-\d{2})"', payload_text)
    snapshot_date = date_match.group(1) if date_match else date.today().isoformat()
    name_match = re.search(r'"name":\d+,[^}]*?},"([^"]+)"', payload_text)
    etf_name = name_match.group(1) if name_match else ""

    pattern = re.compile(
        r'\{"code":\d+,"name":\d+,"weight":\d+,"shares":\d+(?:,"unit":\d+)?(?:,"industry":\d+)?\},'
        r'"(?P<code>\d{4}[A-Z]?)","(?P<name>[^"]+)",(?P<weight>-?\d+(?:\.\d+)?),(?P<shares>\d+)'
    )
    holdings = []
    for match in pattern.finditer(payload_text):
        shares = int(match.group("shares"))
        weight = float(match.group("weight"))
        stock_id = match.group("code")
        stock_name = match.group("name")
        holdings.append(
            {
                "stock_id": stock_id,
                "stock_name": stock_name,
                "stock_display": f"{stock_name}({stock_id})",
                "weight_pct": weight,
                "shares": shares,
                "shares_lot": round_lot(shares),
                "weight_change_pct": 0,
                "shares_change": 0,
                "shares_change_lot": 0,
                "source_change_text": "持平",
                "system_change_type": "持平",
                "source_status": "updated",
                "note": "",
            }
        )
    if not holdings:
        return None
    return {
        "meta": {
            "etf_code": etf_code,
            "etf_name": etf_name,
            "data_date": snapshot_date,
            "run_date": date.today().isoformat(),
            "source_status": "updated",
            "source_url": source_url,
            "holdings_count": len(holdings),
        },
        "holdings": holdings,
    }


def discover_active_etfs() -> list[dict[str, Any]]:
    return discover_active_etfs_from_html(fetch_text(ACTIVE_URL))


def holdings_page_url(etf_code: str, page: int = 1) -> str:
    base = f"{BASE_URL}/etf/{etf_code}/holdings"
    if page <= 1:
        return base
    return f"{base}?page={page}"


def page_count(html_text: str) -> int:
    lines = html_to_lines(html_text)
    for line in lines:
        match = re.search(r"(\d+)\s*/\s*(\d+)", line)
        if match:
            return int(match.group(2))
    return 1


def fetch_holdings(etf_code: str, *, sleep_seconds: float = 0.25) -> dict[str, Any]:
    first_url = holdings_page_url(etf_code)
    first_html = fetch_text(first_url)
    payload_src_match = re.search(r'data-src="([^"]+_payload\.json[^"]*)"', first_html)
    if payload_src_match:
        payload_url = urllib.parse.urljoin(first_url, html.unescape(payload_src_match.group(1)))
        payload = parse_nuxt_payload(fetch_text(payload_url), etf_code=etf_code, source_url=first_url)
        if payload:
            snapshot_date = extract_snapshot_date(first_html)
            if snapshot_date:
                payload["meta"]["data_date"] = snapshot_date
            return payload

    first_payload = parse_holdings_page(first_html, etf_code=etf_code, source_url=first_url)
    holdings = first_payload["holdings"]
    if not holdings:
        return first_payload

    for page in range(2, page_count(first_html) + 1):
        time.sleep(sleep_seconds)
        url = holdings_page_url(etf_code, page)
        payload = parse_holdings_page(fetch_text(url), etf_code=etf_code, source_url=url)
        holdings.extend(payload["holdings"])

    seen = set()
    deduped = []
    for holding in holdings:
        if holding["stock_id"] in seen:
            continue
        seen.add(holding["stock_id"])
        deduped.append(holding)
    first_payload["holdings"] = deduped
    first_payload["meta"]["holdings_count"] = len(deduped)
    return first_payload


def main() -> None:
    parser = argparse.ArgumentParser(description="Discover active ETFs or fetch ETFInfo holdings.")
    parser.add_argument("--discover", action="store_true")
    parser.add_argument("--code")
    args = parser.parse_args()

    if args.discover:
        print(json.dumps(discover_active_etfs(), ensure_ascii=False, indent=2))
    elif args.code:
        print(json.dumps(fetch_holdings(args.code), ensure_ascii=False, indent=2))
    else:
        parser.error("Use --discover or --code ETF_CODE")


if __name__ == "__main__":
    main()
