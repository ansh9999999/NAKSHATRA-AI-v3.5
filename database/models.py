"""
NAKSHATRA AI
Database Models
"""

from database.database import get_connection


# ---------------------------------------------------
# Save Trade
# ---------------------------------------------------

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


# ---------------------------------------------------
# Get All Trades
# ---------------------------------------------------

def get_all_trades():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT *
    FROM trades
    ORDER BY id DESC
    """)

    rows = cursor.fetchall()

    conn.close()

    return rows


# ---------------------------------------------------
# Get Open Trades
# ---------------------------------------------------

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


# ---------------------------------------------------
# Close Trade
# ---------------------------------------------------

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


# ---------------------------------------------------
# Update Stop Loss
# ---------------------------------------------------

def update_stop_loss(
    trade_id,
    stop_loss
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE trades
    SET stop_loss=?
    WHERE id=?
    """, (
        stop_loss,
        trade_id
    ))

    conn.commit()
    conn.close()


# ---------------------------------------------------
# Update Target
# ---------------------------------------------------

def update_target(
    trade_id,
    target
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE trades
    SET target=?
    WHERE id=?
    """, (
        target,
        trade_id
    ))

    conn.commit()
    conn.close()


# ---------------------------------------------------
# Update Stop Loss + Target
# ---------------------------------------------------

def update_trade_levels(
    trade_id,
    stop_loss,
    target
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE trades
    SET
        stop_loss=?,
        target=?
    WHERE id=?
    """, (
        stop_loss,
        target,
        trade_id
    ))

    conn.commit()
    conn.close()


# ---------------------------------------------------
# Delete Trade
# ---------------------------------------------------

def delete_trade(
    trade_id
):

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    DELETE FROM trades
    WHERE id=?
    """, (
        trade_id,
    ))

    conn.commit()
    conn.close()


# ---------------------------------------------------
# Trade Count
# ---------------------------------------------------

def trade_count():

    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT COUNT(*)
    FROM trades
    """)

    count = cursor.fetchone()[0]

    conn.close()

    return count
