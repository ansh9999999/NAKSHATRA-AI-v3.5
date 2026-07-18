"""
NAKSHATRA AI
Broker Manager
"""

from config import BROKER_TYPE

from broker.paper import PaperBroker
from broker.delta import DeltaBroker


class BrokerManager:

    def __init__(self):

        if BROKER_TYPE.lower() == "paper":

            self.broker = PaperBroker()

        elif BROKER_TYPE.lower() == "delta":

            self.broker = DeltaBroker()

        else:

            raise ValueError(
                f"Unsupported broker: {BROKER_TYPE}"
            )

    def get_balance(self):

        return self.broker.get_balance()

    def get_positions(self):

        if hasattr(self.broker, "get_positions"):
            return self.broker.get_positions()

        return []

    def get_position(self, symbol):

        return self.broker.get_position(symbol)

    def place_order(
        self,
        symbol,
        side,
        quantity,
        price=None,
        order_type="market"
    ):

        if BROKER_TYPE.lower() == "paper":

            return self.broker.place_order(
                symbol=symbol,
                side=side,
                quantity=quantity,
                price=price,
                order_type=order_type
            )

        return self.broker.place_order(
            product_id=symbol,
            side=side,
            size=quantity,
            order_type=order_type,
            limit_price=price
        )

    def close_position(
        self,
        symbol,
        side=None,
        quantity=None,
        exit_price=None
    ):

        if BROKER_TYPE.lower() == "paper":

            return self.broker.close_position(
                symbol=symbol,
                exit_price=exit_price
            )

        return self.broker.close_position(
            product_id=symbol,
            side=side,
            size=quantity
        )

    def cancel_order(self, order_id):

        return self.broker.cancel_order(order_id)

    def health(self):

        if hasattr(self.broker, "health"):

            return self.broker.health()

        return True


broker = BrokerManager()
