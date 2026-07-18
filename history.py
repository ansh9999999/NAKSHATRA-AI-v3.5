"""
NAKSHATRA AI
Historical Candle Data
"""

import requests
import pandas as pd

from config import DELTA_BASE_URL


def get_history(
    symbol,
    resolution="5m",
    limit=200
):

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

            data = response.json().get(
                "result",
                []
            )

            if not data:
                return pd.DataFrame()

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

            for column in numeric_columns:

                if column in df.columns:

                    df[column] = pd.to_numeric(
                        df[column],
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
