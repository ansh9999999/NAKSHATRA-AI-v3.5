"""NAKSHATRA Indian/Delta option-chain engine v2.10.
NSE v3 REST is primary for NIFTY/BANKNIFTY, nselib is secondary, Kotak last fallback.
No synthetic/stale chain is fabricated.
"""
from datetime import datetime, timezone
import math, re, threading, time
import requests

from delta import get_option_tickers
from market_registry import canonical_symbol, get_market
from kotak_neo_adaptor import get_option_chain as neo_get_option_chain

_CACHE = {}; _LOCK = threading.Lock(); TTL = 45

def _num(v, default=0.0):
    try:
        if v is None or v == "": return default
        x=float(str(v).replace(",","")); return x if math.isfinite(x) else default
    except Exception: return default

def _clean_expiry(v):
    if v is None: return None
    s=str(v).strip()
    for fmt in ("%d-%b-%Y","%d-%m-%Y","%d/%m/%Y","%Y-%m-%d","%d-%B-%Y"):
        try: return datetime.strptime(s,fmt).strftime("%d-%m-%Y")
        except Exception: pass
    return s or None

def _no_data(reason, source="none", expiry=None, diagnostics=None):
    return {"status":"NO DATA","signal":"NEUTRAL","confidence":0,"reason":reason,"source":source,"expiry":expiry,"rows":[],"row_count":0,"diagnostics":diagnostics or []}

def _max_pain(rows):
    strikes=sorted({r["strike"] for r in rows if r.get("strike") is not None})
    if not strikes:return None
    return min(strikes,key=lambda s:sum((max(s-r["strike"],0) if r["type"]=="CALL" else max(r["strike"]-s,0))*_num(r.get("oi")) for r in rows))

def _analyze_rows(symbol,rows,spot_price=None,expiry=None,source="unknown"):
    calls=[r for r in rows if r.get("type")=="CALL"]; puts=[r for r in rows if r.get("type")=="PUT"]
    if not calls or not puts:return _no_data(f"Incomplete option chain: calls={len(calls)} puts={len(puts)}",source,expiry)
    call_oi=sum(_num(r.get("oi")) for r in calls); put_oi=sum(_num(r.get("oi")) for r in puts)
    call_vol=sum(_num(r.get("volume")) for r in calls); put_vol=sum(_num(r.get("volume")) for r in puts)
    pcr=put_oi/call_oi if call_oi else None; vpcr=put_vol/call_vol if call_vol else None
    spot=_num(spot_price,0); strikes=sorted({r["strike"] for r in rows if _num(r.get("strike"))>0})
    atm=min(strikes,key=lambda k:abs(k-spot)) if strikes and spot else None
    cres=max(calls,key=lambda r:_num(r.get("oi")),default=None); psup=max(puts,key=lambda r:_num(r.get("oi")),default=None)
    signal="BULLISH" if pcr is not None and pcr>=1.10 else "BEARISH" if pcr is not None and pcr<=0.90 else "SIDEWAYS"
    confidence=min(95.0,50+abs(pcr-1)*100) if pcr is not None else 0
    topc=sorted(calls,key=lambda r:_num(r.get("oi")),reverse=True)[:5]; topp=sorted(puts,key=lambda r:_num(r.get("oi")),reverse=True)[:5]
    try:
        from analysis.gamma_squeeze_engine import detect_squeeze
        squeeze=detect_squeeze(symbol,rows,spot,expiry)
    except Exception as e: squeeze={"status":"NO DATA","reason":str(e)}
    return {"status":"OK","signal":signal,"confidence":round(confidence,1),"underlying":symbol,"source":source,"expiry":expiry,"spot":round(spot,2) if spot else None,"atm_strike":atm,"pcr":round(pcr,4) if pcr is not None else None,"volume_pcr":round(vpcr,4) if vpcr is not None else None,"call_oi":round(call_oi,2),"put_oi":round(put_oi,2),"call_volume":round(call_vol,2),"put_volume":round(put_vol,2),"max_call_oi_resistance":cres.get("strike") if cres else None,"max_put_oi_support":psup.get("strike") if psup else None,"max_pain":_max_pain(rows),"top_call_oi":[{"strike":r["strike"],"oi":_num(r.get("oi")),"ltp":_num(r.get("ltp")),"oi_change":_num(r.get("oi_change"))} for r in topc],"top_put_oi":[{"strike":r["strike"],"oi":_num(r.get("oi")),"ltp":_num(r.get("ltp")),"oi_change":_num(r.get("oi_change"))} for r in topp],"rows":rows,"row_count":len(rows),"gamma_squeeze":squeeze,"reason":f"PCR {pcr:.2f} • {source}" if pcr is not None else f"PCR unavailable • {source}"}

