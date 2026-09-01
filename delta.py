"""
NAKSHATRA AI v4.0
ROOT delta.py

Delta Exchange India market-data helper.

FIXES:
- BTCUSD / ETHUSD symbol-price cross mapping protection
- Exact symbol validation
- Bulk ticker fallback
- Robust ticker extraction
- Candle history
- Multi-timeframe history
- Safe timestamps
- Retry / timeout
- Compatible get_history()
- Compatible get_multi_timeframe_history()
"""

import os
import time
from datetime import datetime

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
    TICKER_URL = f"{BASE_URL}/tickers"
    CANDLE_URL = f"{BASE_URL}/history/candles"
else:
    TICKER_URL = f"{BASE_URL}/v2/tickers"
    CANDLE_URL = f"{BASE_URL}/v2/history/candles"

TIMEOUT = 15
RETRIES = 3


# ==========================================================
# SESSION
# ==========================================================

session = requests.Session()

session.headers.update({
    "User-Agent": "NAKSHATRA-AI/4.0",
    "Accept": "application/json",
})


# ==========================================================
# SUPPORTED SYMBOLS
# ==========================================================

SUPPORTED_SYMBOLS = {
    "BTCUSD",
    "ETHUSD",
}


# ==========================================================
# SAFE FLOAT
# ==========================================================

def _float(value, default=0.0):
    try:
        if value is None:
            return default

        if isinstance(value, str):
            value = value.strip()

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
# SYMBOL NORMALIZER
# ==========================================================

def _normalize_symbol(symbol):
    symbol = str(symbol or "").upper().strip()

    # Browser/API clients can leak a JavaScript undefined token.
    # Treat it as the dashboard default rather than sending an invalid
    # symbol to Delta. Explicit supported symbols remain unchanged.
    if symbol in ("", "UNDEFINED", "NULL", "NONE", "NAN"):
        return "BTCUSD"

    aliases = {
        "BTC": "BTCUSD",
        "BTC/USDT": "BTCUSD",
        "BTC-USDT": "BTCUSD",
        "BTCUSD": "BTCUSD",

        "ETH": "ETHUSD",
        "ETH/USDT": "ETHUSD",
        "ETH-USDT": "ETHUSD",
        "ETHUSD": "ETHUSD",
    }

    return aliases.get(symbol, symbol)


# ==========================================================
# SYMBOL VALIDATION
# ==========================================================

def _validate_symbol(symbol):
    symbol = _normalize_symbol(symbol)

    if symbol not in SUPPORTED_SYMBOLS:
        raise ValueError(
            f"Unsupported Delta symbol: {symbol}. "
            f"Allowed: BTCUSD, ETHUSD"
        )

    return symbol


# ==========================================================
# SAFE TIMESTAMP
# ==========================================================

def _timestamp_seconds(value):
    """
    Convert timestamp to Unix seconds.

    Supports:
    - Unix seconds
    - milliseconds
    - microseconds
    - datetime
    - pandas Timestamp
    - ISO strings
    """

    if value is None:
        return None

    # datetime / pandas Timestamp
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

    # Numeric timestamp
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

    # String / ISO timestamp
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

    df.index = pd.DatetimeIndex(
        [],
        name="datetime"
    )

    return df


# ==========================================================
# HTTP GET WITH RETRY
# ==========================================================

def _get_json(url, params=None):

    last_error = None

    for attempt in range(RETRIES):

        try:

            response = session.get(
                url,
                params=params,
                timeout=TIMEOUT
            )

            response.raise_for_status()

            payload = response.json()

            if not isinstance(payload, dict):
                raise ValueError(
                    "Delta returned non-dict JSON"
                )

            return payload

        except Exception as exc:

            last_error = exc

            print(
                f"Delta HTTP error "
                f"attempt={attempt + 1}/{RETRIES}: "
                f"{exc}"
            )

            if attempt < RETRIES - 1:
                time.sleep(0.5)

    raise last_error


# ==========================================================
# EXTRACT TICKER RESULT
# ==========================================================

def _extract_ticker_result(payload, requested_symbol):

    if not isinstance(payload, dict):
        return None

    result = payload.get("result")

    if isinstance(result, dict):

        # Normal /tickers/{symbol} response
        result_symbol = _normalize_symbol(
            result.get("symbol")
        )

        if result_symbol == requested_symbol:
            return result

        # Some API responses can return nested data
        for key in (
            "data",
            "ticker",
            "result",
        ):

            nested = result.get(key)

            if isinstance(nested, dict):

                nested_symbol = _normalize_symbol(
                    nested.get("symbol")
                )

                if nested_symbol == requested_symbol:
                    return nested

    elif isinstance(result, list):

        for item in result:

            if not isinstance(item, dict):
                continue

            item_symbol = _normalize_symbol(
                item.get("symbol")
            )

            if item_symbol == requested_symbol:
                return item

    return None


# ==========================================================
# GET ALL TICKERS
# ==========================================================

