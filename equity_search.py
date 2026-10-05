"""NAKSHATRA AI - Kotak Neo equity search.

Read-only discovery layer for NSE/BSE cash equities.  It uses Kotak Neo's
ScripMaster files, caches the parsed universe in memory, and dynamically
registers a selected equity with NAKSHATRA's existing market/history layers.
No order placement is performed.
"""
from __future__ import annotations

import re
import threading
import io
import time
from typing import Any

import pandas as pd
import requests

from logger import logger
from market_registry import MARKETS
from kotak_neo import _client, _normalise_record, _walk_objects, _first, _text, _TOKEN_CACHE, _kotak_throttle

_LOCK = threading.Lock()
_UNIVERSE: list[dict[str, Any]] = []
_UNIVERSE_TIME = 0.0
_UNIVERSE_TTL = 6 * 60 * 60
_SEARCH_CACHE: dict[tuple[str, int], tuple[float, dict[str, Any]]] = {}
_SEARCH_CACHE_TTL = 30.0


def _urls_from_response(response: Any) -> list[str]:
    urls: list[str] = []
    if isinstance(response, str):
        urls.append(response)
    else:
        for obj in _walk_objects(response):
            for key in ("filePath", "file_path", "url", "path"):
                value = obj.get(key)
                if isinstance(value, str) and value.startswith("http"):
                    urls.append(value)
            for key in ("filesPaths", "filePaths"):
                value = obj.get(key)
                if isinstance(value, list):
                    urls.extend(str(x) for x in value if str(x).startswith("http"))
    return list(dict.fromkeys(urls))


def _norm_text(v: Any) -> str:
    return re.sub(r"[^A-Z0-9]", "", str(v or "").upper())


def _is_cash_equity(raw: dict[str, Any], normal: dict[str, Any]) -> bool:
    seg = str(normal.get("exchange_segment") or _first(raw, "pExchSeg", "exchangeSegment", "exchange") or "").lower()
    if seg not in {"nse_cm", "bse_cm", "nse_cm"}:
        return False

    inst = str(normal.get("instrument_type") or _first(raw, "pInstType", "instrumentType", "instrument_type") or "").upper()
    symbol = str(normal.get("trading_symbol") or "").upper()

    # ScripMaster schemas vary.  Accept explicit equity/cash types, and for
    # older files accept records that look like normal cash-market symbols.
    if any(x in inst for x in ("EQ", "EQUITY", "CASH")):
        return True
    if any(x in symbol for x in ("-EQ", "-BE", "-BL")):
        return True
    return bool(symbol) and not any(x in symbol for x in ("FUT", "CE", "PE"))


def _display_name(raw: dict[str, Any], normal: dict[str, Any]) -> str:
    return str(
        _first(
            raw,
            "company_name", "companyName", "company", "description", "Description",
            "pDesc", "pDescription", "name", "symbol", "trading_symbol", "pTrdSymbol",
        )
        or normal.get("trading_symbol")
        or ""
    ).strip()


def _parse_url(url: str) -> list[dict[str, Any]]:
    try:
        r = requests.get(url, timeout=20)
        r.raise_for_status()
        content = r.content
        # Kotak's scrip files are CSV/TSV depending on generation.
        try:
            df = pd.read_csv(io.BytesIO(content), low_memory=False)
        except Exception:
            df = pd.read_csv(io.BytesIO(content), sep="|", low_memory=False)
        if df.empty:
            return []
    except Exception as exc:
        logger.warning("EQUITY SEARCH scrip-master download failed: %s", exc)
        return []

    rows: list[dict[str, Any]] = []
    for _, row in df.iterrows():
        raw = {str(k): row[k] for k in df.columns}
        normal = _normalise_record(raw)
        token = normal.get("instrument_token")
        trading = str(normal.get("trading_symbol") or "").strip()
        if token in (None, "", "nan") or not trading:
            continue
        if not _is_cash_equity(raw, normal):
            continue
        rows.append({
            "token": str(token),
            "exchange_segment": str(normal.get("exchange_segment") or "nse_cm").lower(),
            "trading_symbol": trading,
            "name": _display_name(raw, normal),
            "instrument_type": str(normal.get("instrument_type") or "EQ"),
        })
    return rows



