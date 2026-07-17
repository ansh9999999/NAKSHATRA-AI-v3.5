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

    cursor.execute("""
    SELECT * FROM trades
    ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


def get_open_trades():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM trades
    WHERE result='OPEN'
    ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


def update_trade(
    trade_id,
    exit_price,
    pnl,
    result
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE trades
    SET
        exit_price=?,
        pnl=?,
        result=?
    WHERE id=?
    """, (
        exit_price,
        pnl,
        result,
        trade_id
    ))

    conn.commit()
    conn.close()
