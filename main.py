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

try:
    from delta import get_ticker as delta_get_ticker
except Exception:
    delta_get_ticker = None


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
_live_executor = ThreadPoolExecutor(max_workers=1)
_LIVE_CACHE_TTL = 60
_MAX_ANALYSIS_CACHE = 24
_MAX_TIMEFRAME_CACHE = 24
_MAX_LIVE_CACHE = 24

def _cache_put(cache, key, value, max_items):
    cache[key] = value
    while len(cache) > max_items:
        try:
            oldest = min(cache.items(), key=lambda kv: kv[1].get("time", 0) if isinstance(kv[1], dict) else 0)[0]
        except Exception:
            oldest = next(iter(cache))
        if oldest == key and len(cache) > 1:
            oldest = next(iter(k for k in cache if k != key))
        cache.pop(oldest, None)



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
            _cache_put(_analysis_cache, symbol, {"time": time.time(), "result": result}, _MAX_ANALYSIS_CACHE)
            return result

        data["symbol"] = symbol
        result = generate_signal(data)
        result = _json_safe(result)

        if isinstance(result, dict):
            result["status"] = "OK"
            result["server_ms"] = round(
                (time.time() - started) * 1000
            )

        _cache_put(_analysis_cache, symbol, {"time": time.time(), "result": result}, _MAX_ANALYSIS_CACHE)
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
        _cache_put(_analysis_cache, symbol, {"time": time.time(), "result": result}, _MAX_ANALYSIS_CACHE)
        return result


def _get_market_quote(symbol):
    symbol = canonical_symbol(symbol)
    market = None

    try:
        from market_registry import get_market
        market = get_market(symbol)
    except Exception:
        pass

    if market and market.get("provider") == "kotak_neo":
        try:
            return get_quote(symbol)
        except Exception as exc:
            logger.warning(
                "Kotak quote failed %s: %s",
                symbol,
                exc,
            )
            return None

    if delta_get_ticker is not None:
        try:
            return delta_get_ticker(symbol)
        except Exception as exc:
            logger.warning(
                "Delta quote failed %s: %s",
                symbol,
                exc,
            )

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
    version="5.22",
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
        _cache_put(_timeframe_cache, symbol, {"time":now,"data":d}, _MAX_TIMEFRAME_CACHE)
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
        "version": "5.22",
        "status": "RUNNING",
        "supported_symbols": symbols(),
        "provider_routing": {
            "BTCUSD": "delta",
            "ETHUSD": "delta",
            "INDIAN_MARKETS": "kotak_neo",
        },
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

@app.get("/api/quote")
def api_quote(symbol: str = "NIFTY50"):
    """Fast quote-only endpoint. Never runs historical/AI analysis."""
    raw = str(symbol or "NIFTY50").strip().upper()
    try:
        canonical = canonical_symbol(raw)
        quote = _get_market_quote(canonical)
        if quote:
            return _json_safe({"status":"OK", "symbol":canonical, "ticker":quote, "server_time":time.time()})
        return {"status":"NO DATA", "symbol":canonical, "ticker":None, "server_time":time.time()}
    except Exception as exc:
        logger.warning("FAST QUOTE ERROR %s: %s", raw, exc)
        return {"status":"ERROR", "symbol":raw, "ticker":None, "error":str(exc), "server_time":time.time()}


@app.get("/api/futures")
def api_futures(symbol: str = "NIFTY50"):
    symbol = canonical_symbol(symbol)
    if str(symbol).startswith("EQ_"):
        return {"futures":{"status":"NOT_AVAILABLE","symbol":symbol,"reason":"Cash equity selected; futures contract not selected."},"combined":{"status":"NOT_REQUIRED","view":"CASH EQUITY","action":"TECHNICAL ONLY"}}
    if symbol not in ("NIFTY50", "BANKNIFTY", "NIFTYIT"):
        return {"futures":{"status":"NOT_REQUIRED","symbol":symbol,"reason":"Index futures intelligence is enabled for NIFTY/BANKNIFTY/NIFTY IT."},"combined":{"status":"NOT_REQUIRED","view":"NOT REQUIRED","action":"WAIT"}}
    try:
        ticker = _get_market_quote(symbol) or {}
        spot = ticker.get("ltp") or ticker.get("price") or ticker.get("close")
        fut = get_futures_intelligence(symbol, spot)
        # Options are deliberately read from the existing cache/engine here; this
        # endpoint must not invoke the full AI analysis pipeline.
        opt = {"status":"NO DATA","signal":"NEUTRAL"}
        if symbol in ("NIFTY50", "BANKNIFTY"):
            opt = analyze_option_chain(symbol, spot_price=spot)
        combined = combine_futures_options(fut, opt)
        return _json_safe({"status":"OK" if fut.get("status") in ("OK","NO_DATA","NOT_REQUIRED") else fut.get("status"),"symbol":symbol,"futures":fut,"combined":combined})
    except Exception as exc:
        logger.exception("FUTURES API ERROR %s", symbol)
        return {"status":"ERROR","symbol":symbol,"futures":{"status":"ERROR","reason":str(exc)},"combined":{"status":"DATA RISK","view":"WAIT","action":"WAIT"}}


