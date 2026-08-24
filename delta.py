import requests

BASE_URL = "https://api.india.delta.exchange/v2"


def get_ticker(symbol="BTCUSD"):
    try:
        url = f"{BASE_URL}/tickers/{symbol}"
        r = requests.get(url, timeout=10)

        if r.status_code != 200:
            return None

        data = r.json()["result"]

        return {
            "symbol": data["symbol"],
            "price": float(data["close"]),
            "mark_price": float(data["mark_price"]),
            "volume": float(data["volume"]),
        }

    except Exception as e:
        print("Delta Error:", e)
        return None
