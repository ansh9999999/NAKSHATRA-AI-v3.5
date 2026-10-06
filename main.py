from market_catalyst import get_market_catalysts
"""
NAKSHATRA AI - Fast dashboard API

Provider routing:
    BTCUSD / ETHUSD -> Delta
    Indian markets -> Kotak Neo

No order placement is performed by this API.
"""

from contextlib import asynccontextmanager
from concurrent.futures import ThreadPoolExecutor
import math
import time
import threading

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from scheduler import start_scheduler
from logger import logger
from database.database import initialize_database
from database.models import get_all_trades, get_open_trades
from history import get_multi_timeframe_history
from analysis.signal import generate_signal
from scanner import market_scan
from market_registry import canonical_symbol, symbols
from kotak_neo import get_quote
from futures_intelligence import get_futures_intelligence, combine_futures_options
from analysis.option_chain_engine import analyze_option_chain
from nse_intelligence import get_nse_intelligence
from position_shift_engine import ingest as ingest_position_shift, analyze as analyze_position_shift
from market_shift_engine import detect_market_shift
from equity_search import search as search_equities, register as register_equity



CACHE_TTL = 180
_TIMEFRAME_TTL = 60
_analysis_cache = {}
_timeframe_cache = {}
_sentiment_cache = {"time": 0.0, "data": None}

# V2.23: /api/live is a heavy aggregate endpoint. Never make the browser
# wait for the complete MTF + options + NSE intelligence pipeline. A single
# background refresh builds the full snapshot while the API returns quickly.
_live_cache = {}
_live_jobs = set()
_live_lock = threading.Lock()
_live_executor = ThreadPoolExecutor(max_workers=2)
_LIVE_CACHE_TTL = 20


def _json_safe(value):
    if value is None or isinstance(value, (str, bool, int, float)):
        if isinstance(value, float) and not math.isfinite(value):
            return None
        return value

    if hasattr(value, "item"):
        try:
            return _json_safe(value.item())
        except Exception:
            pass

    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}

    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]

    if hasattr(value, "isoformat"):
        try:
            return value.isoformat()
        except Exception:
            pass

    return str(value)


def run_analysis(symbol: str, force=False):
    symbol = canonical_symbol(symbol)
    now = time.time()

    if not force:
        cached = _analysis_cache.get(symbol)
        if cached and now - cached["time"] < CACHE_TTL:
            return cached["result"]

    started = time.time()

    try:
        data = get_multi_timeframe_history(symbol, limit=200)
        entry = data.get("5m")

        if entry is None or entry.empty:
            result = {
                "status": "NO DATA",
                "symbol": symbol,
                "message": (
                    "5m candle data unavailable. "
                    "Check the market-data provider and Kotak Neo credentials."
                ),
                "server_time": time.time(),
            }
            _analysis_cache[symbol] = {
                "time": time.time(),
                "result": result,
            }
            return result

        data["symbol"] = symbol
        result = generate_signal(data)
        result = _json_safe(result)

        if isinstance(result, dict):
            result["status"] = "OK"
            result["server_ms"] = round(
                (time.time() - started) * 1000
            )

        _analysis_cache[symbol] = {
            "time": time.time(),
            "result": result,
        }
        return result

    except Exception as exc:
        logger.exception("ANALYSIS ERROR %s", symbol)
        result = {
            "status": "ERROR",
            "symbol": symbol,
            "message": str(exc),
            "server_ms": round(
                (time.time() - started) * 1000
            ),
        }
        _analysis_cache[symbol] = {
            "time": time.time(),
            "result": result,
        }
        return result


