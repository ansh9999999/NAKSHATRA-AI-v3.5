"""
NAKSHATRA AI
History Engine v6.1
Delta Exchange Live History
"""

import time
import requests
import pandas as pd

from config import DELTA_BASE_URL
from logger import logger


# ==========================================================
# Delta History
# ==========================================================

def _fetch_history(symbol, resolution="5m", limit=200):

    logger.info("=" * 70)
    logger.info("Fetching History")
    logger.info(f"Symbol      : {symbol}")
    logger.info(f"Resolution  : {resolution}")
    logger.info(f"Limit       : {limit}")

    # Candle duration in seconds
    resolution_seconds = {
        "1m": 60,
        "3m": 180,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "2h": 7200,
        "4h": 14400,
        "6h": 21600,
        "1d": 86400,
        "1w": 604800
    }

    if resolution not in resolution_seconds:
        logger.error(f"Unsupported resolution: {resolution}")
        return pd.DataFrame()

    # Current Unix time in seconds
    end_time = int(time.time())

    # Calculate start time for requested number of candles
    start_time = end_time - (
        limit * resolution_seconds[resolution]
    )

    endpoint = f"{DELTA_BASE_URL}/v2/history/candles"

    params = {
        "symbol": symbol,
        "resolution": resolution,
        "start": start_time,
        "end": end_time
    }

    logger.info(f"Endpoint    : {endpoint}")
    logger.info(f"Start       : {start_time}")
    logger.info(f"End         : {end_time}")

    for attempt in range(1, 4):

        try:

            logger.info(f"Attempt {attempt}")

            response = requests.get(
                endpoint,
                params=params,
                headers={
                    "Accept": "application/json"
                },
                timeout=20
            )

            logger.info(
                f"HTTP Status : {response.status_code}"
            )

            response.raise_for_status()

            payload = response.json()

            logger.info(
                f"API Success : {payload.get('success')}"
            )

            candles = payload.get("result", [])

            logger.info(
                f"Candles     : {len(candles)}"
            )

            if not candles:

                logger.warning(
                    f"No candle data for {symbol} {resolution}"
                )

                time.sleep(1)
                continue

            # --------------------------------------------------
            # Convert response to DataFrame
            # --------------------------------------------------

            df = pd.DataFrame(candles)

            logger.info(
                f"Raw columns : {list(df.columns)}"
            )

            # Delta returns candle timestamp as "time"
            if "time" in df.columns:

                df.rename(
                    columns={
                        "time": "timestamp"
                    },
                    inplace=True
                )

            # --------------------------------------------------
            # Numeric columns
            # --------------------------------------------------

            numeric_columns = [
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]

            for column in numeric_columns:

                if column in df.columns:

                    df[column] = pd.to_numeric(
                        df[column],
                        errors="coerce"
                    )

            # Remove invalid rows
            df.dropna(
                subset=[
                    "open",
                    "high",
                    "low",
                    "close"
                ],
                inplace=True
            )

            # --------------------------------------------------
            # Timestamp
            # --------------------------------------------------

            if "timestamp" in df.columns:

                df["timestamp"] = pd.to_datetime(
                    df["timestamp"],
                    unit="s",
                    utc=True,
                    errors="coerce"
                )

                df.dropna(
                    subset=["timestamp"],
                    inplace=True
                )

                df.set_index(
                    "timestamp",
                    inplace=True
                )

            # --------------------------------------------------
            # Sort oldest -> newest
            # --------------------------------------------------

            df.sort_index(
                inplace=True
            )

            # Keep only requested number of candles
            if len(df) > limit:

                df = df.tail(limit)

            logger.info(
                f"Loaded {len(df)} candles "
                f"for {symbol} {resolution}"
            )

            if not df.empty:

                logger.info(
                    f"Latest candle: {df.index[-1]}"
                )

                logger.info(
                    f"Latest close : {df['close'].iloc[-1]}"
                )

            return df

        except requests.HTTPError as e:

            logger.exception(
                f"HTTP Error : {e}"
            )

        except requests.RequestException as e:

            logger.exception(
                f"Network Error : {e}"
            )

        except ValueError as e:

            logger.exception(
                f"JSON Error : {e}"
            )

        except Exception as e:

            logger.exception(
                f"Unknown Error : {e}"
            )

        time.sleep(1)

    logger.error(
        f"Failed to fetch history for "
        f"{symbol} {resolution}"
    )

    return pd.DataFrame()


# ==========================================================
# Compatibility
# ==========================================================

def get_history(
    symbol,
    resolution="5m",
    limit=200
):

    return _fetch_history(
        symbol,
        resolution,
        limit
    )


# ==========================================================
# Multi Timeframe
# ==========================================================

def get_multi_timeframe_history(
    symbol,
    limit=200
):

    logger.info("=" * 70)
    logger.info(
        f"MULTI TIMEFRAME HISTORY START: {symbol}"
    )
    logger.info("=" * 70)

    data = {

        "symbol": symbol,

        "5m": _fetch_history(
            symbol,
            "5m",
            limit
        ),

        "15m": _fetch_history(
            symbol,
            "15m",
            limit
        ),

        "1h": _fetch_history(
            symbol,
            "1h",
            limit
        ),

        "1d": _fetch_history(
            symbol,
            "1d",
            limit
        )

    }

    logger.info(
        f"5m candles  : {len(data['5m'])}"
    )

    logger.info(
        f"15m candles : {len(data['15m'])}"
    )

    logger.info(
        f"1h candles  : {len(data['1h'])}"
    )

    logger.info(
        f"1d candles  : {len(data['1d'])}"
    )

    logger.info(
        f"MULTI TIMEFRAME HISTORY END: {symbol}"
    )

    return data
