"""
NAKSHATRA AI
Historical Candle Data
Phase 3 - Debug Version
"""

import requests
import pandas as pd

from config import DELTA_BASE_URL
from logger import logger


# ==========================================================
# Fetch History
# ==========================================================

def _fetch_history(symbol, resolution="5m", limit=200):

    url = f"{DELTA_BASE_URL}/v2/history/candles"

    params = {
        "symbol": symbol,
        "resolution": resolution,
        "limit": limit
    }

    logger.info("=" * 60)
    logger.info(f"SYMBOL     : {symbol}")
    logger.info(f"RESOLUTION : {resolution}")
    logger.info(f"LIMIT      : {limit}")
    logger.info(f"URL        : {url}")

    for attempt in range(3):

        try:

            response = requests.get(
                url,
                params=params,
                timeout=20
            )

            logger.info(
                f"HTTP STATUS : {response.status_code}"
            )

            logger.info(
                f"RAW RESPONSE : {response.text[:500]}"
            )

            response.raise_for_status()

            json_data = response.json()

            data = json_data.get("result", [])

            logger.info(
                f"CANDLES RECEIVED : {len(data)}"
            )

            if len(data) == 0:

                logger.error(
                    f"NO DATA -> {symbol} {resolution}"
                )

                continue

            df = pd.DataFrame(data)

            if "time" in df.columns:

                df.rename(
                    columns={
                        "time": "timestamp"
                    },
                    inplace=True
                )

            numeric_columns = [
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]
            for col in numeric_columns:

                if col in df.columns:

                    df[col] = pd.to_numeric(
                        df[col],
                        errors="coerce"
                    )

            df.dropna(inplace=True)

            if "timestamp" in df.columns:

                df.sort_values(
                    "timestamp",
                    inplace=True
                )

            df.reset_index(
                drop=True,
                inplace=True
            )

            logger.info(
                f"SUCCESS -> {symbol} {resolution} Rows={len(df)}"
            )

            return df

        except requests.RequestException as e:

            logger.exception(
                f"REQUEST ERROR : {symbol} {resolution}"
            )

            logger.exception(e)

        except Exception as e:

            logger.exception(
                f"UNKNOWN ERROR : {symbol} {resolution}"
            )

            logger.exception(e)

    logger.error(
        f"FAILED AFTER 3 ATTEMPTS : {symbol} {resolution}"
    )

    return pd.DataFrame()


# ==========================================================
# Existing Function
# ==========================================================

def get_history(symbol, resolution="5m", limit=200):

    return _fetch_history(
        symbol,
        resolution,
        limit
    )


# ==========================================================
# Multi Timeframe
# ==========================================================

def get_multi_timeframe_history(symbol, limit=200):

    return {

        "5m": _fetch_history(symbol, "5m", limit),

        "15m": _fetch_history(symbol, "15m", limit),

        "1h": _fetch_history(symbol, "1h", limit),

        "1d": _fetch_history(symbol, "1d", limit),

        "1w": _fetch_history(symbol, "1w", limit),

        "1mo": _fetch_history(symbol, "1mo", limit),

                }