def _get_market_quote(symbol):
    """Indian project routing: every supported Indian instrument uses Kotak Neo.
    Delta is intentionally NOT a fallback in this project.
    """
    symbol = canonical_symbol(symbol)
    try:
        from market_registry import get_market
        market = get_market(symbol)
    except Exception:
        market = None
    if not market or market.get("provider") != "kotak_neo":
        logger.warning("INDIAN ROUTING BLOCKED non-Kotak symbol=%s", symbol)
        return None
    try:
        quote = get_quote(symbol)
        if quote:
            quote["provider"] = "kotak_neo"
            quote["source"] = "kotak_neo"
        return quote
    except Exception as exc:
        logger.warning("Kotak quote failed %s: %s", symbol, exc)
        return None


def _build_option_buy_plan(symbol, analysis, oc):
    if symbol not in ("NIFTY50","BANKNIFTY") or not isinstance(analysis,dict): return {"status":"NOT_REQUIRED"}
    side=str(analysis.get("recommendation") or analysis.get("signal") or "WAIT").upper()
    if side not in ("BUY","SELL"): return {"status":"WAIT","action":"NO OPTION BUY","reason":"Main AI signal is WAIT or data quality is insufficient."}
    if not isinstance(oc,dict) or oc.get("status")!="OK" or not oc.get("rows"): return {"status":"WAIT","action":"NO OPTION BUY","reason":"Live option chain unavailable."}
    typ="CALL" if side=="BUY" else "PUT"; suffix="CE" if typ=="CALL" else "PE"; atm=oc.get("atm_strike")
    rows=[r for r in oc.get("rows",[]) if r.get("type")==typ and r.get("strike") is not None]
    if not rows:return {"status":"WAIT","action":"NO OPTION BUY","reason":f"No {typ} contracts available."}
    row=min(rows,key=lambda r:abs(float(r.get("strike") or 0)-float(atm))) if atm is not None else max(rows,key=lambda r:float(r.get("volume") or 0))
    strike=row.get("strike"); contract=f"{symbol} {strike:g} {suffix}" if isinstance(strike,(int,float)) else f"{symbol} {strike} {suffix}"
    return {"status":"READY","action":f"BUY {suffix}","contract":contract,"option_type":typ,"strike":strike,"expiry":oc.get("expiry"),"ltp":row.get("ltp"),"oi":row.get("oi"),"volume":row.get("volume"),"iv":row.get("iv"),"basis":"ATM option after confirmed underlying direction and live option-chain validation."}

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting NAKSHATRA AI provider-aware API")
    initialize_database()
    start_scheduler()
    yield
    logger.info("Stopping NAKSHATRA AI provider-aware API")


app = FastAPI(
    title="NAKSHATRA AI",
    version="INDIA-1.0",
    lifespan=lifespan,
)

templates = Jinja2Templates(directory="templates")
app.mount(
    "/static",
    StaticFiles(directory="static"),
    name="static",
)



def _trend_from_close(df):
    try:
        if df is None or df.empty or "close" not in df.columns or len(df)<12:return {"trend":"UNKNOWN"}
        c=df["close"].astype(float); e9=float(c.ewm(span=9,adjust=False).mean().iloc[-1]); e50=float(c.ewm(span=50,adjust=False).mean().iloc[-1]); px=float(c.iloc[-1])
        trend="UPTREND" if e9>e50 and px>=e50 else "DOWNTREND" if e9<e50 and px<=e50 else "SIDEWAYS"
        return {"trend":trend,"ema9":e9,"ema50":e50,"source":"cached market candles"}
    except Exception:return {"trend":"UNKNOWN"}

def _enrich_timeframes(symbol,analysis):
    if not isinstance(analysis,dict): return analysis
    now=time.time()
    cached=_timeframe_cache.get(symbol)
    if cached and now-cached["time"] < _TIMEFRAME_TTL:
        analysis["derived_timeframes"]=cached["data"]
        return analysis
    try:
        data=get_multi_timeframe_history(symbol,limit=220); d={}
        for tf in ("5m","15m","1h","1d","1w"):
            if tf in data and data[tf] is not None and not data[tf].empty:
                d[tf]=_trend_from_close(data[tf])
        if "1w" not in d and data.get("1d") is not None and len(data["1d"])>=10:
            x=data["1d"].copy().reset_index(drop=True); x["grp"]=x.index//5
            w=x.groupby("grp").agg({"close":"last"}); d["1w"]=_trend_from_close(w)
            d["1w"]["source"]="derived from 1D candles (5 trading sessions)"
        _timeframe_cache[symbol]={"time":now,"data":d}
        analysis["derived_timeframes"]=d
    except Exception as e:
        analysis["derived_timeframes_error"]=str(e)
        if cached: analysis["derived_timeframes"]=cached["data"]
    return analysis


