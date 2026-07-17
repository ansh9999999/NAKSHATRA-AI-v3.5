import requests
import pandas as pd
from config import BASE_URL


def get_history(symbol, resolution="5m", limit=200):
    url = f"{BASE_URL}/v2/history/candles"

    params = {
        "symbol": symbol,
        "resolution": resolution,
        "limit": limit
    }

    response = requests.get(url, params=params, timeout=15)
    response.raise_for_status()

    data = response.json().get("result", [])

    if not data:
        return pd.DataFrame()

    df = pd.DataFrame(data)

    df = df.rename(columns={
        "time": "timestamp"
    })

    numeric_columns = ["open", "high", "low", "close", "volume"]

    for col in numeric_columns:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col])

    df = df.sort_values("timestamp").reset_index(drop=True)

    return df
