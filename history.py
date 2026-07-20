"""
NAKSHATRA AI
Historical Candle Data
Phase 2 - Multi Timeframe Engine
"""

import requests
import pandas as pd

from config import DELTA_BASE_URL


def _fetch_history(symbol, resolution="5m", limit=200):

    url = f"{DELTA_BASE_URL}/v2/history/candles"

    params = {
        "symbol": symbol,
        "resolution": resolution,
        "limit": limit
    }

    for attempt in range(3):

        try:

            response = requests.get(
                url,
                params=params,
                timeout=15
            )

            response.raise_for_status()

            data = response.json().get("result", [])

            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data)

            if "time" in df.columns:
                df.rename(
                    columns={"time": "timestamp"},
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

            return df

        except requests.RequestException:

            if attempt == 2:
                return pd.DataFrame()

        except Exception:
            return pd.DataFrame()

    return pd.DataFrame()


# --------------------------
# Existing Function
# --------------------------

def get_history(symbol, resolution="5m", limit=200):
    """
    Backward compatible
    Existing scanner continues to work
    """
    return _fetch_history(symbol, resolution, limit)


# --------------------------
# Phase 2 Multi Timeframe
# --------------------------

def get_multi_timeframe_history(symbol, limit=200):

    return {

        "5m": _fetch_history(symbol, "5m", limit),

        "15m": _fetch_history(symbol, "15m", limit),

        "1h": _fetch_history(symbol, "1h", limit),

        "1d": _fetch_history(symbol, "1d", limit),

        "1w": _fetch_history(symbol, "1w", limit),

        "1mo": _fetch_history(symbol, "1mo", limit),

    }
