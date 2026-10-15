"""Read-only global crypto market APIs. Kept independent from Delta analysis."""
from datetime import datetime, timezone
import time
import requests
from fastapi import APIRouter, Query

router = APIRouter(prefix="/api/global-market", tags=["Global Market"])
SESSION = requests.Session()
SESSION.headers.update({"User-Agent": "NAKSHATRA-Global-Market/1.0", "Accept": "application/json"})
_CACHE = {}
CACHE_TTL = 8

def _get(url, params=None):
    r = SESSION.get(url, params=params, timeout=6)
    r.raise_for_status()
    return r.json()

def _cached(key, fn):
    now = time.time()
    old = _CACHE.get(key)
    if old and now - old["at"] < CACHE_TTL:
        return old["value"]
    try:
        value = fn()
        value["status"] = "OK"
    except Exception as exc:
        value = {"status": "ERROR", "exchange": key, "error": str(exc)[:180]}
    _CACHE[key] = {"at": now, "value": value}
    return value

def _binance_spot():
    d = _get("https://api.binance.com/api/v3/ticker/24hr", {"symbol":"BTCUSDT"})
    return {"exchange":"Binance Spot","market_type":"spot","symbol":"BTCUSDT","price":float(d["lastPrice"]),
            "change_pct":float(d["priceChangePercent"]),"volume_quote":float(d["quoteVolume"]),
            "high":float(d["highPrice"]),"low":float(d["lowPrice"]),"source":"Binance public API"}

def _coinbase():
    ticker = _get("https://api.exchange.coinbase.com/products/BTC-USD/ticker")
    stats = _get("https://api.exchange.coinbase.com/products/BTC-USD/stats")
    last, opening = float(ticker["price"]), float(stats["open"])
    return {"exchange":"Coinbase Spot","market_type":"spot","symbol":"BTC-USD","price":last,
            "change_pct":((last/opening)-1)*100 if opening else None,
            "volume_quote":float(stats["volume"])*last,"high":float(stats["high"]),
            "low":float(stats["low"]),"source":"Coinbase Exchange public API"}

def _kraken():
    d = _get("https://api.kraken.com/0/public/Ticker", {"pair":"XBTUSD"})
    if d.get("error"): raise RuntimeError(str(d["error"]))
    x = next(iter(d["result"].values()))
    last, opening = float(x["c"][0]), float(x["o"])
    return {"exchange":"Kraken Spot","market_type":"spot","symbol":"XBT/USD","price":last,
            "change_pct":((last/opening)-1)*100 if opening else None,
            "volume_quote":float(x["v"][1])*last,"high":float(x["h"][1]),
            "low":float(x["l"][1]),"source":"Kraken public API"}

def _binance_futures():
    t = _get("https://fapi.binance.com/fapi/v1/ticker/24hr", {"symbol":"BTCUSDT"})
    oi = _get("https://fapi.binance.com/fapi/v1/openInterest", {"symbol":"BTCUSDT"})
    p = _get("https://fapi.binance.com/fapi/v1/premiumIndex", {"symbol":"BTCUSDT"})
    return {"exchange":"Binance USDⓈ-M Futures","market_type":"perpetual","symbol":"BTCUSDT",
            "price":float(t["lastPrice"]),"change_pct":float(t["priceChangePercent"]),
            "volume_quote":float(t["quoteVolume"]),"open_interest":float(oi["openInterest"]),
            "funding_rate":float(p["lastFundingRate"]),"source":"Binance Futures public API"}

