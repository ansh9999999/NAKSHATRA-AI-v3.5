"""
NAKSHATRA AI v4.0
Delta Exchange India - Robust Market Data Helper

ROOT delta.py

Provides:
- Live ticker
- Current price
- Candle history
- Multi-timeframe history
- Safe timestamp handling
- Retry + timeout
- Compatible get_history()
- Compatible get_multi_timeframe_history()
"""

import os
import time
from datetime import datetime, timezone

import requests
import pandas as pd


# ==========================================================
# CONFIG
# ==========================================================

BASE_URL = os.getenv(
    "DELTA_BASE_URL",
    "https://api.india.delta.exchange/v2"
).rstrip("/")

if BASE_URL.endswith("/v2"):
    CANDLE_URL = f"{BASE_URL}/history/candles"
    TICKER_URL = f"{BASE_URL}/tickers"
else:
    CANDLE_URL = f"{BASE_URL}/v2/history/candles"
    TICKER_URL = f"{BASE_URL}/v2/tickers"

TIMEOUT = 15
RETRIES = 2


# ==========================================================
# SESSION
# ==========================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "NAKSHATRA-AI/4.0",
    "Accept": "application/json",
})


# ==========================================================
# SAFE FLOAT
# ==========================================================

def _float(value, default=0.0):
    try:
        if value is None:
            return default

        return float(value)

    except Exception:
        return default


# ==========================================================
# SAFE INT
# ==========================================================

def _int(value, default=None):
    try:
        return int(float(value))
    except Exception:
        return default


# ==========================================================
# SAFE TIMESTAMP
# ==========================================================

def _timestamp_seconds(value):
    """
    Convert Delta timestamp into Unix seconds.

    Supports:
    - Unix seconds
    - milliseconds
    - microseconds
    - datetime
    - pandas Timestamp
    - ISO datetime string
    """

    if value is None:
        return None

    # ------------------------------------------------------
    # datetime / pandas Timestamp
    # ------------------------------------------------------

    if isinstance(value, (datetime, pd.Timestamp)):
        try:
            ts = pd.Timestamp(value)

            if ts.tzinfo is None:
                ts = ts.tz_localize("UTC")
            else:
                ts = ts.tz_convert("UTC")

            return int(ts.timestamp())

        except Exception:
            return None

    # ------------------------------------------------------
    # Numeric timestamp
    # ------------------------------------------------------

    try:
        number = float(value)

        if number != number:
            return None

        ts = int(number)

        # microseconds
        if abs(ts) > 10_000_000_000_000:
            ts //= 1_000_000

        # milliseconds
        elif abs(ts) > 10_000_000_000:
            ts //= 1_000

        return ts

    except Exception:
        pass

    # ------------------------------------------------------
    # ISO / string datetime
    # ------------------------------------------------------

    try:
        text = str(value).strip()

        if not text:
            return None

        parsed = pd.to_datetime(
            text,
            utc=True,
            errors="coerce"
        )

        if pd.isna(parsed):
            return None

        return int(parsed.timestamp())

    except Exception:
        return None


# ==========================================================
# EMPTY DATAFRAME
# ==========================================================

def _empty_dataframe():
    df = pd.DataFrame(
        columns=[
            "timestamp",
            "open",
            "high",
            "low",
            "close",
            "volume",
        ]
    )

    df.index = pd.DatetimeIndex([], name="datetime")

    return df


# ==========================================================
# LIVE TICKER
# ==========================================================

def get_ticker(symbol="BTCUSD"):
    """
    Get live ticker from Delta Exchange India.
    """

    symbol = str(symbol).upper().strip()

    url = f"{TICKER_URL}/{symbol}"

    try:

        response = session.get(
            url,
            timeout=TIMEOUT
        )

        response.raise_for_status()

        payload = response.json()

        result = payload.get("result")

        if not result:
            return None

        price = (
            result.get("close")
            or result.get("mark_price")
            or result.get("spot_price")
        )

        return {
            "symbol": result.get(
                "symbol",
                symbol
            ),

            "price": _float(price),

            "mark_price": _float(
                result.get(
                    "mark_price",
                    price
                )
            ),

            "volume": _float(
                result.get(
                    "volume",
                    0
                )
            ),
        }

    except Exception as exc:

        print(
            f"Delta ticker error "
            f"[{symbol}]: {exc}"
        )

        return None


# ==========================================================
# CURRENT PRICE
# ==========================================================

def get_current_price(symbol="BTCUSD"):

    ticker = get_ticker(symbol)

    if not ticker:
        return None

    price = ticker.get("price")

    if price is None:
        return None

    return float(price)


