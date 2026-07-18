"""
NAKSHATRA AI
Broker Manager
"""

from broker.paper import PaperBroker

# Future:
# from broker.delta import DeltaBroker


BROKER_TYPE = "paper"


class BrokerManager:

    def __init__(self):

        if BROKER_TYPE == "paper":

            self.broker = PaperBroker()

        # elif BROKER_TYPE == "delta":
        #     self.broker = DeltaBroker()

        else:
            raise ValueError("Invalid Broker Type")

    def get_balance(self):

        return self.broker.get_balance()

    def get_position(self, symbol):

        return self.broker.get_position(symbol)

    def place_order(
        self,
        symbol,
        side,
        quantity,
        price,
        order_type="MARKET"
    ):

        return self.broker.place_order(
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            order_type=order_type
        )

    def close_position(
        self,
        symbol,
        exit_price
    ):

        return self.broker.close_position(
            symbol,
            exit_price
        )

    def cancel_order(self, order_id):

        return self.broker.cancel_order(order_id)

    def list_positions(self):

        return self.broker.list_positions()

    def list_orders(self):

        return self.broker.list_orders()


broker = BrokerManager()
