"""
NAKSHATRA AI
Professional Backtest Report Generator
"""

from backtest.metrics import calculate_metrics


def generate_report(df):

    metrics = calculate_metrics(df)

    avg_rr = round(df["risk_reward"].mean(), 2) if not df.empty else 0
    avg_conf = round(df["confidence"].mean(), 2) if not df.empty else 0

    a_plus = len(df[df["grade"] == "A+"]) if not df.empty else 0
    a = len(df[df["grade"] == "A"]) if not df.empty else 0
    b = len(df[df["grade"] == "B"]) if not df.empty else 0
    c = len(df[df["grade"] == "C"]) if not df.empty else 0
    reject = len(df[df["grade"] == "REJECT"]) if not df.empty else 0

    best_trade = round(df["pnl"].max(), 2) if not df.empty else 0
    worst_trade = round(df["pnl"].min(), 2) if not df.empty else 0

    report = f"""

====================================================
              NAKSHATRA AI REPORT
====================================================

TRADING PERFORMANCE

Total Trades          : {metrics['trades']}
Winning Trades        : {metrics['wins']}
Losing Trades         : {metrics['losses']}
Win Rate              : {metrics['win_rate']} %

----------------------------------------------------

PROFITABILITY

Net Profit            : {metrics['net_profit']}
Gross Profit          : {metrics['gross_profit']}
Gross Loss            : {metrics['gross_loss']}
Profit Factor         : {metrics['profit_factor']}

----------------------------------------------------

RISK ANALYSIS

Average Win           : {metrics['average_win']}
Average Loss          : {metrics['average_loss']}
Expectancy            : {metrics['expectancy']}
Maximum Drawdown      : {metrics['max_drawdown']}

Average Risk Reward   : {avg_rr}
Average Confidence    : {avg_conf} %

----------------------------------------------------

TRADE QUALITY

A+ Trades             : {a_plus}
A Trades              : {a}
B Trades              : {b}
C Trades              : {c}
Rejected Trades       : {reject}

----------------------------------------------------

BEST TRADE            : {best_trade}
WORST TRADE           : {worst_trade}

====================================================
        NAKSHATRA AI BACKTEST COMPLETE
====================================================

"""

    return report


def print_report(df):
    print(generate_report(df))