# ==========================================================
# RESOLUTIONS
# ==========================================================

RESOLUTION_SECONDS = {

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

    # Approximate month window.
    # Used only for historical request.
    "1mo": 2592000,
}


# ==========================================================
# NORMALIZE RESULT
# ==========================================================

def _extract_rows(payload):

    if not isinstance(payload, dict):
        return []

    result = payload.get("result")

    if isinstance(result, list):
        return result

    if isinstance(result, dict):

        for key in (
            "candles",
            "data",
            "rows",
            "result",
        ):

            value = result.get(key)

            if isinstance(value, list):
                return value

    return []


# ==========================================================
# GET CANDLES
# ==========================================================

def get_candles(
    symbol="BTCUSD",
    resolution="5m",
    limit=200
):
    """
    Download historical candles.

    Returns DataFrame:

    timestamp
    open
    high
    low
    close
    volume

    Index:
    UTC datetime
    """

    symbol = str(
        symbol
    ).upper().strip()

    resolution = str(
        resolution
    ).lower().strip()

    # ------------------------------------------------------
    # Resolution validation
    # ------------------------------------------------------

    if resolution not in RESOLUTION_SECONDS:

        print(
            f"Delta: unsupported resolution "
            f"{resolution}; using 5m"
        )

        resolution = "5m"

    # ------------------------------------------------------
    # Limit
    # ------------------------------------------------------

    try:
        limit = int(limit)

    except Exception:
        limit = 200

    limit = max(
        10,
        min(limit, 1000)
    )

    candle_seconds = RESOLUTION_SECONDS[
        resolution
    ]

    # ------------------------------------------------------
    # Unix time
    #
    # IMPORTANT:
    # Keep API start/end as INTEGER Unix seconds.
    # Do not pass datetime objects to Delta.
    # ------------------------------------------------------

    now = int(time.time())

    end = now

    start = (
        end -
        (
            limit *
            candle_seconds
        )
    )

    params = {
        "symbol": symbol,
        "resolution": resolution,
        "start": int(start),
        "end": int(end),
    }

    # ------------------------------------------------------
    # Request with retry
    # ------------------------------------------------------

    last_error = None

    for attempt in range(RETRIES + 1):

        try:

            response = session.get(
                CANDLE_URL,
                params=params,
                timeout=TIMEOUT
            )

            response.raise_for_status()

            payload = response.json()

            rows = _extract_rows(payload)

            if not rows:

                print(
                    f"Delta: no candles "
                    f"{symbol} {resolution}"
                )

                return _empty_dataframe()

            df = pd.DataFrame(rows)

            if df.empty:
                return _empty_dataframe()

            # --------------------------------------------------
            # TIMESTAMP
            # --------------------------------------------------

            timestamp_column = None

            if "time" in df.columns:
                timestamp_column = "time"

            elif "timestamp" in df.columns:
                timestamp_column = "timestamp"

            elif "start" in df.columns:
                timestamp_column = "start"

            if timestamp_column is None:

                print(
                    f"Delta: timestamp missing "
                    f"{symbol} {resolution}"
                )

                return _empty_dataframe()

            df["timestamp"] = (
                df[timestamp_column]
                .apply(_timestamp_seconds)
            )

            # --------------------------------------------------
            # OHLCV
            # --------------------------------------------------

            required = [
                "open",
                "high",
                "low",
                "close",
            ]

            for column in required:

                if column not in df.columns:

                    print(
                        f"Delta: missing {column} "
                        f"{symbol} {resolution}"
                    )

                    return _empty_dataframe()

                df[column] = pd.to_numeric(
                    df[column],
                    errors="coerce"
                )

            if "volume" in df.columns:

                df["volume"] = pd.to_numeric(
                    df["volume"],
                    errors="coerce"
                )

            else:

                df["volume"] = 0.0

            # --------------------------------------------------
            # CLEAN
            # --------------------------------------------------

            df.dropna(
                subset=[
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                ],
                inplace=True
            )

            if df.empty:
                return _empty_dataframe()

            # --------------------------------------------------
            # Force timestamp to integer seconds
            # --------------------------------------------------

            df["timestamp"] = (
                df["timestamp"]
                .astype("int64")
            )

            # --------------------------------------------------
            # Remove duplicate candles
            # --------------------------------------------------

            df.drop_duplicates(
                subset=["timestamp"],
                keep="last",
                inplace=True
            )

            # --------------------------------------------------
            # Sort
            # --------------------------------------------------

            df.sort_values(
                "timestamp",
                inplace=True
            )

            df.reset_index(
                drop=True,
                inplace=True
            )

            # --------------------------------------------------
            # DATETIME INDEX
            #
            # IMPORTANT:
            # Keep timestamp column numeric.
            # Keep DataFrame index as datetime.
            # --------------------------------------------------

            df["datetime"] = pd.to_datetime(
                df["timestamp"],
                unit="s",
                utc=True,
                errors="coerce"
            )

            df.dropna(
                subset=["datetime"],
                inplace=True
            )

            if df.empty:
                return _empty_dataframe()

            df.set_index(
                "datetime",
                inplace=True
            )

            df.index.name = "datetime"

            df.sort_index(
                inplace=True
            )

            # --------------------------------------------------
            # FINAL COLUMN ORDER
            # --------------------------------------------------

            df = df[
                [
                    "timestamp",
                    "open",
                    "high",
                    "low",
                    "close",
                    "volume",
                ]
            ]

            print(
                f"Delta candles OK: "
                f"{symbol} {resolution} "
                f"rows={len(df)} "
                f"last={df.index[-1]}"
            )

            return df

        except requests.RequestException as exc:

            last_error = exc

            print(
                f"Delta request error "
                f"[{symbol} {resolution}] "
                f"attempt={attempt + 1}: "
                f"{exc}"
            )

            if attempt < RETRIES:
                time.sleep(0.5)

        except ValueError as exc:

            last_error = exc

            print(
                f"Delta JSON/data error "
                f"[{symbol} {resolution}]: "
                f"{exc}"
            )

            if attempt < RETRIES:
                time.sleep(0.5)

        except Exception as exc:

            last_error = exc

            print(
                f"Delta candle error "
                f"[{symbol} {resolution}]: "
                f"{exc}"
            )

            if attempt < RETRIES:
                time.sleep(0.5)

    print(
        f"Delta candle FAILED "
        f"[{symbol} {resolution}]: "
        f"{last_error}"
    )

    return _empty_dataframe()


