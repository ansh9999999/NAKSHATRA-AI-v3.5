"""
NAKSHATRA AI
Database Models
"""

from database.database import get_connection


def save_trade(trade):

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""

    INSERT INTO trades(

        trade_time,

        symbol,

        signal,

        entry,

        stop_loss,

        target,

        exit_price,

        pnl,

        score,

        trend,

        volume,

        liquidity,

        result

    )

    VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)

    """, (

        trade["trade_time"],

        trade["symbol"],

        trade["signal"],

        trade["entry"],

        trade["stop_loss"],

        trade["target"],

        trade["exit_price"],

        trade["pnl"],

        trade["score"],

        trade["trend"],

        trade["volume"],

        trade["liquidity"],

        trade["result"]

    ))

    conn.commit()

    conn.close()


def get_all_trades():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("SELECT * FROM trades")

    rows = cursor.fetchall()

    conn.close()

    return rows