def _public_sentiment():
    """Small cached public Fear & Greed feed; never used as live order-flow."""
    import requests
    now=time.time()
    if _sentiment_cache.get("data") is not None and now-_sentiment_cache.get("time",0) < 300:
        return _sentiment_cache["data"]
    try:
        r=requests.get("https://api.alternative.me/fng/?limit=1&format=json",timeout=4)
        r.raise_for_status()
        item=(r.json().get("data") or [None])[0]
        if not item: raise RuntimeError("Fear & Greed feed returned no data")
        value=int(float(item.get("value")))
        label=str(item.get("value_classification") or "Unknown")
        bias="BULLISH" if value>=55 else "BEARISH" if value<=45 else "NEUTRAL"
        out={"status":"OK","bias":bias,"fear_greed":f"{label} ({value})","score":round((value-50)/50,2),"social_sentiment":"NOT CONNECTED","news_sentiment":"NOT CONNECTED","source":"Alternative.me Fear & Greed","note":"Fear & Greed is a broad sentiment gauge; it is not live institutional order flow."}
        _sentiment_cache.update(time=now,data=out)
        return out
    except Exception as exc:
        return {"status":"NO DATA","bias":"WAIT","fear_greed":"NOT CONNECTED","social_sentiment":"NOT CONNECTED","news_sentiment":"NOT CONNECTED","score":None,"source":"Alternative.me unavailable","note":str(exc)}

@app.get("/", response_class=HTMLResponse)
async def home_page(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"request": request},
    )


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    return templates.TemplateResponse(
        request=request,
        name="dashboard.html",
        context={"request": request},
    )


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.get("/api")
def api():
    return {
        "project": "NAKSHATRA AI",
        "version": "INDIA-1.0",
        "status": "RUNNING",
        "supported_symbols": [x for x in symbols() if x not in ("BTCUSD", "ETHUSD")],
        "provider_routing": {"INDIAN_MARKETS": "kotak_neo"},
        "dashboard_api": "/api/live?symbol=NIFTY50",
    }


@app.get("/api/equity-search")
def api_equity_search(q: str = "", limit: int = 12):
    try:
        return _json_safe(search_equities(q, limit=limit))
    except Exception as exc:
        logger.exception("EQUITY SEARCH ERROR")
        return {"status":"ERROR","query":q,"count":0,"results":[],"error":str(exc)}


@app.get("/api/equity-register")
def api_equity_register(symbol: str = ""):
    try:
        row = register_equity(symbol)
        if not row:
            return {"status":"NOT_FOUND","symbol":symbol}
        return _json_safe({"status":"OK", **row})
    except Exception as exc:
        logger.exception("EQUITY REGISTER ERROR")
        return {"status":"ERROR","symbol":symbol,"error":str(exc)}