def _search_scrip_direct(query: str, limit: int) -> list[dict[str, Any]]:
    """Fast path: use Kotak Neo's search_scrip API before downloading masters.

    Kotak's current SDK exposes search_scrip(exchange_segment, symbol, ...),
    which searches the ScripMaster internally. This avoids downloading and
    parsing the full NSE/BSE universe for every dashboard search.
    """
    try:
        client = _client()
        search_fn = getattr(client, "search_scrip", None)
        if not callable(search_fn):
            return []
    except Exception as exc:
        logger.warning("EQUITY SEARCH client unavailable: %s", exc)
        return []

    out: list[dict[str, Any]] = []
    seen: set[tuple[str, str]] = set()
    # Search both cash segments. Search results are already instrument records.
    for segment in ("nse_cm", "bse_cm"):
        try:
            _kotak_throttle()
            response = search_fn(
                exchange_segment=segment,
                symbol=query.strip().upper(),
                expiry="",
                option_type="",
                strike_price="",
            )
        except TypeError:
            try:
                response = search_fn(
                    exchange_segment=segment,
                    symbol=query.strip().upper(),
                )
            except Exception as exc:
                logger.warning("EQUITY SEARCH %s search_scrip failed: %s", segment, exc)
                continue
        except Exception as exc:
            logger.warning("EQUITY SEARCH %s search_scrip failed: %s", segment, exc)
            continue

        for raw in _walk_objects(response):
            normal = _normalise_record(raw)
            # Kotak sample equity records use pGroup=EQ and pTrdSymbol=YESBANK-EQ.
            group = str(_first(raw, "pGroup", "group", "instrument_group") or "").upper()
            inst = str(normal.get("instrument_type") or "").upper()
            symbol = str(normal.get("trading_symbol") or "").strip()
            token = normal.get("instrument_token")
            exch = str(normal.get("exchange_segment") or segment).lower()
            if not symbol or token in (None, "", "nan") or exch not in {"nse_cm", "bse_cm"}:
                continue
            if group not in {"", "EQ", "EQUITY", "CASH"} and not any(x in inst for x in ("EQ", "EQUITY", "CASH")):
                continue
            # Exclude derivatives and non-cash variants.
            us = symbol.upper()
            if any(x in us for x in ("-FUT", "-CE", "-PE")):
                continue
            key = (exch, us)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "token": str(token),
                "exchange_segment": exch,
                "trading_symbol": symbol,
                "name": str(_first(raw, "pDesc", "pSymbolName", "description", "company_name", "companyName", "name") or symbol).strip(),
                "instrument_type": inst or group or "EQ",
            })
            if len(out) >= max(1, min(int(limit) * 3, 60)):
                return out
    return out

def _load_universe(force: bool = False) -> list[dict[str, Any]]:
    global _UNIVERSE, _UNIVERSE_TIME
    now = time.time()
    with _LOCK:
        if _UNIVERSE and not force and now - _UNIVERSE_TIME < _UNIVERSE_TTL:
            return _UNIVERSE

        try:
            client = _client()
            urls: list[str] = []
            for segment in ("nse_cm", "bse_cm"):
                try:
                    urls.extend(_urls_from_response(client.scrip_master(exchange_segment=segment)))
                except TypeError:
                    urls.extend(_urls_from_response(client.scrip_master()))
                except Exception as exc:
                    logger.warning("EQUITY SEARCH scrip-master %s failed: %s", segment, exc)
            urls = list(dict.fromkeys(urls))
        except Exception as exc:
            logger.warning("EQUITY SEARCH client unavailable: %s", exc)
            return _UNIVERSE

        combined: list[dict[str, Any]] = []
        for url in urls:
            combined.extend(_parse_url(url))

        # Deduplicate by exchange + trading symbol.
        seen = set()
        clean = []
        for row in combined:
            key = (row["exchange_segment"], _norm_text(row["trading_symbol"]))
            if key in seen:
                continue
            seen.add(key)
            clean.append(row)

        clean.sort(key=lambda x: (x["exchange_segment"], x["trading_symbol"]))
        _UNIVERSE = clean
        _UNIVERSE_TIME = now
        logger.info("EQUITY SEARCH universe loaded rows=%s urls=%s", len(clean), len(urls))
        return _UNIVERSE


