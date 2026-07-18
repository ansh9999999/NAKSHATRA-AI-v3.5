"""
NAKSHATRA AI
Delta Exchange India Broker
"""

import time
import hmac
import hashlib
import json
import requests

from config import (
    DELTA_API_KEY,
    DELTA_API_SECRET,
)

BASE_URL = "https://api.india.delta.exchange"


class DeltaBroker:

    def __init__(self):

        self.base_url = BASE_URL
        self.api_key = DELTA_API_KEY
        self.api_secret = DELTA_API_SECRET

    def _timestamp(self):
        return str(int(time.time()))

    def _signature(
        self,
        method,
        path,
        timestamp,
        body=""
    ):

        message = (
            method.upper()
            + timestamp
            + path
            + body
        )

        return hmac.new(
            self.api_secret.encode(),
            message.encode(),
            hashlib.sha256
        ).hexdigest()

    def _headers(
        self,
        method,
        path,
        body=""
    ):

        ts = self._timestamp()

        sign = self._signature(
            method,
            path,
            ts,
            body
        )

        return {

            "api-key": self.api_key,

            "timestamp": ts,

            "signature": sign,

            "Content-Type": "application/json"

        }

    def get_balance(self):

        path = "/v2/wallet/balances"

        headers = self._headers(
            "GET",
            path
        )

        r = requests.get(
            self.base_url + path,
            headers=headers,
            timeout=15
        )

        r.raise_for_status()

        return r.json()

    def get_positions(self):

        path = "/v2/positions"

        headers = self._headers(
            "GET",
            path
        )

        r = requests.get(
            self.base_url + path,
            headers=headers,
            timeout=15
        )

        r.raise_for_status()

        return r.json()
          def place_market_order(
        self,
        product_id,
        side,
        size
    ):

        path = "/v2/orders"

        payload = {

            "product_id": product_id,

            "size": size,

            "side": side.lower(),

            "order_type": "market"

        }

        body = json.dumps(payload)

        headers = self._headers(
            "POST",
            path,
            body
        )

        response = requests.post(

            self.base_url + path,

            headers=headers,

            data=body,

            timeout=15

        )

        response.raise_for_status()

        return response.json()


    def place_limit_order(

        self,

        product_id,

        side,

        size,

        limit
          def place_order(
        self,
        product_id,
        side,
        size,
        order_type="market",
        limit_price=None
    ):
        """
        Generic order placement wrapper.
        """

        try:

            if order_type.lower() == "market":

                return self.place_market_order(
                    product_id=product_id,
                    side=side,
                    size=size
                )

            elif order_type.lower() == "limit":

                return self.place_limit_order(
                    product_id=product_id,
                    side=side,
                    size=size,
                    limit_price=limit_price
                )

            else:

                raise ValueError("Unsupported order type")

        except requests.RequestException as e:

            return {
                "success": False,
                "error": str(e)
            }

        except Exception as e:

            return {
                "success": False,
                "error": str(e)
            }


    def close_position(
        self,
        product_id,
        side,
        size
    ):
        """
        Close an existing position using
        opposite market order.
        """

        opposite_side = "sell"

        if side.lower() == "sell":
            opposite_side = "buy"

        return self.place_market_order(
            product_id=product_id,
            side=opposite_side,
            size=size
        )


    def get_position(
        self,
        product_id
    ):

        try:

            positions = self.get_positions()

            if "result" not in positions:
                return None

            for position in positions["result"]:

                if position["product_id"] == product_id:
                    return position

            return None

        except Exception:

            return None


    def cancel_all_orders(self):

        try:

            orders = self.get_open_orders()

            if "result" not in orders:
                return

            for order in orders["result"]:

                self.cancel_order(
                    order["id"]
                )

        except Exception:

            pass


    def health(self):

        try:

            self.get_balance()

            return True

        except Exception:

            return False


if __name__ == "__main__":

    broker = DeltaBroker()

    print("========== DELTA TEST ==========")

    print("Connection :", broker.health())

    try:

        balance = broker.get_balance()

        print(balance)

    except Exception as e:

        print(e)
