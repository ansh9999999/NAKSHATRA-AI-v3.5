"""NAKSHATRA market registry and provider routing.

Indian markets are deliberately routed to Kotak Neo; BTC/ETH remain on Delta.
"""

MARKETS = {
    "BTCUSD": {"asset_class": "CRYPTO", "exchange": "DELTA", "provider": "delta", "option_chain": True},
    "ETHUSD": {"asset_class": "CRYPTO", "exchange": "DELTA", "provider": "delta", "option_chain": True},
    "NIFTY50": {"asset_class": "INDEX", "exchange": "NSE", "provider": "kotak_neo", "neo_segment": "nse_cm", "neo_symbols": ["Nifty 50", "NIFTY 50", "NIFTY"], "option_chain": True},
    "BANKNIFTY": {"asset_class": "INDEX", "exchange": "NSE", "provider": "kotak_neo", "neo_segment": "nse_cm", "neo_symbols": ["Nifty Bank", "BANKNIFTY", "NIFTY BANK"], "option_chain": True},
    "SENSEX": {"asset_class": "INDEX", "exchange": "BSE", "provider": "kotak_neo", "neo_segment": "bse_cm", "neo_symbols": ["SENSEX", "BSE SENSEX"], "option_chain": True},
    "NIFTYIT": {"asset_class": "INDEX", "exchange": "NSE", "provider": "kotak_neo", "neo_segment": "nse_cm", "neo_symbols": ["NIFTY IT", "Nifty IT"], "option_chain": False},
    "GOLD": {"asset_class": "COMMODITY", "exchange": "MCX", "provider": "kotak_neo", "neo_segment": "mcx_fo", "neo_symbols": ["GOLD"], "option_chain": True},
    "SILVER": {"asset_class": "COMMODITY", "exchange": "MCX", "provider": "kotak_neo", "neo_segment": "mcx_fo", "neo_symbols": ["SILVER"], "option_chain": True},
    "CRUDEOIL": {"asset_class": "COMMODITY", "exchange": "MCX", "provider": "kotak_neo", "neo_segment": "mcx_fo", "neo_symbols": ["CRUDEOIL", "CRUDE OIL"], "option_chain": True},
}

ALIASES = {
    "NIFTY": "NIFTY50", "NIFTY50": "NIFTY50", "NIFTY 50": "NIFTY50",
    "BANKNIFTY": "BANKNIFTY", "NIFTYBANK": "BANKNIFTY", "NIFTY BANK": "BANKNIFTY",
    "SENSEX": "SENSEX", "NIFTYIT": "NIFTYIT", "NIFTY IT": "NIFTYIT",
    "GOLD": "GOLD", "GOLDM": "GOLD", "SILVER": "SILVER", "SILVERM": "SILVER",
    "CRUDE": "CRUDEOIL", "CRUDEOIL": "CRUDEOIL", "CRUDE OIL": "CRUDEOIL",
    "BTC": "BTCUSD", "BTC/USDT": "BTCUSD", "BTC-USDT": "BTCUSD",
    "ETH": "ETHUSD", "ETH/USDT": "ETHUSD", "ETH-USDT": "ETHUSD",
}


def canonical_symbol(symbol, default="NIFTY50"):
    s = str(symbol or "").strip().upper()
    if not s or s in {"UNDEFINED", "NULL", "NONE", "NAN"}:
        return default
    return ALIASES.get(s, s)


def get_market(symbol):
    return MARKETS.get(canonical_symbol(symbol))


def is_supported(symbol):
    return canonical_symbol(symbol) in MARKETS
