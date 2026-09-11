"""Read-only Kotak Neo smoke test for NAKSHATRA.
Run locally after setting NEO_CONSUMER_KEY and NEO_ACCESS_TOKEN.
No order APIs are called.
"""
from kotak_neo_adaptor import get_quote, get_history

for symbol in ("NIFTY50", "BANKNIFTY", "SENSEX", "NIFTYIT", "GOLD", "SILVER", "CRUDEOIL"):
    print(f"\n=== {symbol} ===")
    try:
        print("QUOTE:", get_quote(symbol))
    except Exception as exc:
        print("QUOTE ERROR:", exc)
    try:
        df = get_history(symbol, "5m", 20)
        print("HISTORY:", len(df), "rows", "last=" + str(df["close"].iloc[-1]) if not df.empty else "empty")
    except Exception as exc:
        print("HISTORY ERROR:", exc)