# NSE changed its public option-chain interface to contract-info + option-chain-v3.
def _nse_v3(symbol):
    ns={"NIFTY50":"NIFTY","BANKNIFTY":"BANKNIFTY"}.get(symbol)
    if not ns:return None,"unsupported symbol"
    s=requests.Session(); s.headers.update({"User-Agent":"Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/126 Safari/537.36","Accept":"application/json,text/plain,*/*","Accept-Language":"en-US,en;q=0.9","Referer":"https://www.nseindia.com/option-chain","Connection":"keep-alive"})
    try:
        s.get("https://www.nseindia.com/option-chain",timeout=8)
        ci=s.get("https://www.nseindia.com/api/option-chain-contract-info",params={"symbol":ns},timeout=10)
        ci.raise_for_status(); meta=ci.json(); expiries=meta.get("expiryDates") or []
        if not expiries:return None,"NSE contract-info returned no expiries"
        expiry=expiries[0]
        rr=s.get("https://www.nseindia.com/api/option-chain-v3",params={"type":"Indices","symbol":ns,"expiry":expiry},timeout=12)
        rr.raise_for_status(); data=rr.json()
        records=data.get("records") or data.get("data") or {}
        items=records.get("data",[]) if isinstance(records,dict) else records if isinstance(records,list) else []
        spot=(records.get("underlyingValue") if isinstance(records,dict) else None) or data.get("underlyingValue")
        rows=[]
        for item in items:
            strike=_num(item.get("strikePrice") or item.get("strike"),None)
            if not strike: continue
            for side,typ in (("CE","CALL"),("PE","PUT")):
                x=item.get(side) or {}
                if not x: continue
                rows.append({"symbol":x.get("identifier") or f"{ns}-{strike:g}-{side}","type":typ,"strike":strike,"oi":_num(x.get("openInterest")),"volume":_num(x.get("totalTradedVolume")),"ltp":_num(x.get("lastPrice")),"oi_change":_num(x.get("changeinOpenInterest")),"iv":_num(x.get("impliedVolatility")),"expiry":_clean_expiry(x.get("expiryDate") or expiry)})
        if rows:return (rows,_clean_expiry(expiry),_num(spot,None)),None
        return None,"NSE option-chain-v3 returned zero rows"
    except Exception as e:return None,f"NSE v3 error: {type(e).__name__}: {e}"
    finally:s.close()

def _nselib(symbol):
    ns={"NIFTY50":"NIFTY","BANKNIFTY":"BANKNIFTY"}.get(symbol)
    if not ns:return None,"unsupported symbol"
    try:
        from nselib import derivatives
        df=derivatives.nse_live_option_chain(symbol=ns,oi_mode="compact")
        if df is None or getattr(df,"empty",True):return None,"nselib returned empty dataframe"
        # nselib compact/full column names vary; normalize tokens and identify CE/PE columns by keywords.
        cmap={re.sub(r"[^a-z0-9]","",str(c).lower()):c for c in df.columns}
        def pick(*tokens):
            for k,c in cmap.items():
                if all(t in k for t in tokens):return c
            return None
        strike=pick("strike","price") or pick("strike")
        coi=pick("calls","oi") or pick("ce","oi"); poi=pick("puts","oi") or pick("pe","oi")
        if strike is None or coi is None or poi is None:return None,f"nselib columns not recognized: {list(map(str,df.columns))[:12]}"
        cvol=pick("calls","volume") or pick("ce","volume"); pvol=pick("puts","volume") or pick("pe","volume")
        cltp=pick("calls","ltp") or pick("ce","ltp"); pltp=pick("puts","ltp") or pick("pe","ltp")
        rows=[]
        for _,r in df.iterrows():
            st=_num(r.get(strike),None)
            if not st:continue
            rows += [{"symbol":f"{ns}-{st:g}-CE","type":"CALL","strike":st,"oi":_num(r.get(coi)),"volume":_num(r.get(cvol)),"ltp":_num(r.get(cltp)),"oi_change":0,"iv":0},{"symbol":f"{ns}-{st:g}-PE","type":"PUT","strike":st,"oi":_num(r.get(poi)),"volume":_num(r.get(pvol)),"ltp":_num(r.get(pltp)),"oi_change":0,"iv":0}]
        return ((rows,None,None),None) if rows else (None,"nselib parsed zero rows")
    except Exception as e:return None,f"nselib error: {type(e).__name__}: {e}"