@app.get("/api/scanner")
def api_scanner():
    """Lightweight live scanner based on fast quotes only.

    It intentionally does not call market_scan()/generate_signal() for every
    symbol, because that would multiply historical/option requests and can
    push a 512 MB Render instance into OOM.
    """
    now = time.time()
    key = "__scanner__"
    cached = _live_cache.get(key)
    if cached and now - cached.get("time", 0) < 15:
        return cached["payload"]

    scan_symbols = ["NIFTY50", "BANKNIFTY", "SENSEX", "NIFTYIT", "GOLD", "SILVER", "CRUDEOIL"]
    rows = []
    for sym in scan_symbols:
        try:
            q = _get_market_quote(sym) or {}
            px = q.get("ltp") or q.get("price") or q.get("close")
            ch = q.get("percent_change")
            rows.append({"symbol":sym,"price":px,"change_pct":ch,"status":"OK" if px is not None else "NO DATA"})
        except Exception as exc:
            rows.append({"symbol":sym,"price":None,"change_pct":None,"status":"ERROR","error":str(exc)})
    payload = {"status":"OK","rows":rows,"server_time":now,"note":"Fast quote scanner; AI analysis loads separately for the selected market."}
    _cache_put(_live_cache, key, {"time":now,"payload":payload}, _MAX_LIVE_CACHE)
    return _json_safe(payload)


@app.get("/api/nse-intelligence")
def api_nse_intelligence(symbol: str = "NIFTY50"):
    try:
        return _json_safe(get_nse_intelligence(canonical_symbol(symbol)))
    except Exception as exc:
        logger.exception("NSE INTELLIGENCE ERROR")
        return {"status":"ERROR","symbol":symbol,"error":str(exc)}


@app.get("/api/position-shift")
def api_position_shift(symbol: str = "NIFTY50"):
    try:
        canonical = canonical_symbol(symbol)
        if str(canonical).startswith("EQ_") or canonical not in ("NIFTY50","BANKNIFTY"):
            return {"status":"NOT_REQUIRED","symbol":canonical,"bias":"WAIT","strength":0,"action":"WAIT","note":"Live option position shift is enabled for NIFTY/BANKNIFTY."}
        return _json_safe(analyze_position_shift(canonical))
    except Exception as exc:
        logger.exception("POSITION SHIFT ERROR")
        return {"status":"ERROR","symbol":symbol,"bias":"WAIT","strength":0,"error":str(exc)}


@app.get("/api/market-shift")
def api_market_shift(symbol: str = "NIFTY50"):
    try:
        canonical = canonical_symbol(symbol)
        return _json_safe(detect_market_shift(canonical))
    except Exception as exc:
        logger.exception("MARKET SHIFT ERROR")
        return {"status":"ERROR","symbol":symbol,"bias":"WAIT","strength":0,"error":str(exc)}


@app.get("/api/catalysts")
def api_catalysts(symbol: str = "NIFTY50"):
    try:
        return _json_safe(get_market_catalysts(canonical_symbol(symbol)))
    except Exception as exc:
        logger.exception("CATALYSTS ERROR")
        return {"status":"ERROR","symbol":symbol,"items":[],"error":str(exc)}


