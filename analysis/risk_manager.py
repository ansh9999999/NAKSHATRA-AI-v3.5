"""
NAKSHATRA AI
Risk Management Engine
"""

class RiskManager:

    def __init__(
        self,
        capital=100000,
        risk_per_trade=1.0,
        max_daily_loss=3.0,
        max_open_positions=5,
        max_portfolio_exposure=50.0
    ):

        self.capital = capital

        self.risk_per_trade = risk_per_trade

        self.max_daily_loss = max_daily_loss

        self.max_open_positions = max_open_positions

        self.max_portfolio_exposure = max_portfolio_exposure

        self.daily_loss = 0

    # ------------------------------------
    # Position Size
    # ------------------------------------

    def calculate_quantity(
        self,
        entry,
        stop_loss
    ):

        risk_amount = (
            self.capital *
            self.risk_per_trade /
            100
        )

        risk_per_unit = abs(
            entry - stop_loss
        )

        if risk_per_unit == 0:
            return 0

        quantity = risk_amount / risk_per_unit

        return int(quantity)

    # ------------------------------------
    # Portfolio Exposure
    # ------------------------------------

    def exposure_percent(
        self,
        portfolio
    ):

        invested = 0

        for position in portfolio.positions:

            invested += position["investment"]

        return round(
            invested /
            self.capital *
            100,
            2
        )

    # ------------------------------------
    # Can Open Trade?
    # ------------------------------------

    def can_open_trade(
        self,
        portfolio,
        entry,
        stop_loss,
        quantity
    ):

        if len(portfolio.positions) >= self.max_open_positions:

            return False, "Maximum Open Positions"

        exposure = self.exposure_percent(
            portfolio
        )

        investment = entry * quantity

        future_exposure = exposure + (
            investment /
            self.capital *
            100
        )

        if future_exposure > self.max_portfolio_exposure:

            return False, "Portfolio Exposure Limit"

        if self.daily_loss >= self.max_daily_loss:

            return False, "Daily Loss Limit Reached"

        if quantity <= 0:

            return False, "Invalid Quantity"

        return True, "Approved"

    # ------------------------------------
    # Update Daily Loss
    # ------------------------------------

    def update_daily_loss(
        self,
        pnl
    ):

        if pnl < 0:

            loss_percent = abs(
                pnl /
                self.capital *
                100
            )

            self.daily_loss += loss_percent

    # ------------------------------------
    # Reset Day
    # ------------------------------------

    def reset_daily_loss(self):

        self.daily_loss = 0

    # ------------------------------------
    # Risk Reward
    # ------------------------------------

    def risk_reward(
        self,
        entry,
        stop_loss,
        target
    ):

        risk = abs(
            entry -
            stop_loss
        )

        reward = abs(
            target -
            entry
        )

        if risk == 0:

            return 0

        return round(
            reward / risk,
            2
        )

    # ------------------------------------
    # Validate Trade
    # ------------------------------------

    def validate_trade(
        self,
        confidence,
        risk_reward
    ):

        if confidence < 70:

            return False, "Low Confidence"

        if risk_reward < 1.5:

            return False, "Poor Risk Reward"

        return True, "Trade Accepted"

    # ------------------------------------
    # Summary
    # ------------------------------------

    def summary(self):

        return {

            "capital": self.capital,

            "risk_per_trade":
                self.risk_per_trade,

            "daily_loss":
                round(self.daily_loss, 2),

            "max_daily_loss":
                self.max_daily_loss,

            "max_open_positions":
                self.max_open_positions,

            "max_portfolio_exposure":
                self.max_portfolio_exposure

  }
