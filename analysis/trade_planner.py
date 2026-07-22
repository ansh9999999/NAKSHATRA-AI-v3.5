"""
NAKSHATRA AI
Trade Planner
"""

class TradePlanner:

    def __init__(self):
        pass

    # ----------------------------------
    # BUY Trade
    # ----------------------------------

    def plan_buy(
        self,
        entry,
        atr,
        risk_multiple=1.5,
        reward_multiple=2.5
    ):

        stop_loss = round(
            entry - (atr * risk_multiple),
            2
        )

        target1 = round(
            entry + (atr * reward_multiple),
            2
        )

        target2 = round(
            entry + (atr * reward_multiple * 2),
            2
        )

        target3 = round(
            entry + (atr * reward_multiple * 3),
            2
        )

        risk = entry - stop_loss
        reward = target1 - entry

        rr = round(
            reward / risk,
            2
        ) if risk != 0 else 0

        return {

            "entry": round(entry, 2),

            "stop_loss": stop_loss,

            "target1": target1,

            "target2": target2,

            "target3": target3,

            "risk_reward": rr

        }

    # ----------------------------------
    # SELL Trade
    # ----------------------------------

    def plan_sell(
        self,
        entry,
        atr,
        risk_multiple=1.5,
        reward_multiple=2.5
    ):

        stop_loss = round(
            entry + (atr * risk_multiple),
            2
        )

        target1 = round(
            entry - (atr * reward_multiple),
            2
        )

        target2 = round(
            entry - (atr * reward_multiple * 2),
            2
        )

        target3 = round(
            entry - (atr * reward_multiple * 3),
            2
        )

        risk = stop_loss - entry
        reward = entry - target1

        rr = round(
            reward / risk,
            2
        ) if risk != 0 else 0

        return {

            "entry": round(entry, 2),

            "stop_loss": stop_loss,

            "target1": target1,

            "target2": target2,

            "target3": target3,

            "risk_reward": rr

        }

    # ----------------------------------
    # Auto Planner
    # ----------------------------------

    def create_trade(
        self,
        signal,
        entry,
        atr
    ):

        signal = signal.upper()

        if signal in ["BUY", "STRONG BUY"]:

            return self.plan_buy(
                entry,
                atr
            )

        elif signal in ["SELL", "STRONG SELL"]:

            return self.plan_sell(
                entry,
                atr
            )

        return None
