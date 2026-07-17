"""
NAKSHATRA AI
SQLite Database
"""

import sqlite3


DATABASE_NAME = "trades.db"


def get_connection():
    """
    Create SQLite connection.
    """
    return sqlite3.connect(DATABASE_NAME)


def initialize_database():

    conn = get_connection()

    cursor = conn.cursor()

    cursor.execute("""

    CREATE TABLE IF NOT EXISTS trades (

        id INTEGER PRIMARY KEY AUTOINCREMENT,

        trade_time TEXT,

        symbol TEXT,

        signal TEXT,

        entry REAL,

        stop_loss REAL,

        target REAL,

        exit_price REAL,

        pnl REAL,

        score REAL,

        trend TEXT,

        volume TEXT,

        liquidity TEXT,

        result TEXT

    )

    """)

    conn.commit()

    conn.close()
