"""
NAKSHATRA AI
Delta Exchange India Broker
"""

import time
import hmac
import hashlib
import json
import requests

from config import DELTA_API_KEY, DELTA_API_SECRET

BASE_URL = "https://api.india.delta.exchange"


class DeltaBroker:
    def __init__(self):
        self.base_url = BASE_URL
        self.api_key = DELTA_API_KEY
        self.api_secret = DELTA_API_SECRET

    def _timestamp(self):
        return str(int(time.time()))

    def _signature(self, method, path, timestamp, body=""):
        msg = method.upper() + timestamp + path + body
        return hmac.new(
            self.api_secret.encode(),
            msg.encode(),
            hashlib.sha256
        ).hexdigest()

    def _headers(self, method, path, body=""):
        ts = self._timestamp()
        return {
            "api-key": self.api_key,
            "timestamp": ts,
            "signature": self._signature(method, path, ts, body),
            "Content-Type": "application/json",
        }

    def get_balance(self):
        path = "/v2/wallet/balances"
        r = requests.get(
            self.base_url + path,
            headers=self._headers("GET", path),
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def get_positions(self):
        path = "/v2/positions"
        r = requests.get(
            self.base_url + path,
            headers=self._headers("GET", path),
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def place_market_order(self, product_id, side, size):
        return self.place_order(
            product_id=product_id,
            side=side,
            size=size,
            order_type="market",
        )

    def place_limit_order(self, product_id, side, size, limit_price):
        return self.place_order(
            product_id=product_id,
            side=side,
            size=size,
            order_type="limit",
            limit_price=limit_price,
        )

    def place_order(self, product_id, side, size,
                    order_type="market", limit_price=None):
        path = "/v2/orders"
        payload = {
            "product_id": product_id,
            "size": size,
            "side": side.lower(),
            "order_type": order_type.lower(),
        }
        if order_type.lower() == "limit":
            payload["limit_price"] = limit_price

        body = json.dumps(payload)

        r = requests.post(
            self.base_url + path,
            headers=self._headers("POST", path, body),
            data=body,
            timeout=15,
        )
        r.raise_for_status()
        return r.json()

    def close_position(self, product_id, side, size):
        opposite = "buy" if side.lower() == "sell" else "sell"
        return self.place_market_order(product_id, opposite, size)

    def health(self):
        try:
            self.get_balance()
            return True
        except Exception:
            return False


if __name__ == "__main__":
    broker = DeltaBroker()
    print("Connection:", broker.health())