def _register(row: dict[str, Any]) -> str:
    token = row["token"]
    seg = row["exchange_segment"]
    trading = row["trading_symbol"]
    # Stable internal symbol. It is deliberately not the broker trading symbol
    # so aliases/canonicalization cannot collide with existing index symbols.
    safe_token = re.sub(r"[^A-Za-z0-9]", "_", token)
    safe_trading = re.sub(r"[^A-Z0-9]", "", trading.upper())[:18]
    internal = f"EQ_{seg}_{safe_trading}_{safe_token}"[:60]

    market = {
        "name": row.get("name") or trading,
        "display": trading,
        "asset_class": "EQUITY",
        "exchange": "NSE" if seg == "nse_cm" else "BSE",
        "provider": "kotak_neo",
        "data_symbol": trading,
        "neo_exchange_segment": seg,
        "neo_symbol_candidates": [trading],
        "option_chain": False,
        "dynamic_equity": True,
        "instrument_token": token,
        "instrument_record": {
            "instrument_token": token,
            "exchange_segment": seg,
            "trading_symbol": trading,
            "instrument_type": row.get("instrument_type") or "EQ",
        },
    }
    MARKETS[internal] = market
    _TOKEN_CACHE[internal] = {"time": time.time(), "record": market["instrument_record"]}
    return internal


def search(query: str, limit: int = 12) -> dict[str, Any]:
    q = str(query or "").strip()
    safe_limit = max(1, min(int(limit), 30))
    cache_key = (q.upper(), safe_limit)
    cached = _SEARCH_CACHE.get(cache_key)
    if cached and time.time() - cached[0] < _SEARCH_CACHE_TTL:
        return cached[1]
    if len(q) < 2:
        return {"status": "OK", "query": q, "count": 0, "results": [], "note": "Type at least 2 characters."}

    # V2.21 fast path: Kotak search_scrip is the authoritative current lookup.
    direct = _search_scrip_direct(q, safe_limit)
    rows = direct if direct else _load_universe()

    nq = _norm_text(q)
    q_upper = q.upper()
    exact, prefix, contains = [], [], []
    for row in rows:
        sym = str(row.get("trading_symbol") or "").upper()
        name = str(row.get("name") or "").upper()
        ns = _norm_text(sym)
        nn = _norm_text(name)
        item = row
        if ns == nq or nn == nq:
            exact.append(item)
        elif ns.startswith(nq) or nn.startswith(nq) or sym.startswith(q_upper):
            prefix.append(item)
        elif nq in ns or nq in nn or q_upper in name:
            contains.append(item)

    ordered = exact + prefix + contains
    seen = set()
    results = []
    for row in ordered:
        key = (row["exchange_segment"], row["trading_symbol"])
        if key in seen:
            continue
        seen.add(key)
        internal = _register(row)
        results.append({
            "symbol": internal,
            "trading_symbol": row["trading_symbol"],
            "name": row["name"],
            "exchange": "NSE" if row["exchange_segment"] == "nse_cm" else "BSE",
            "segment": row["exchange_segment"],
        })
        if len(results) >= safe_limit:
            break

    source = "Kotak Neo search_scrip" if direct else "Kotak Neo ScripMaster"
    note = None if results else "No equity match or Kotak search_scrip returned no cash-equity result."
    payload = {"status": "OK", "query": q, "count": len(results), "results": results, "source": source}
    if note:
        payload["note"] = note
    _SEARCH_CACHE[cache_key] = (time.time(), payload)
    return payload

def register(symbol: str) -> dict[str, Any] | None:
    for row in _load_universe():
        if row["trading_symbol"].upper() == str(symbol or "").upper():
            internal = _register(row)
            return {"symbol": internal, **row}
    return None
        