def _get_all_tickers():

    payload = _get_json(
        TICKER_URL
    )

    result = payload.get("result")

    if isinstance(result, list):
        return result

    if isinstance(result, dict):

        for key in (
            "data",
            "tickers",
            "rows",
            "result",
        ):

            value = result.get(key)

            if isinstance(value, list):
                return value

    return []


# ==========================================================
# OPTION CHAIN TICKERS
# ==========================================================

def get_option_tickers(underlying_asset="BTC", expiry_date=None):
    """Get public Delta option-chain tickers for an underlying asset.

    Delta documents /v2/tickers with contract_types=call_options,put_options
    and an underlying asset symbol. An optional expiry_date is DD-MM-YYYY.
    """
    underlying_asset = str(underlying_asset or "").upper().strip()
    if underlying_asset not in ("BTC", "ETH"):
        raise ValueError("Unsupported option underlying")

    params = {
        "contract_types": "call_options,put_options",
        "underlying_asset_symbols": underlying_asset,
    }
    if expiry_date:
        params["expiry_date"] = str(expiry_date)

    payload = _get_json(TICKER_URL, params=params)
    result = payload.get("result") if isinstance(payload, dict) else None
    if isinstance(result, list):
        return result
    if isinstance(result, dict):
        for key in ("data", "tickers", "rows", "result"):
            value = result.get(key)
            if isinstance(value, list):
                return value
    return []


# ==========================================================
# LIVE TICKER
# ==========================================================

def get_ticker(symbol="BTCUSD"):
    """
    Get exact live ticker from Delta Exchange India.

    IMPORTANT:
    The requested symbol MUST match the symbol returned
    by Delta. This prevents BTCUSD / ETHUSD cross-mapping.
    """

    requested_symbol = _validate_symbol(symbol)

    # ------------------------------------------------------
    # METHOD 1
    # Exact /tickers/{symbol}
    # ------------------------------------------------------

    try:

        url = f"{TICKER_URL}/{requested_symbol}"

        payload = _get_json(url)

        result = _extract_ticker_result(
            payload,
            requested_symbol
        )

        if result:

            returned_symbol = _normalize_symbol(
                result.get("symbol")
            )

            # HARD SAFETY CHECK
            if returned_symbol != requested_symbol:

                print(
                    "Delta ticker symbol mismatch: "
                    f"requested={requested_symbol}, "
                    f"returned={returned_symbol}"
                )

            else:

                price = (
                    result.get("close")
                    if result.get("close") is not None
                    else result.get("mark_price")
                )

                if price is None:
                    price = result.get("spot_price")

                price = _float(price, None)

                if price is not None and price > 0:

                    return {
                        "symbol": returned_symbol,

                        "price": price,

                        "close": price,

                        "mark_price": _float(
                            result.get(
                                "mark_price"
                            ),
                            price
                        ),

                        "spot_price": _float(
                            result.get(
                                "spot_price"
                            ),
                            0.0
                        ),

                        "volume": _float(
                            result.get(
                                "volume"
                            ),
                            0.0
                        ),

                        "open": _float(
                            result.get(
                                "open"
                            ),
                            0.0
                        ),

                        "high": _float(
                            result.get(
                                "high"
                            ),
                            0.0
                        ),

                        "low": _float(
                            result.get(
                                "low"
                            ),
                            0.0
                        ),

                        "source": "delta_exact",
                    }

    except Exception as exc:

        print(
            f"Delta exact ticker failed "
            f"[{requested_symbol}]: {exc}"
        )


    # ------------------------------------------------------
    # METHOD 2
    # Bulk /tickers fallback
    #
    # This is the important protection against a wrong
    # symbol response.
    # ------------------------------------------------------

    try:

        tickers = _get_all_tickers()

        exact = None

        for item in tickers:

            if not isinstance(item, dict):
                continue

            item_symbol = _normalize_symbol(
                item.get("symbol")
            )

            if item_symbol == requested_symbol:

                exact = item
                break

        if exact is None:

            print(
                f"Delta bulk ticker: "
                f"{requested_symbol} not found"
            )

            return None

        returned_symbol = _normalize_symbol(
            exact.get("symbol")
        )

        # HARD SAFETY CHECK
        if returned_symbol != requested_symbol:

            print(
                "Delta bulk ticker mismatch: "
                f"requested={requested_symbol}, "
                f"returned={returned_symbol}"
            )

            return None

        price = exact.get("close")

        if price is None:
            price = exact.get("mark_price")

        if price is None:
            price = exact.get("spot_price")

        price = _float(price, None)

        if price is None or price <= 0:
            return None

        return {
            "symbol": returned_symbol,

            "price": price,

            "close": price,

            "mark_price": _float(
                exact.get(
                    "mark_price"
                ),
                price
            ),

            "spot_price": _float(
                exact.get(
                    "spot_price"
                ),
                0.0
            ),

            "volume": _float(
                exact.get(
                    "volume"
                ),
                0.0
            ),

            "open": _float(
                exact.get(
                    "open"
                ),
                0.0
            ),

            "high": _float(
                exact.get(
                    "high"
                ),
                0.0
            ),

            "low": _float(
                exact.get(
                    "low"
                ),
                0.0
            ),

            "source": "delta_bulk",
        }

    except Exception as exc:

        print(
            f"Delta bulk ticker failed "
            f"[{requested_symbol}]: {exc}"
        )

    # METHOD 3: latest 5m candle fallback. Delta's documented
    # candles endpoint requires start/end timestamps.
    try:
        candles = get_candles(symbol=requested_symbol, resolution="5m", limit=2)
        if candles is not None and not candles.empty and "close" in candles.columns:
            close = _float(candles["close"].iloc[-1], None)
            if close is not None and close > 0:
                return {
                    "symbol": requested_symbol,
                    "price": close,
                    "close": close,
                    "mark_price": close,
                    "spot_price": 0.0,
                    "volume": _float(candles["volume"].iloc[-1], 0.0) if "volume" in candles.columns else 0.0,
                    "source": "delta_5m_candle_fallback",
                }
    except Exception as exc:
        print(f"Delta candle price fallback failed [{requested_symbol}]: {exc}")

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

}


