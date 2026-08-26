"""
NAKSHATRA AI v4.0 - Fast/Resilient historical data layer

Fixes:
- Fetches multiple timeframes concurrently.
- Uses the configured Delta base URL consistently.
- Each timeframe has its own timeout and failure isolation.
- A failed optional timeframe no longer blocks the whole analysis.
- Keeps the existing get_history() and get_multi_timeframe_history() API.
"""

from concurrent.futures import ThreadPoolExecutor, as_completed
import time

import pandas as pd
import requests

from config import DELTA_BASE_URL
from logger import logger

RESOLUTIONS = ("5m", "15m", "1h", "1d", "1w", "1mo")
TIMEOUT_SECONDS = 12
RETRIES = 3

_HTTP_HEADERS = {
    "User-Agent": "NAKSHATRA-AI/4.0",
    "Accept": "application/json",
}
DEFAULT_LIMIT = 200

# Small in-process cache prevents dashboard + scanner from hammering Delta.
_CACHE = {}
_CACHE_TTL = 8


def _endpoint():
    base = str(DELTA_BASE_URL).rstrip("/")
    if base.endswith("/v2"):
        return f"{base}/history/candles"
    return f"{base}/v2/history/candles"


def _empty():
    return pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume"])


def _fetch_history(symbol, resolution="5m", limit=200):
    key = (symbol.upper(), resolution, int(limit))
    now = time.time()

    cached = _CACHE.get(key)
    if cached and now - cached[0] < _CACHE_TTL:
        return cached[1].copy()

    # Delta candles API expects a time window in Unix seconds.
    interval_seconds = {
        "1m": 60,
        "3m": 180,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "2h": 7200,
        "4h": 14400,
        "6h": 21600,
        "12h": 43200,
        "1d": 86400,
        "1w": 604800,
        "1mo": 2592000,
    }.get(resolution)

    if interval_seconds is None:
        raise ValueError(f"Unsupported Delta resolution: {resolution}")

    end = int(time.time())
    start = end - (int(limit) * interval_seconds)

    params = {
        "symbol": symbol.upper(),
        "resolution": resolution,
        "start": start,
        "end": end,
    }
    url = _endpoint()

    last_error = None

    for attempt in range(RETRIES + 1):
        try:
            response = requests.get(
                url,
                params=params,
                headers=_HTTP_HEADERS,
                timeout=TIMEOUT_SECONDS,
            )
            response.raise_for_status()

            payload = response.json()
            rows = payload.get("result") or []
            if isinstance(rows, dict):
                for key in ("candles", "data", "rows", "result"):
                    if isinstance(rows.get(key), list):
                        rows = rows[key]
                        break
            if not isinstance(rows, list):
                raise ValueError(
                    f"Unexpected Delta candle response for {symbol.upper()} {resolution}"
                )

            if not rows:
                raise ValueError(
                    f"Delta returned no candles for {symbol.upper()} {resolution}"
                )

            df = pd.DataFrame(rows)

            if "time" in df.columns and "timestamp" not in df.columns:
                df.rename(columns={"time": "timestamp"}, inplace=True)

            numeric = ["open", "high", "low", "close", "volume"]
            for col in numeric:
                if col in df.columns:
                    df[col] = pd.to_numeric(df[col], errors="coerce")

            required = ["timestamp", "open", "high", "low", "close"]
            missing = [c for c in required if c not in df.columns]
            if missing:
                raise ValueError(
                    f"Missing candle columns for {symbol.upper()} {resolution}: {missing}"
                )

            df.dropna(subset=required, inplace=True)
            df.sort_values("timestamp", inplace=True)
            df.reset_index(drop=True, inplace=True)

            _CACHE[key] = (time.time(), df.copy())
            logger.info(
                "HISTORY OK %s %s rows=%s",
                symbol.upper(),
                resolution,
                len(df),
            )
            return df

        except Exception as exc:
            last_error = exc
            if attempt < RETRIES:
                time.sleep(0.5 * (attempt + 1))

    logger.warning(
        "HISTORY FAILED %s %s: %s",
        symbol.upper(),
        resolution,
        last_error,
    )
    return _empty()


def get_history(symbol="BTCUSD", resolution="5m", limit=200):
    return _fetch_history(symbol, resolution, limit)


def get_multi_timeframe_history(symbol, limit=200):
    """
    Fetch all six timeframes concurrently.

    A failed optional timeframe returns an empty DataFrame; the caller can
    still use the available frames. The entry timeframe (5m) remains the
    primary requirement of the signal engine.
    """
    result = {tf: _empty() for tf in RESOLUTIONS}

    with ThreadPoolExecutor(max_workers=len(RESOLUTIONS)) as pool:
        jobs = {
            pool.submit(_fetch_history, symbol, tf, limit): tf
            for tf in RESOLUTIONS
        }

        for job in as_completed(jobs):
            tf = jobs[job]
            try:
                result[tf] = job.result()
            except Exception as exc:
                logger.exception("TIMEFRAME ERROR %s %s", symbol, tf)
                result[tf] = _empty()

    return result