def _bybit():
    d = _get("https://api.bybit.com/v5/market/tickers", {"category":"linear","symbol":"BTCUSDT"})
    rows = d.get("result",{}).get("list",[])
    if not rows: raise RuntimeError("Bybit returned no BTCUSDT ticker")
    x=rows[0]
    oi = _get("https://api.bybit.com/v5/market/open-interest", {"category":"linear","symbol":"BTCUSDT","intervalTime":"5min","limit":1})
    f = _get("https://api.bybit.com/v5/market/funding/history", {"category":"linear","symbol":"BTCUSDT","limit":1})
    oirows=oi.get("result",{}).get("list",[])
    frows=f.get("result",{}).get("list",[])
    return {"exchange":"Bybit USDT Perpetual","market_type":"perpetual","symbol":"BTCUSDT",
            "price":float(x["lastPrice"]),"change_pct":float(x["price24hPcnt"])*100,
            "volume_quote":float(x.get("turnover24h",0)),
            "open_interest":float(oirows[0]["openInterest"]) if oirows else None,
            "funding_rate":float(frows[0]["fundingRate"]) if frows else None,
            "source":"Bybit public API"}

PROVIDERS=[("Binance Spot",_binance_spot),("Coinbase Spot",_coinbase),("Kraken Spot",_kraken),
           ("Binance Futures",_binance_futures),("Bybit Futures",_bybit)]

@router.get("/overview")
def overview():
    markets=[_cached(name,fn) for name,fn in PROVIDERS]
    return {"status":"OK","as_of":datetime.now(timezone.utc).isoformat(),"cache_ttl_seconds":CACHE_TTL,
            "valid_sources":sum(1 for m in markets if m.get("price") is not None),
            "total_sources":len(markets),"markets":markets,
            "note":"Spot and perpetual prices are separate markets. API errors are shown per provider."}

@router.get("/orderbook")
def orderbook(exchange: str = Query("binance"), limit: int = Query(20, ge=5, le=100)):
    try:
        if exchange.lower()=="binance":
            d=_get("https://api.binance.com/api/v3/depth",{"symbol":"BTCUSDT","limit":limit})
            return {"status":"OK","exchange":"Binance Spot","symbol":"BTCUSDT","bids":d.get("bids",[]),"asks":d.get("asks",[])}
        if exchange.lower()=="bybit":
            d=_get("https://api.bybit.com/v5/market/orderbook",{"category":"linear","symbol":"BTCUSDT","limit":limit})
            x=d.get("result",{})
            return {"status":"OK","exchange":"Bybit Perpetual","symbol":"BTCUSDT","bids":x.get("b",[]),"asks":x.get("a",[])}
        return {"status":"ERROR","error":"Supported exchanges: binance, bybit"}
    except Exception as exc:
        return {"status":"ERROR","exchange":exchange,"error":str(exc)[:180]}

@router.get("/candles")
def candles(exchange: str = "binance", interval: str = "5m", limit: int = Query(100, ge=20, le=500)):
    allowed={"1m":"1m","5m":"5m","15m":"15m","1h":"1h","4h":"4h","1d":"1d"}
    if interval not in allowed:
        return {"status":"ERROR","error":"Unsupported interval"}
    try:
        if exchange.lower()=="binance":
            raw=_get("https://api.binance.com/api/v3/klines",{"symbol":"BTCUSDT","interval":interval,"limit":limit})
            rows=[{"time":int(x[0]),"open":float(x[1]),"high":float(x[2]),"low":float(x[3]),"close":float(x[4]),"volume":float(x[5])} for x in raw]
        elif exchange.lower()=="bybit":
            iv={"1m":"1","5m":"5","15m":"15","1h":"60","4h":"240","1d":"D"}[interval]
            d=_get("https://api.bybit.com/v5/market/kline",{"category":"linear","symbol":"BTCUSDT","interval":iv,"limit":limit})
            rows=[{"time":int(x[0]),"open":float(x[1]),"high":float(x[2]),"low":float(x[3]),"close":float(x[4]),"volume":float(x[5])} for x in reversed(d.get("result",{}).get("list",[]))]
        else:
            return {"status":"ERROR","error":"Supported candle sources: Binance, Bybit"}
        return {"status":"OK","exchange":exchange,"symbol":"BTCUSDT","interval":interval,"candles":rows}
    except Exception as exc:
        return {"status":"ERROR","exchange":exchange,"error":str(exc)[:180]}