def _build_live_payload(symbol: str = "BTCUSD", force: bool = False):
    symbol = canonical_symbol(symbol)
    analysis = run_analysis(symbol, force=force)
    analysis = _enrich_timeframes(symbol, analysis)
    ticker = _get_market_quote(symbol)
    market_shift = detect_market_shift(symbol)

    # v2.10 data-quality gate for index decisions. A strong directional call
    # is not allowed when the option chain or positioning sentiment is absent.
    quality = {"status": "NOT_REQUIRED"}
    oc = None
    if symbol in ("NIFTY50", "BANKNIFTY") and isinstance(analysis, dict):
        try:
            spot = (ticker or {}).get("ltp") or (ticker or {}).get("price") or (ticker or {}).get("close")
            oc = analyze_option_chain(symbol, spot_price=spot)
            ingest_position_shift(symbol, spot, oc)
            intel = get_nse_intelligence(symbol)
            sent = (intel or {}).get("sentiment", {})
            public_sent = _public_sentiment()
            merged_sent = dict(public_sent or {})
            if isinstance(sent, dict):
                merged_sent.update({k:v for k,v in sent.items() if v not in (None, "", "NOT CONNECTED")})
            analysis["option_chain"] = oc
            analysis["nse_intelligence"] = intel
            analysis["sentiment"] = merged_sent
            option_ok = oc.get("status") == "OK" and oc.get("row_count", 0) > 0
            sentiment_ok = sent.get("status") == "OK"
            quality = {"status": "OK" if option_ok and sentiment_ok else "DATA RISK", "option_chain": option_ok, "sentiment": sentiment_ok}
            if not (option_ok and sentiment_ok):
                analysis["recommendation"] = "WAIT"
                analysis["signal"] = "WAIT"
                analysis["data_quality"] = quality
                analysis["data_quality_reason"] = "Required NSE option-chain/positioning data unavailable; directional signal suppressed."
                if analysis.get("overall_confidence") is not None:
                    analysis["overall_confidence"] = min(float(analysis.get("overall_confidence") or 0), 49.0)
        except Exception as exc:
            quality = {"status": "DATA RISK", "error": str(exc)}
            analysis["recommendation"] = "WAIT"
            analysis["signal"] = "WAIT"
            analysis["data_quality"] = quality

    shift = analyze_position_shift(symbol) if symbol in ("NIFTY50","BANKNIFTY") else {"status":"NOT_REQUIRED"}
    futures_payload = {"futures":{"status":"NOT_REQUIRED"},"combined":{"status":"NOT_REQUIRED"}}
    if symbol in ("NIFTY50","BANKNIFTY","NIFTYIT"):
        try:
            fut = get_futures_intelligence(symbol, (ticker or {}).get("ltp") or (ticker or {}).get("price") or (ticker or {}).get("close"))
            futures_payload = {"futures": fut, "combined": combine_futures_options(fut, oc or {"status":"NO DATA"})}
        except Exception as exc:
            futures_payload = {"futures":{"status":"ERROR","reason":str(exc)},"combined":{"status":"DATA RISK","view":"WAIT","action":"WAIT"}}
    if isinstance(analysis, dict):
        analysis["futures_intelligence"] = futures_payload

    option_trade = _build_option_buy_plan(symbol, analysis, oc)
    if option_trade.get("status") == "READY" and shift.get("status") == "OK":
        needed = "BULLISH" if option_trade.get("option_type") == "CALL" else "BEARISH"
        if shift.get("bias") not in (needed, "NEUTRAL"):
            option_trade = {"status":"WAIT","action":"NO OPTION BUY","reason":"Live position shift conflicts with the directional signal.","position_shift":shift}
        else:
            option_trade["position_shift"] = shift
    if isinstance(analysis, dict):
        analysis["option_trade"] = option_trade
        analysis["market_shift"] = market_shift

    return _json_safe({
        "status": (
            analysis.get("status", "UNKNOWN")
            if isinstance(analysis, dict)
            else "UNKNOWN"
        ),
        "symbol": symbol,
        "ticker": ticker,
        "analysis": analysis,
        "server_time": time.time(),
        "data_quality": quality,
        "option_trade": option_trade,
        "position_shift": shift,
        "market_shift": market_shift,
        "futures_intelligence": futures_payload,
    })


