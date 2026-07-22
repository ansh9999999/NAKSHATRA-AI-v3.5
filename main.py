from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from scheduler import start_scheduler
from logger import logger

from database.database import initialize_database
from database.models import (
    get_all_trades,
    get_open_trades,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting NAKSHATRA AI v4.0")

    initialize_database()

    start_scheduler()

    yield

    logger.info("Stopping NAKSHATRA AI v4.0")


app = FastAPI(
    title="NAKSHATRA AI v4.0",
    version="4.0",
    lifespan=lifespan
)


templates = Jinja2Templates(directory="templates")

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
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
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from scheduler import start_scheduler
from logger import logger

from database.database import initialize_database
from database.models import (
    get_all_trades,
    get_open_trades,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting NAKSHATRA AI v4.0")

    initialize_database()

    start_scheduler()

    yield

    logger.info("Stopping NAKSHATRA AI v4.0")


app = FastAPI(
    title="NAKSHATRA AI v4.0",
    version="4.0",
    lifespan=lifespan
)


templates = Jinja2Templates(directory="templates")

app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static"
)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        "dashboard.html",
        {"request": request}
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


@app.get("/api/history")
def api_history():
    trades = get_all_trades()
    history = []
    for t in trades[-100:]:
        history.append({
            "symbol": t[1],
            "side": t[2],
            "entry": t[5],
            "exit": t[6],
            "pnl": t[8],
            "status": t[13]
        })
    return history


@app.get("/api/scanner")
def api_scanner():
    return [
        {
            "symbol":"NIFTY",
            "signal":"Waiting",
            "strength":"-"
        }
    ]
