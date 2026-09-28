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
import threading

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
_CACHE_TTL = 45

# V2.14: Kotak history is expensive/rate-limited. Cache by symbol+timeframe
# (NOT by requested limit), so dashboard limit=200 and analysis limit=220
# share the same fetch instead of making duplicate API calls.
_TIMEFRAME_TTL = {
    "5m": 60,
    "15m": 180,
    "1h": 600,
    "1d": 3600,
}
_KOTAK_FETCH_LIMIT = 240
_STALE_FALLBACK_SECONDS = 1800

# One in-flight request per symbol/timeframe. Concurrent dashboard/scanner
# requests wait for the first request and then reuse its cache.
_LOCKS = {}
_LOCKS_GUARD = threading.Lock()

# Reject clearly old intraday history. This still tolerates weekends/holidays.
_MAX_LAST_CANDLE_AGE = {
    "5m": 5 * 86400,
    "15m": 5 * 86400,
    "1h": 7 * 86400,
    "1d": 14 * 86400,
}

# Kotak historical-data endpoint does not support MCX in this integration.
# MCX instruments still have live quotes/options, but history must not be
# requested repeatedly because Kotak returns HTTP 400 for that exchange.
MCX_SYMBOLS = {"GOLD", "SILVER", "CRUDEOIL"}


def _kotak_lock(symbol, resolution):
    key = (symbol, resolution)
    with _LOCKS_GUARD:
        if key not in _LOCKS:
            _LOCKS[key] = threading.Lock()
        return _LOCKS[key]


def _last_candle_age_seconds(df):
    try:
        if df is None or df.empty:
            return None
        idx = df.index[-1]
        ts = pd.Timestamp(idx)
        if ts.tzinfo is None:
            ts = ts.tz_localize("UTC")
        else:
            ts = ts.tz_convert("UTC")
        return max(0.0, time.time() - ts.timestamp())
    except Exception:
        return None


def _is_reasonably_fresh(df, resolution):
    age = _last_candle_age_seconds(df)
    if age is None:
        return False
    return age <= _MAX_LAST_CANDLE_AGE.get(resolution, 14 * 86400)


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
        if canonical in MCX_SYMBOLS:
            logger.info(
                "HISTORY SKIP provider=kotak_neo symbol=%s tf=%s reason=MCX_HISTORY_UNSUPPORTED",
                canonical, resolution,
            )
            return _empty()

        tf = str(resolution).lower()
        # IMPORTANT: no limit in cache key. A 200-row and 220-row caller now
        # share the same 240-row upstream fetch.
        key = ("kotak", canonical, tf)
        now = time.time()
        ttl = _TIMEFRAME_TTL.get(tf, _CACHE_TTL)

        cached = _CACHE.get(key)
        if cached and now - cached[0] < ttl:
            df = cached[1]
            if _is_reasonably_fresh(df, tf):
                logger.info(
                    "HISTORY CACHE HIT provider=kotak_neo symbol=%s tf=%s age=%.1fs rows=%s",
                    canonical, tf, now - cached[0], min(len(df), int(limit)),
                )
                return df.tail(int(limit)).copy()

        lock = _kotak_lock(canonical, tf)
        with lock:
            # Another request may have populated the cache while we waited.
            now = time.time()
            cached = _CACHE.get(key)
            if cached and now - cached[0] < ttl and _is_reasonably_fresh(cached[1], tf):
                logger.info(
                    "HISTORY CACHE HIT AFTER WAIT provider=kotak_neo symbol=%s tf=%s rows=%s",
                    canonical, tf, min(len(cached[1]), int(limit)),
                )
                return cached[1].tail(int(limit)).copy()

            # Fetch one common superset so all consumers reuse it.
            fetch_limit = max(_KOTAK_FETCH_LIMIT, int(limit))
            df = kotak_get_history(canonical, tf, fetch_limit)

            if df is not None and not df.empty and _is_reasonably_fresh(df, tf):
                _CACHE[key] = (time.time(), df.copy())
                logger.info(
                    "HISTORY OK provider=kotak_neo symbol=%s tf=%s rows=%s cached_rows=%s",
                    canonical, tf, min(len(df), int(limit)), len(df),
                )
                return df.tail(int(limit)).copy()

            if df is not None and not df.empty:
                logger.warning(
                    "HISTORY STALE REJECTED provider=kotak_neo symbol=%s tf=%s last_age=%s",
                    canonical, tf, _last_candle_age_seconds(df),
                )

            # If Kotak is temporarily rate-limited, use the last GOOD cache for
            # a bounded period rather than falling back to arbitrary old chunks.
            cached = _CACHE.get(key)
            if cached and now - cached[0] <= _STALE_FALLBACK_SECONDS and _is_reasonably_fresh(cached[1], tf):
                logger.warning(
                    "HISTORY STALE-CACHE FALLBACK provider=kotak_neo symbol=%s tf=%s cache_age=%.1fs",
                    canonical, tf, now - cached[0],
                )
                return cached[1].tail(int(limit)).copy()

            logger.warning(
                "HISTORY FAILED provider=kotak_neo symbol=%s tf=%s no_safe_cache=1",
                canonical, tf,
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

    # Kotak rate-limits historical requests. Parallel requests for 5m/15m/1h/1d
    # can trigger HTTP 429, especially on Render cold starts. Fetch sequentially
    # and rely on the per-timeframe cache above.
    if market and market.get("provider") == "kotak_neo":
        for tf in resolutions:
            try:
                result[tf] = get_history(canonical, tf, limit)
                time.sleep(0.35)
            except Exception:
                logger.exception(
                    "TIMEFRAME ERROR symbol=%s tf=%s",
                    canonical,
                    tf,
                )
                result[tf] = _empty()
        return result

    with ThreadPoolExecutor(max_workers=len(resolutions)) as pool:
        jobs = {pool.submit(get_history, canonical, tf, limit): tf for tf in resolutions}
        for job in as_completed(jobs):
            tf = jobs[job]
            try:
                result[tf] = job.result()
            except Exception:
                logger.exception("TIMEFRAME ERROR symbol=%s tf=%s", canonical, tf)
                result[tf] = _empty()

    return result