# ==========================================================
# EXTRACT CANDLE ROWS
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
    Download historical OHLCV candles.

    Returns:
        DataFrame with:
        timestamp
        open
        high
        low
        close
        volume

    Index:
        UTC datetime
    """

    symbol = _validate_symbol(symbol)

    resolution = str(
        resolution
    ).lower().strip()


    # ------------------------------------------------------
    # 1 MONTH
    #
    # Delta REST supports standard candle resolutions.
    # Build monthly candles locally from daily candles.
    # ------------------------------------------------------

    if resolution == "1mo":

        try:

            daily = get_candles(
                symbol=symbol,
                resolution="1d",
                limit=max(
                    int(limit) * 32,
                    60
                )
            )

            if daily.empty:
                return _empty_dataframe()

            monthly = (
                daily
                .resample("MS")
                .agg({
                    "timestamp": "first",
                    "open": "first",
                    "high": "max",
                    "low": "min",
                    "close": "last",
                    "volume": "sum",
                })
                .dropna(
                    subset=[
                        "open",
                        "high",
                        "low",
                        "close",
                    ]
                )
            )

            monthly = monthly.tail(
                int(limit)
            )

            return monthly

        except Exception as exc:

            print(
                f"Delta monthly error "
                f"[{symbol}]: {exc}"
            )

            return _empty_dataframe()


    # ------------------------------------------------------
    # Resolution validation
    # ------------------------------------------------------

    if resolution not in RESOLUTION_SECONDS:

        print(
            f"Delta unsupported resolution "
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
        min(
            limit,
            2000
        )
    )


    candle_seconds = (
        RESOLUTION_SECONDS[
            resolution
        ]
    )


    # ------------------------------------------------------
    # Unix time
    # ------------------------------------------------------

    end = int(time.time())

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
    # Request
    # ------------------------------------------------------

    last_error = None

    for attempt in range(RETRIES):

        try:

            payload = _get_json(
                CANDLE_URL,
                params=params
            )

            rows = _extract_rows(
                payload
            )

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
                df[
                    timestamp_column
                ].apply(
                    _timestamp_seconds
                )
            )


            # --------------------------------------------------
            # OHLC
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
                        f"Delta: missing "
                        f"{column} "
                        f"{symbol} "
                        f"{resolution}"
                    )

                    return _empty_dataframe()

                df[column] = pd.to_numeric(
                    df[column],
                    errors="coerce"
                )


            # --------------------------------------------------
            # VOLUME
            # --------------------------------------------------

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
            # INTEGER TIMESTAMP
            # --------------------------------------------------

            df["timestamp"] = (
                df["timestamp"]
                .astype("int64")
            )


            # --------------------------------------------------
            # DUPLICATES
            # --------------------------------------------------

            df.drop_duplicates(
                subset=[
                    "timestamp"
                ],
                keep="last",
                inplace=True
            )


            # --------------------------------------------------
            # SORT
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
            # --------------------------------------------------

            df["datetime"] = pd.to_datetime(
                df["timestamp"],
                unit="s",
                utc=True,
                errors="coerce"
            )

            df.dropna(
                subset=[
                    "datetime"
                ],
                inplace=True
            )


            if df.empty:
                return _empty_dataframe()


            df.set_index(
                "datetime",
                inplace=True
            )

            df.index.name = "datetime"


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


            # --------------------------------------------------
            # LAST LIMIT
            # --------------------------------------------------

            df = df.tail(
                limit
            )


            print(
                f"Delta candles OK: "
                f"{symbol} "
                f"{resolution} "
                f"rows={len(df)} "
                f"last={df.index[-1]}"
            )


            return df


        except Exception as exc:

            last_error = exc

            print(
                f"Delta candle error "
                f"[{symbol} {resolution}] "
                f"attempt={attempt + 1}: "
                f"{exc}"
            )

            if attempt < RETRIES - 1:
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