def _build_live_payload(symbol: str = "BTCUSD", force: bool = False):
    symbol = canonical_symbol(symbol)
    analysis = run_analysis(symbol, force=force)
    analysis = _enrich_timeframes(symbol, analysis)
    ticker = _get_market_quote(symbol)

    # Keep expensive shift/position modules out of the fast equity path.
    if str(symbol).startswith("EQ_"):
        market_shift = {"status":"NOT_REQUIRED","symbol":symbol,"bias":"WAIT","strength":0,"phase":"CASH EQUITY","action":"TECHNICAL ONLY","note":"Market-shift/options positioning is reserved for index derivatives."}
    else:
        market_shift = detect_market_shift(symbol)

    quality = {"status":"NOT_REQUIRED"}
    oc = None
    if isinstance(analysis, dict):
        # generate_signal() already calculated the option chain. Reuse it instead
        # of hitting NSE/Kotak a second time in the same live refresh.
        existing_oc = analysis.get("option_chain")
        if isinstance(existing_oc, dict):
            oc = existing_oc

    if symbol in ("NIFTY50", "BANKNIFTY") and isinstance(analysis, dict):
        try:
            spot = (ticker or {}).get("ltp") or (ticker or {}).get("price") or (ticker or {}).get("close")
            if not isinstance(oc, dict) or oc.get("status") != "OK":
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
    elif isinstance(analysis, dict):
        # Public sentiment is useful for cash equities too; do not leave the UI
        # blank simply because there is no option chain.
        analysis["sentiment"] = _public_sentiment()

    shift = analyze_position_shift(symbol) if symbol in ("NIFTY50","BANKNIFTY") else {"status":"NOT_REQUIRED","symbol":symbol,"bias":"WAIT","strength":0,"action":"WAIT"}
    futures_payload = {"futures":{"status":"NOT_REQUIRED","symbol":symbol},"combined":{"status":"NOT_REQUIRED","view":"NOT REQUIRED","action":"WAIT"}}
    if symbol in ("NIFTY50","BANKNIFTY","NIFTYIT"):
        try:
            spot = (ticker or {}).get("ltp") or (ticker or {}).get("price") or (ticker or {}).get("close")
            fut = get_futures_intelligence(symbol, spot)
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
        "status": analysis.get("status", "UNKNOWN") if isinstance(analysis, dict) else "UNKNOWN",
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
            _cache_put(_live_cache, symbol, {"time": time.time(), "payload": payload}, _MAX_LIVE_CACHE)
    except Exception as exc:
        logger.exception("LIVE BACKGROUND REFRESH ERROR %s", symbol)
        with _live_lock:
            _cache_put(_live_cache, symbol, {"time": time.time(), "payload": {"status":"ERROR","symbol":symbol,"ticker":None,"analysis":{"status":"ERROR","message":str(exc)},"data_quality":{"status":"DATA RISK","reason":str(exc)},"server_time":time.time()}}, _MAX_LIVE_CACHE)
    finally:
        with _live_lock:
            _live_jobs.discard(symbol)


@app.get("/api/live")
def api_live(symbol: str = "BTCUSD", force: bool = False):
    symbol = canonical_symbol(symbol)
    now = time.time()
    with _live_lock:
        cached = _live_cache.get(symbol)
        if cached and now - cached["time"] < _LIVE_CACHE_TTL and not force:
            return cached["payload"]
        if symbol not in _live_jobs:
            _live_jobs.add(symbol)
            _live_executor.submit(_refresh_live_background, symbol)
    return {"status":"LOADING","symbol":symbol,"ticker":None,"analysis":{"status":"LOADING","symbol":symbol,"message":"Building live market snapshot…"},"data_quality":{"status":"LOADING","reason":"Live snapshot is being refreshed."},"server_time":now}


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
            calls=[r for r in rows if str(r.get("type") or "").upper()=="CALL"]
            puts=[r for r in rows if str(r.get("type") or "").upper()=="PUT"]
            co=sum(float(r.get("oi") or 0) for r in calls); po=sum(float(r.get("oi") or 0) for r in puts)
            cv=sum(float(r.get("volume") or 0) for r in calls); pv=sum(float(r.get("volume") or 0) for r in puts)
            payload.update(pcr_oi_calc=round(po/co,4) if co else payload.get("pcr"),pcr_volume_calc=round(pv/cv,4) if cv else payload.get("volume_pcr"),chain_total_oi=co+po,chain_total_volume=cv+pv,call_volume_total=cv,put_volume_total=pv)
        logger.info("OPTION CHAIN %s status=%s source=%s expiry=%s rows=%s", symbol, payload.get("status"), payload.get("source"), payload.get("expiry"), payload.get("row_count",0))
        return _json_safe(payload)
    except Exception as exc:
        logger.exception("OPTION API ERROR %s", symbol)
        return {"status":"ERROR","signal":"NEUTRAL","confidence":0,"reason":str(exc),"source":"exception","rows":[]}
