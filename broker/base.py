from abc import ABC, abstractmethod


class BaseBroker(ABC):

    @abstractmethod
    def get_balance(self):
        pass

    @abstractmethod
    def get_position(self, symbol):
        pass

    @abstractmethod
    def place_order(
        self,
        symbol,
        side,
        quantity,
        order_type="market"
    ):
        pass

    @abstractmethod
    def cancel_order(self, order_id):
        pass
