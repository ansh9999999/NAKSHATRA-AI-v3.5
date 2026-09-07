"""
NAKSHATRA AI - Market Registry
Central registry for supported markets.

IMPORTANT:
This file only defines market identity/routing metadata.
It does NOT fetch market data and it does NOT contain broker credentials.
"""

MARKETS = {
    # Crypto markets - existing Delta Exchange feed
    "BTCUSD": {
        "name": "Bitcoin",
        "display": "BTCUSD",
        "asset_class": "CRYPTO",
        "exchange": "DELTA",
        "provider": "delta",
        "data_symbol": "BTCUSD",
        "option_chain": False,
    },
    "ETHUSD": {
        "name": "Ethereum",
        "display": "ETHUSD",
        "asset_class": "CRYPTO",
        "exchange": "DELTA",
        "provider": "delta",
        "data_symbol": "ETHUSD",
        "option_chain": False,
    },

    # Indian cash/index markets
    "NIFTY50": {
        "name": "NIFTY 50",
        "display": "NIFTY",
        "asset_class": "INDEX",
        "exchange": "NSE",
        "provider": "yahoo",
        "data_symbol": "^NSEI",
        "option_chain": True,
    },
    "BANKNIFTY": {
        "name": "NIFTY BANK",
        "display": "BANKNIFTY",
        "asset_class": "INDEX",
        "exchange": "NSE",
        "provider": "yahoo",
        "data_symbol": "^NSEBANK",
        "option_chain": True,
    },
    "SENSEX": {
        "name": "SENSEX",
        "display": "SENSEX",
        "asset_class": "INDEX",
        "exchange": "BSE",
        "provider": "yahoo",
        "data_symbol": "^BSESN",
        "option_chain": True,
    },
    "NIFTYIT": {
        "name": "NIFTY IT",
        "display": "NIFTY IT",
        "asset_class": "INDEX",
        "exchange": "NSE",
        "provider": "yahoo",
        "data_symbol": "^CNXIT",
        "option_chain": True,
    },

    # MCX commodities - identifiers reserved for the MCX/Neo data adapter.
    "GOLD": {
        "name": "Gold",
        "display": "GOLD",
        "asset_class": "COMMODITY",
        "exchange": "MCX",
        "provider": "kotak_neo",
        "data_symbol": "GOLD",
        "option_chain": True,
    },
    "SILVER": {
        "name": "Silver",
        "display": "SILVER",
        "asset_class": "COMMODITY",
        "exchange": "MCX",
        "provider": "kotak_neo",
        "data_symbol": "SILVER",
        "option_chain": True,
    },
    "CRUDEOIL": {
        "name": "Crude Oil",
        "display": "CRUDE OIL",
        "asset_class": "COMMODITY",
        "exchange": "MCX",
        "provider": "kotak_neo",
        "data_symbol": "CRUDEOIL",
        "option_chain": True,
    },
}

ALIASES = {
    "BTC": "BTCUSD",
    "BTC/USDT": "BTCUSD",
    "BTC-USDT": "BTCUSD",
    "ETH": "ETHUSD",
    "ETH/USDT": "ETHUSD",
    "ETH-USDT": "ETHUSD",

    "NIFTY": "NIFTY50",
    "NIFTY50": "NIFTY50",
    "NIFTY 50": "NIFTY50",
    "NIFTY_BANK": "BANKNIFTY",
    "NIFTY BANK": "BANKNIFTY",
    "BANK NIFTY": "BANKNIFTY",
    "SENSEX": "SENSEX",
    "NIFTY_IT": "NIFTYIT",
    "NIFTY IT": "NIFTYIT",
    "CNXIT": "NIFTYIT",

    "GOLD": "GOLD",
    "GOLDM": "GOLD",
    "SILVER": "SILVER",
    "SILVERM": "SILVER",
    "CRUDE": "CRUDEOIL",
    "CRUDE OIL": "CRUDEOIL",
    "CRUDEOIL": "CRUDEOIL",
}


def canonical_symbol(value, default="NIFTY50"):
    """Return the internal canonical market symbol."""
    s = str(value or "").strip().upper()
    if s in ("", "UNDEFINED", "NULL", "NONE", "NAN"):
        return default
    return ALIASES.get(s, s)


def get_market(value, default=None):
    """Return market metadata for a symbol."""
    symbol = canonical_symbol(value)
    return MARKETS.get(symbol, default)


def is_supported(value):
    return canonical_symbol(value, default="") in MARKETS


def symbols():
    return list(MARKETS.keys())
