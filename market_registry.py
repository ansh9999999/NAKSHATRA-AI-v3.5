"""
NAKSHATRA AI - Central Market Registry

Crypto:
    BTCUSD / ETHUSD -> Delta Exchange

Indian markets:
    NIFTY50 / BANKNIFTY / SENSEX / NIFTYIT / MCX
    -> Kotak Neo

This file contains no credentials and performs no network calls.
"""

MARKETS = {
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

    "NIFTY50": {
        "name": "NIFTY 50",
        "display": "NIFTY",
        "asset_class": "INDEX",
        "exchange": "NSE",
        "provider": "kotak_neo",
        "neo_exchange_segment": "nse_cm",
        "neo_symbol_candidates": ["NIFTY 50", "NIFTY50", "NIFTY"],
        "data_symbol": "NIFTY 50",
        "option_chain": True,
    },
    "BANKNIFTY": {
        "name": "NIFTY BANK",
        "display": "BANKNIFTY",
        "asset_class": "INDEX",
        "exchange": "NSE",
        "provider": "kotak_neo",
        "neo_exchange_segment": "nse_cm",
        "neo_symbol_candidates": ["NIFTY BANK", "BANKNIFTY", "NIFTYBANK"],
        "data_symbol": "NIFTY BANK",
        "option_chain": True,
    },
    "SENSEX": {
        "name": "SENSEX",
        "display": "SENSEX",
        "asset_class": "INDEX",
        "exchange": "BSE",
        "provider": "kotak_neo",
        "neo_exchange_segment": "bse_cm",
        "neo_symbol_candidates": ["SENSEX"],
        "data_symbol": "SENSEX",
        "option_chain": True,
    },
    "NIFTYIT": {
        "name": "NIFTY IT",
        "display": "NIFTY IT",
        "asset_class": "INDEX",
        "exchange": "NSE",
        "provider": "kotak_neo",
        "neo_exchange_segment": "nse_cm",
        "neo_symbol_candidates": ["NIFTY IT", "NIFTYIT", "CNXIT"],
        "data_symbol": "NIFTY IT",
        "option_chain": False,
    },

    "GOLD": {
        "name": "Gold",
        "display": "GOLD",
        "asset_class": "COMMODITY",
        "exchange": "MCX",
        "provider": "kotak_neo",
        "neo_exchange_segment": "mcx_fo",
        "neo_symbol_candidates": ["GOLD", "GOLDM"],
        "data_symbol": "GOLD",
        "option_chain": True,
    },
    "SILVER": {
        "name": "Silver",
        "display": "SILVER",
        "asset_class": "COMMODITY",
        "exchange": "MCX",
        "provider": "kotak_neo",
        "neo_exchange_segment": "mcx_fo",
        "neo_symbol_candidates": ["SILVER", "SILVERM"],
        "data_symbol": "SILVER",
        "option_chain": True,
    },
    "CRUDEOIL": {
        "name": "Crude Oil",
        "display": "CRUDE OIL",
        "asset_class": "COMMODITY",
        "exchange": "MCX",
        "provider": "kotak_neo",
        "neo_exchange_segment": "mcx_fo",
        "neo_symbol_candidates": ["CRUDEOIL", "CRUDE OIL", "CRUDE"],
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
    "NIFTY 50": "NIFTY50",
    "NIFTY50": "NIFTY50",
    "NIFTY_BANK": "BANKNIFTY",
    "NIFTY BANK": "BANKNIFTY",
    "BANK NIFTY": "BANKNIFTY",
    "BANKNIFTY": "BANKNIFTY",
    "SENSEX": "SENSEX",
    "NIFTY_IT": "NIFTYIT",
    "NIFTY IT": "NIFTYIT",
    "CNXIT": "NIFTYIT",
    "NIFTYIT": "NIFTYIT",

    "GOLD": "GOLD",
    "GOLDM": "GOLD",
    "SILVER": "SILVER",
    "SILVERM": "SILVER",
    "CRUDE": "CRUDEOIL",
    "CRUDE OIL": "CRUDEOIL",
    "CRUDEOIL": "CRUDEOIL",
}


def canonical_symbol(value, default="NIFTY50"):
    s = str(value or "").strip().upper()
    if s in ("", "UNDEFINED", "NULL", "NONE", "NAN"):
        return default
    return ALIASES.get(s, s)


def get_market(value, default=None):
    return MARKETS.get(canonical_symbol(value), default)


def is_supported(value):
    return canonical_symbol(value, default="") in MARKETS


def symbols():
    return list(MARKETS.keys())
