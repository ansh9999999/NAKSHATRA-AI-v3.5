"""
NAKSHATRA AI - Market Registry
Central registry for supported markets.

IMPORTANT:
This file only defines market identity/routing metadata.
It does NOT fetch market data and it does NOT contain broker credentials.

INDIAN MARKETS:
NIFTY/BANKNIFTY/SENSEX/NIFTY IT are routed through Kotak Neo.
BTC/ETH continue through Delta Exchange.
MCX commodities are routed through Kotak Neo.
"""

MARKETS = {
    # ==========================================================
    # CRYPTO - DELTA EXCHANGE
    # ==========================================================
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

    # ==========================================================
    # INDIAN INDEX MARKETS - KOTAK NEO
    #
    # Kotak Neo uses the index display name together with the
    # exchange segment for index historical/quote requests.
    # ==========================================================
    "NIFTY50": {
        "name": "NIFTY 50",
        "display": "NIFTY",
        "asset_class": "INDEX",
        "exchange": "NSE",
        "provider": "kotak_neo",
        "data_symbol": "Nifty 50",
        "neo_exchange_segment": "nse_cm",
        "neo_symbol_candidates": [
            "Nifty 50",
            "NIFTY",
            "NIFTY50",
        ],
        "option_chain": True,
    },

    "BANKNIFTY": {
        "name": "NIFTY BANK",
        "display": "BANKNIFTY",
        "asset_class": "INDEX",
        "exchange": "NSE",
        "provider": "kotak_neo",
        "data_symbol": "Nifty Bank",
        "neo_exchange_segment": "nse_cm",
        "neo_symbol_candidates": [
            "Nifty Bank",
            "BANKNIFTY",
            "NIFTYBANK",
        ],
        "option_chain": True,
    },

    "SENSEX": {
        "name": "SENSEX",
        "display": "SENSEX",
        "asset_class": "INDEX",
        "exchange": "BSE",
        "provider": "kotak_neo",
        "data_symbol": "SENSEX",
        "neo_exchange_segment": "bse_cm",
        "neo_symbol_candidates": [
            "SENSEX",
        ],
        "option_chain": True,
    },

    "NIFTYIT": {
        "name": "NIFTY IT",
        "display": "NIFTY IT",
        "asset_class": "INDEX",
        "exchange": "NSE",
        "provider": "kotak_neo",
        "data_symbol": "Nifty IT",
        "neo_exchange_segment": "nse_cm",
        "neo_symbol_candidates": [
            "Nifty IT",
            "NIFTY IT",
            "NIFTYIT",
            "CNXIT",
        ],
        "option_chain": True,
    },

    # ==========================================================
    # MCX COMMODITIES - KOTAK NEO
    # ==========================================================
    "GOLD": {
        "name": "Gold",
        "display": "GOLD",
        "asset_class": "COMMODITY",
        "exchange": "MCX",
        "provider": "kotak_neo",
        "data_symbol": "GOLD",
        "neo_exchange_segment": "mcx_fo",
        "neo_symbol_candidates": [
            "GOLD",
            "GOLDM",
        ],
        "option_chain": True,
    },

    "SILVER": {
        "name": "Silver",
        "display": "SILVER",
        "asset_class": "COMMODITY",
        "exchange": "MCX",
        "provider": "kotak_neo",
        "data_symbol": "SILVER",
        "neo_exchange_segment": "mcx_fo",
        "neo_symbol_candidates": [
            "SILVER",
            "SILVERM",
        ],
        "option_chain": True,
    },

    "CRUDEOIL": {
        "name": "Crude Oil",
        "display": "CRUDE OIL",
        "asset_class": "COMMODITY",
        "exchange": "MCX",
        "provider": "kotak_neo",
        "data_symbol": "CRUDEOIL",
        "neo_exchange_segment": "mcx_fo",
        "neo_symbol_candidates": [
            "CRUDEOIL",
            "CRUDE OIL",
            "CRUDE",
        ],
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
    "BANKNIFTY": "BANKNIFTY",

    "SENSEX": "SENSEX",

    "NIFTY_IT": "NIFTYIT",
    "NIFTY IT": "NIFTYIT",
    "NIFTYIT": "NIFTYIT",
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
    """Return True when the symbol exists in MARKETS."""
    return canonical_symbol(value, default="") in MARKETS


def symbols():
    """Return all supported canonical symbols."""
    return list(MARKETS.keys())
