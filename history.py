"""
NAKSHATRA AI - Provider-aware history layer.

Delta is used ONLY for BTC/ETH.
Kotak Neo is used for Indian indices and MCX.

Public API kept compatible:
    get_history(symbol, resolution, limit)
    get_multi_timeframe_history(symbol, limit)
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import time

import pandas as pd
import requests

from config import DELTA_BASE_URL
from logger import logger
from market_registry import canonical_symbol, get_market
from kotak_neo import get_history as kotak_get_history

RESOLUTIONS = ("5m", "15m", "1h", "1d", "1w", "1mo")
DELTA_RESOLUTIONS = {
    "5m": 300,
    "15m": 900,
    "1h": 3600,
    "1d": 86400,
    "1w": 604800,
    "1mo": 2592000,
}
TIMEOUT_SECONDS = 8
RETRIES = 1
DEFAULT_LIMIT = 200

_CACHE = {}
_CACHE_TTL = 8


def _empty():
    return pd.DataFrame(
        columns=["open", "high", "low", "close", "volume"]
    )


def _delta_endpoint():
    base = str(DELTA_BASE_URL).rstrip("/")
    if base.endswith("/v2"):
        return f"{base}/history/candles"
    return f"{base}/v2/history/candles"


def _fetch_delta_history(symbol, resolution="5m", limit=200):
    key = ("delta", symbol.upper(), resolution, int(limit))
    now = time.time()

    cached = _CACHE.get(key)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1].copy()

    interval_seconds = DELTA_RESOLUTIONS.get(resolution)
    if interval_seconds is None:
        logger.warning("Unsupported Delta resolution: %s", resolution)
        return _empty()

    end = int(time.time())
    start = end - int(limit) * interval_seconds

    params = {
        "symbol": symbol.upper(),
        "resolution": resolution,
        "start": start,
        "end": end,
    }

    last_error = None

    for attempt in range(RETRIES + 1):
        try:
            response = requests.get(
                _delta_endpoint(),
                params=params,
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()

            payload = response.json()
            rows = payload.get("result") or []

            if not isinstance(rows, list) or not rows:
                raise ValueError(
                    f"Delta returned no candles for {symbol.upper()} {resolution}"
                )

            df = pd.DataFrame(rows)

            if "time" in df.columns and "timestamp" not in df.columns:
                df.rename(columns={"time": "timestamp"}, inplace=True)

            required = ["timestamp", "open", "high", "low", "close"]
            if any(col not in df.columns for col in required):
                raise ValueError(
                    f"Invalid Delta candle response for {symbol.upper()} {resolution}"
                )

            for col in ["open", "high", "low", "close", "volume"]:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            df["timestamp"] = pd.to_datetime(
                df["timestamp"],
                unit="s",
                utc=True,
                errors="coerce",
            )

            df.dropna(
                subset=["timestamp", "open", "high", "low", "close"],
                inplace=True,
            )
            df.sort_values("timestamp", inplace=True)
            df.drop_duplicates("timestamp", keep="last", inplace=True)
            df.set_index("timestamp", inplace=True)

            if "volume" not in df.columns:
                df["volume"] = 0.0

            df = df[["open", "high", "low", "close", "volume"]]

            _CACHE[key] = (time.time(), df.copy())

            logger.info(
                "HISTORY OK provider=delta symbol=%s tf=%s rows=%s",
                symbol.upper(),
                resolution,
                len(df),
            )
            return df

        except Exception as exc:
            last_error = exc
            if attempt < RETRIES:
                time.sleep(0.25)

    logger.warning(
        "HISTORY FAILED provider=delta symbol=%s tf=%s error=%s",
        symbol.upper(),
        resolution,
        last_error,
    )
    return _empty()


def get_history(symbol="BTCUSD", resolution="5m", limit=200):
    canonical = canonical_symbol(symbol)
    market = get_market(canonical)

    if not market:
        logger.warning("Unsupported market: %s", symbol)
        return _empty()

    provider = market.get("provider")

    if provider == "delta":
        return _fetch_delta_history(canonical, resolution, limit)

    if provider == "kotak_neo":
        key = ("kotak", canonical, resolution, int(limit))
        now = time.time()
        cached = _CACHE.get(key)
        if cached and now - cached[0] < _CACHE_TTL:
            return cached[1].copy()

        df = kotak_get_history(canonical, resolution, limit)

        if df is not None and not df.empty:
            _CACHE[key] = (time.time(), df.copy())
            logger.info(
                "HISTORY OK provider=kotak_neo symbol=%s tf=%s rows=%s",
                canonical,
                resolution,
                len(df),
            )
            return df

        logger.warning(
            "HISTORY FAILED provider=kotak_neo symbol=%s tf=%s",
            canonical,
            resolution,
        )
        return _empty()

    logger.warning(
        "No history provider configured for %s (provider=%s)",
        canonical,
        provider,
    )
    return _empty()


def get_multi_timeframe_history(symbol, limit=DEFAULT_LIMIT):
    canonical = canonical_symbol(symbol)
    result = {tf: _empty() for tf in RESOLUTIONS}

    # For Indian markets only the four timeframes used by the signal engine
    # are requested. Crypto keeps the original extended set.
    market = get_market(canonical)
    if market and market.get("provider") == "kotak_neo":
        resolutions = ("5m", "15m", "1h", "1d")
    else:
        resolutions = RESOLUTIONS

    with ThreadPoolExecutor(max_workers=len(resolutions)) as pool:
        jobs = {
            pool.submit(
                get_history,
                canonical,
                tf,
                limit,
            ): tf
            for tf in resolutions
        }

        for job in as_completed(jobs):
            tf = jobs[job]
            try:
                result[tf] = job.result()
            except Exception:
                logger.exception(
                    "TIMEFRAME ERROR symbol=%s tf=%s",
                    canonical,
                    tf,
                )
                result[tf] = _empty()

    return result