def _refresh_live_background(symbol: str):
    try:
        payload = _build_live_payload(symbol, force=False)
        with _live_lock:
            _live_cache[symbol] = {"time": time.time(), "payload": payload}
    except Exception as exc:
        logger.exception("LIVE BACKGROUND REFRESH ERROR %s", symbol)
        with _live_lock:
            _live_cache[symbol] = {
                "time": time.time(),
                "payload": {
                    "status": "ERROR",
                    "symbol": symbol,
                    "ticker": None,
                    "analysis": {"status": "ERROR", "message": str(exc)},
                    "data_quality": {"status": "DATA RISK", "reason": str(exc)},
                    "server_time": time.time(),
                },
            }
    finally:
        with _live_lock:
            _live_jobs.discard(symbol)


@app.get("/api/live")
def api_live(symbol: str = "NIFTY50", force: bool = False):
    """Fast Indian live endpoint: fetch Kotak LTP first, then refresh analysis in background."""
    symbol = canonical_symbol(symbol)
    now = time.time()
    if symbol not in symbols() or symbol in ("BTCUSD", "ETHUSD"):
        return {"status":"NOT_AVAILABLE","symbol":symbol,"message":"This is the Indian Market project. Use an Indian-market symbol."}
    ticker = _get_market_quote(symbol)
    with _live_lock:
        cached = _live_cache.get(symbol)
        if cached and now-cached["time"] < _LIVE_CACHE_TTL and not force:
            payload = cached["payload"]
            if ticker:
                payload = dict(payload); payload["ticker"] = ticker; payload["server_time"] = now
            return payload
        if symbol not in _live_jobs:
            _live_jobs.add(symbol)
            _live_executor.submit(_refresh_live_background, symbol)
    if ticker:
        return {
            "status":"OK", "symbol":symbol, "ticker":ticker,
            "analysis":{"status":"LOADING","symbol":symbol,"message":"Live Kotak Neo price received; AI snapshot is updating."},
            "data_quality":{"status":"LIVE","provider":"kotak_neo"},
            "server_time":now,
        }
    return {
        "status":"NO DATA", "symbol":symbol, "ticker":None,
        "analysis":{"status":"NO DATA","symbol":symbol,"message":"Kotak Neo live quote unavailable. Check credentials/session or Kotak API response."},
        "data_quality":{"status":"DATA RISK","provider":"kotak_neo"},
        "server_time":now,
    }


@app.get("/api/options")
def api_options(symbol: str = "NIFTY50"):
    symbol = canonical_symbol(symbol)
    if str(symbol).startswith("EQ_"):
        return {"status":"NOT_AVAILABLE","signal":"NEUTRAL","confidence":0,"reason":"Cash equity selected. Option-chain analysis is available only for supported F&O instruments.","rows":[]}
    ticker = _get_market_quote(symbol) or {}
    spot = ticker.get("ltp") or ticker.get("price") or ticker.get("close")
    try:
        payload = analyze_option_chain(symbol, spot_price=spot)
        ingest_position_shift(symbol, spot, payload)
        rows=payload.get("rows") or []
        if rows:
            # Engine rows are one contract per row (type=CALL/PUT). Do not expect paired CE/PE fields.
            calls=[r for r in rows if str(r.get("type") or "").upper()=="CALL"]
            puts=[r for r in rows if str(r.get("type") or "").upper()=="PUT"]
            co=sum(float(r.get("oi") or 0) for r in calls); po=sum(float(r.get("oi") or 0) for r in puts)
            cv=sum(float(r.get("volume") or 0) for r in calls); pv=sum(float(r.get("volume") or 0) for r in puts)
            payload.update(pcr_oi_calc=round(po/co,4) if co else payload.get("pcr"),pcr_volume_calc=round(pv/cv,4) if cv else payload.get("volume_pcr"),chain_total_oi=co+po,chain_total_volume=cv+pv,call_volume_total=cv,put_volume_total=pv)
        logger.info("OPTION CHAIN %s status=%s source=%s expiry=%s rows=%s", symbol, payload.get("status"), payload.get("source"), payload.get("expiry"), payload.get("row_count",0))
        return _json_safe(payload)
    except Exception as exc:
        logger.exception("OPTION API ERROR %s", symbol)
        return {"status
