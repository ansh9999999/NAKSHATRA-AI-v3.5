"""
NAKSHATRA AI v4.0 - Delta Exchange market data helper

This file was missing from the previous deployment package.
The existing project imports:
    from delta import get_ticker

So this module restores that import and keeps the configured
DELTA_BASE_URL compatible with either:
    https://api.india.delta.exchange
or:
    https://api.india.delta.exchange/v2
"""

import requests

from config import DELTA_BASE_URL
from logger import logger


def _ticker_url(symbol: str) -> str:
    base = str(DELTA_BASE_URL).rstrip("/")

    if base.endswith("/v2"):
        return f"{base}/tickers/{symbol.upper()}"

    return f"{base}/v2/tickers/{symbol.upper()}"


def get_ticker(symbol="BTCUSD"):
    symbol = symbol.upper()

    try:
        url = _ticker_url(symbol)
        response = requests.get(url, timeout=8)
        response.raise_for_status()

        payload = response.json()
        data = payload.get("result")

        if not data:
            logger.warning("Delta ticker returned no result for %s", symbol)
            return None

        result = {
            "symbol": data.get("symbol", symbol),
            "price": float(data["close"]) if data.get("close") is not None else None,
            "mark_price": (
                float(data["mark_price"])
                if data.get("mark_price") is not None
                else None
            ),
            "volume": (
                float(data["volume"])
                if data.get("volume") is not None
                else None
            ),
        }

        # Preserve any useful raw fields without making the dashboard
        # dependent on them.
        result["raw"] = data
        return result

    except Exception as exc:
        logger.warning("Delta ticker error %s: %s", symbol, exc)
        return None