# ==========================================================
# HISTORY ALIAS
# ==========================================================

def get_history(
    symbol="BTCUSD",
    resolution="5m",
    limit=200
):

    return get_candles(
        symbol=symbol,
        resolution=resolution,
        limit=limit
    )


# ==========================================================
# MULTI TIMEFRAME HISTORY
# ==========================================================

def get_multi_timeframe_history(
    symbol="BTCUSD",
    limit=200
):
    """
    Return:

    5m
    15m
    1h
    1d
    1w
    1mo

    Each timeframe is independent.
    One failed timeframe does not destroy
    the complete result.
    """

    timeframes = [
        "5m",
        "15m",
        "1h",
        "1d",
        "1w",
        "1mo",
    ]

    result = {}

    for timeframe in timeframes:

        try:

            result[timeframe] = get_candles(
                symbol=symbol,
                resolution=timeframe,
                limit=limit
            )

        except Exception as exc:

            print(
                f"MTF error "
                f"{symbol} {timeframe}: "
                f"{exc}"
            )

            result[timeframe] = (
                _empty_dataframe()
            )

    return result


# ==========================================================
# CONNECTION TEST
# ==========================================================

if __name__ == "__main__":

    print("=" * 60)
    print("NAKSHATRA AI - DELTA CONNECTION TEST")
    print("=" * 60)

    # ------------------------------------------------------
    # BTC ticker
    # ------------------------------------------------------

    btc = get_ticker("BTCUSD")

    print("\nBTC TICKER:")
    print(btc)

    # ------------------------------------------------------
    # ETH ticker
    # ------------------------------------------------------

    eth = get_ticker("ETHUSD")

    print("\nETH TICKER:")
    print(eth)

    # ------------------------------------------------------
    # BTC 5M
    # ------------------------------------------------------

    candles = get_candles(
        "BTCUSD",
        "5m",
        20
    )

    print("\nBTC 5M CANDLES:")

    if candles.empty:

        print("NO CANDLE DATA")

    else:

        print(
            candles.tail(5).to_string()
        )

        print(
            "\nLAST CANDLE INDEX:",
            candles.index[-1]
        )

    # ------------------------------------------------------
    # MTF TEST
    # ------------------------------------------------------

    print("\nMULTI TIMEFRAME TEST:")

    mtf = get_multi_timeframe_history(
        "BTCUSD",
        20
    )

    for tf, data in mtf.items():

        print(
            f"{tf}: "
            f"{len(data)} rows"
        )

    print("=" * 60)
