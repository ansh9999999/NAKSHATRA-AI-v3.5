"""
NAKSHATRA AI
History Engine v6.0
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

  print("===== HISTORY.PY CALLED =====")
    endpoint = f"{DELTA_BASE_URL}/v2/history/candles"

    params = {
        "symbol": symbol,
        "resolution": resolution,
        "limit": limit
    }

    logger.info("=" * 70)
    logger.info(f"Fetching History")
    logger.info(f"Symbol      : {symbol}")
    logger.info(f"Resolution  : {resolution}")
    logger.info(f"Limit       : {limit}")

    for attempt in range(1, 4):

        try:

            logger.info(f"Attempt {attempt}")

            response = requests.get(
                endpoint,
                params=params,
                timeout=20
            )

            logger.info(
                f"HTTP Status : {response.status_code}"
            )

            response.raise_for_status()

            payload = response.json()

          print("STATUS =", response.status_code)
          print("FULL RESPONSE =", payload)
          print("RESULT =", payload.get("result"))
            logger.info(
                f"Success : {payload.get('success')}"
            )

            candles = payload.get("result", [])

            print("FULL RESPONSE =", payload)
            print("RESULT TYPE =", type(payload.get("result")))
            logger.info(
                f"Candles : {len(candles)}"
            )

            if len(candles) == 0:

                logger.warning(
                    f"No candle data for {symbol}"
                )

                time.sleep(1)

                continue

            df = pd.DataFrame(candles)

            if "time" in df.columns:

                df.rename(
                    columns={
                        "time": "timestamp"
                    },
                    inplace=True
                )

            numeric = [
                "open",
                "high",
                "low",
                "close",
                "volume"
            ]
            for col in numeric:

                if col in df.columns:

                    df[col] = pd.to_numeric(
                        df[col],
                        errors="coerce"
                    )

            df.dropna(inplace=True)

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

            df.sort_index(inplace=True)

            logger.info(
                f"Loaded {len(df)} candles"
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

        except Exception as e:

            logger.exception(
                f"Unknown Error : {e}"
            )

        time.sleep(1)

    logger.error(
        f"Failed to fetch history for {symbol}"
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

    return {

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
