"""NAKSHATRA AI v4.0 - Delta historical candle adapter."""
import time
import requests
import pandas as pd
from config import DELTA_BASE_URL
from logger import logger

BASE_URL = DELTA_BASE_URL.rstrip("/")
if not BASE_URL.endswith("/v2"):
    BASE_URL += "/v2"
ENDPOINT = f"{BASE_URL}/history/candles"
TIMEOUT = 20
RETRIES = 3
RESOLUTION_SECONDS = {"1m":60,"3m":180,"5m":300,"15m":900,"30m":1800,"1h":3600,"2h":7200,"4h":14400,"6h":21600,"12h":43200,"1d":86400,"1w":604800}

def _empty():
    df=pd.DataFrame(columns=["open","high","low","close","volume"]); df.index=pd.DatetimeIndex([],name="timestamp"); return df

def _canonical_symbol(symbol):
    s=str(symbol or "").strip().upper()
    if s in ("", "UNDEFINED", "NULL", "NONE", "NAN"):
        return "BTCUSD"
    aliases={"BTC":"BTCUSD","BTC/USDT":"BTCUSD","BTC-USDT":"BTCUSD","ETH":"ETHUSD","ETH/USDT":"ETHUSD","ETH-USDT":"ETHUSD"}
    return aliases.get(s,s)

def _fetch_history(symbol,resolution="5m",limit=200):
    symbol=_canonical_symbol(symbol); resolution=str(resolution).lower().strip(); seconds=RESOLUTION_SECONDS.get(resolution,300)
    if resolution not in RESOLUTION_SECONDS: resolution="5m"
    try: limit=max(10,min(int(limit),2000))
    except Exception: limit=200
    end=int(time.time()); end-=end%seconds; start=end-limit*seconds
    params={"symbol":symbol,"resolution":resolution,"start":start,"end":end}
    for attempt in range(1,RETRIES+1):
        try:
            r=requests.get(ENDPOINT,params=params,timeout=TIMEOUT,headers={"Accept":"application/json","User-Agent":"NAKSHATRA-AI/4.0"}); r.raise_for_status(); payload=r.json(); rows=payload.get("result",[]) if isinstance(payload,dict) else []
            if not isinstance(rows,list) or not rows: logger.warning("No candle data for %s %s",symbol,resolution); continue
            df=pd.DataFrame(rows)
            time_col="time" if "time" in df.columns else ("timestamp" if "timestamp" in df.columns else None)
            if time_col is None: logger.warning("Timestamp missing for %s %s",symbol,resolution); continue
            df["timestamp"]=pd.to_numeric(df[time_col],errors="coerce")
            sample=df["timestamp"].dropna()
            if not sample.empty and abs(float(sample.iloc[0]))>10_000_000_000_000: df["timestamp"]/=1_000_000
            elif not sample.empty and abs(float(sample.iloc[0]))>10_000_000_000: df["timestamp"]/=1_000
            for col in ["open","high","low","close","volume"]:
                if col not in df.columns:
                    if col=="volume": df[col]=0.0
                    else: logger.warning("Missing %s for %s %s",col,symbol,resolution); return _empty()
                df[col]=pd.to_numeric(df[col],errors="coerce")
            df.dropna(subset=["timestamp","open","high","low","close"],inplace=True)
            if df.empty: continue
            df["timestamp"]=pd.to_datetime(df["timestamp"],unit="s",utc=True,errors="coerce"); df.dropna(subset=["timestamp"],inplace=True); df.sort_values("timestamp",inplace=True); df.set_index("timestamp",inplace=True)
            return df[["open","high","low","close","volume"]]
        except requests.RequestException as exc: logger.warning("Delta history request failed %s %s attempt=%s: %s",symbol,resolution,attempt,exc)
        except Exception as exc: logger.exception("Delta history parse failed %s %s: %s",symbol,resolution,exc)
        if attempt<RETRIES: time.sleep(1)
    return _empty()

def get_history(symbol="BTCUSD",resolution="5m",limit=200): return _fetch_history(symbol,resolution,limit)

def get_multi_timeframe_history(symbol="BTCUSD",limit=200):
    symbol=_canonical_symbol(symbol)
    return {"symbol":symbol,"5m":_fetch_history(symbol,"5m",limit),"15m":_fetch_history(symbol,"15m",limit),"1h":_fetch_history(symbol,"1h",limit),"1d":_fetch_history(symbol,"1d",limit)}
