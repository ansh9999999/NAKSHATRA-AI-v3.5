"""
NAKSHATRA AI
Paper Trading Broker
"""

import uuid


class PaperBroker:

    def __init__(self, starting_balance=100000):

        self.balance = float(starting_balance)

        self.positions = {}

        self.orders = {}

    def get_balance(self):

        return {
            "balance": round(self.balance, 2)
        }

    def get_position(self, symbol):

        return self.positions.get(symbol)

    def place_order(
        self,
        symbol,
        side,
        quantity,
        price,
        order_type="MARKET"
    ):

        order_id = str(uuid.uuid4())[:8]

        order = {
            "order_id": order_id,
            "symbol": symbol,
            "side": side,
            "quantity": quantity,
            "price": price,
            "type": order_type,
            "status": "FILLED"
        }

        self.orders[order_id] = order

        self.positions[symbol] = order

        return order

    def close_position(
        self,
        symbol,
        exit_price
    ):

        if symbol not in self.positions:
            return None

        position = self.positions.pop(symbol)

        entry = float(position["price"])

        qty = float(position["quantity"])

        side = position["side"]

        if side.upper() == "BUY":
            pnl = (exit_price - entry) * qty
        else:
            pnl = (entry - exit_price) * qty

        self.balance += pnl

        return {
            "symbol": symbol,
            "entry": entry,
            "exit": exit_price,
            "quantity": qty,
            "pnl": round(pnl, 2),
            "balance": round(self.balance, 2)
        }

    def cancel_order(self, order_id):

        if order_id in self.orders:
            self.orders[order_id]["status"] = "CANCELLED"
            return True

        return False

    def list_positions(self):

        return list(self.positions.values())

    def list_orders(self):

        return list(self.orders.values())
