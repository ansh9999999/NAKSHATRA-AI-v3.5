"""
NAKSHATRA AI
Backtest Report Generator
"""

from backtest.metrics import calculate_metrics


def generate_report(df):

    metrics = calculate_metrics(df)

    report = f"""
========================================
        NAKSHATRA AI REPORT
========================================

Total Trades   : {metrics['trades']}

Winning Trades : {metrics['wins']}

Losing Trades  : {metrics['losses']}

Win Rate       : {metrics['win_rate']} %

----------------------------------------

Net Profit     : {metrics['net_profit']}

Gross Profit   : {metrics['gross_profit']}

Gross Loss     : {metrics['gross_loss']}

Profit Factor  : {metrics['profit_factor']}

----------------------------------------

Average Win    : {metrics['average_win']}

Average Loss   : {metrics['average_loss']}

Expectancy     : {metrics['expectancy']}

Max Drawdown   : {metrics['max_drawdown']}

========================================
"""

    return report


def print_report(df):

    print(generate_report(df))