def _kotak(symbol):
    try:
        p=neo_get_option_chain(symbol); rows=p.get("rows",[]) if isinstance(p,dict) else p or []; exp=p.get("expiry") if isinstance(p,dict) else None
        return (rows,_clean_expiry(exp)) if rows else None
    except Exception:return None

def _delta(symbol,spot):
    underlying="BTC" if symbol=="BTCUSD" else "ETH"; raw=get_option_tickers(underlying); today=datetime.now(timezone.utc).date(); parsed=[]
    for item in raw or []:
        sym=str(item.get("symbol") or ""); ct=str(item.get("contract_type") or "").lower(); typ="CALL" if "call" in ct or sym.startswith("C-") else "PUT" if "put" in ct or sym.startswith("P-") else None
        m=re.search(r"^[CP]-[A-Z]+-([0-9.]+)-([0-9]{6})$",sym); strike=_num(item.get("strike_price"),None); exp=None
        if m:
            strike=_num(m.group(1),strike)
            try:exp=datetime.strptime(m.group(2),"%d%m%y").date()
            except Exception:pass
        if typ and strike and exp and exp>=today:parsed.append((item,typ,strike,exp))
    if not parsed:return _no_data("No current/future Delta options","Delta")
    expiry=min(x[3] for x in parsed); rows=[]
    for item,typ,strike,exp in parsed:
        if exp==expiry:rows.append({"symbol":item.get("symbol"),"type":typ,"strike":strike,"oi":_num(item.get("oi")),"volume":_num(item.get("volume")),"ltp":_num(item.get("close") or item.get("mark_price")),"oi_change":_num(item.get("oi_change"))})
    return _analyze_rows(symbol,rows,spot,expiry.strftime("%d-%m-%Y"),"Delta")

def analyze_option_chain(symbol="BTCUSD",spot_price=None):
    symbol=canonical_symbol(symbol); market=get_market(symbol); key=symbol; now=time.time()
    with _LOCK:
        h=_CACHE.get(key)
        if h and now-h[0]<TTL:return h[1]
    if market and market.get("provider")=="kotak_neo" and symbol in ("NIFTY50","BANKNIFTY"):
        diagnostics=[]; payload,err=_nse_v3(symbol)
        if payload:
            rows,exp,nse_spot=payload; result=_analyze_rows(symbol,rows,spot_price or nse_spot,exp,"NSE v3")
        else:
            diagnostics.append(err); payload,err=_nselib(symbol)
            if payload:
                rows,exp,nse_spot=payload; result=_analyze_rows(symbol,rows,spot_price or nse_spot,exp,"NSE/nselib")
            else:
                diagnostics.append(err); k=_kotak(symbol)
                if k:result=_analyze_rows(symbol,k[0],spot_price,k[1],"Kotak Neo")
                else:result=_no_data("All option-chain providers returned no usable CE/PE rows","none",diagnostics=diagnostics)
    elif market and market.get("provider")=="kotak_neo":result=_no_data("Option chain is enabled only for NIFTY/BANKNIFTY in this build","none")
    else:result=_delta(symbol,spot_price)
    with _LOCK:
        _CACHE[key]=(now,result)
        while len(_CACHE) > 8:
            oldest=min(_CACHE, key=lambda k: _CACHE[k][0])
            _CACHE.pop(oldest, None)
    return result
