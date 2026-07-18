from contextlib import asynccontextmanager

from fastapi import FastAPI

from scheduler import start_scheduler
from logger import logger

from database.database import initialize_database
from database.models import (
    get_all_trades,
    get_open_trades,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting NAKSHATRA AI v3.5")

    initialize_database()

    start_scheduler()

    yield

    logger.info("Stopping NAKSHATRA AI v3.5")


app = FastAPI(
    title="NAKSHATRA AI v3.5",
    version="3.5",
    lifespan=lifespan
)


@app.get("/")
def home():

    return {
        "project": "NAKSHATRA AI",
        "version": "3.5",
        "status": "Running"
    }


@app.get("/health")
def health():

    return {
        "status": "healthy"
    }


@app.get("/trades")
def trades():

    data = get_all_trades()

    return {
        "count": len(data),
        "trades": data
    }


@app.get("/open-trades")
def open_trades():

    data = get_open_trades()

    return {
        "count": len(data),
        "trades": data
    }


@app.get("/stats")
def stats():

    trades = get_all_trades()

    total = len(trades)

    wins = 0
    losses = 0
    open_trades = 0

    total_pnl = 0

    for trade in trades:

        pnl = trade[8]
        result = trade[13]

        total_pnl += pnl

        if result == "WIN":
            wins += 1

        elif result == "LOSS":
            losses += 1

        elif result == "OPEN":
            open_trades += 1

    win_rate = 0

    if wins + losses > 0:
        win_rate = round(
            wins / (wins + losses) * 100,
            2
        )

    return {

        "total_trades": total,

        "wins": wins,

        "losses": losses,

        "open_trades": open_trades,

        "win_rate": win_rate,

        "net_pnl": total_pnl

    }
