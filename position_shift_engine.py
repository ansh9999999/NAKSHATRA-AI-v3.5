from __future__ import annotations
from collections import defaultdict, deque
from threading import Lock
import time, math

_LOCK=Lock(); _H=defaultdict(lambda: deque(maxlen=180)); MIN_SNAPSHOT_SECONDS=10

def _n(v):
    try:
        x=float(v); return x if math.isfinite(x) else None
    except Exception:return None

def _rows(payload):
    out={}
    for r in (payload or {}).get('rows',[]) or []:
        strike=_n(r.get('strike',r.get('strike_price')))
        if strike is None: continue
        typ=str(r.get('type') or r.get('option_type') or '').upper()
        if typ in ('CALL','CE'):
            out[(strike,'CE')]={'oi':_n(r.get('oi',r.get('call_oi'))),'volume':_n(r.get('volume',r.get('call_volume'))),'ltp':_n(r.get('ltp',r.get('call_ltp'))),'iv':_n(r.get('iv',r.get('call_iv')))}
        elif typ in ('PUT','PE'):
            out[(strike,'PE')]={'oi':_n(r.get('oi',r.get('put_oi'))),'volume':_n(r.get('volume',r.get('put_volume'))),'ltp':_n(r.get('ltp',r.get('put_ltp'))),'iv':_n(r.get('iv',r.get('put_iv')))}
        else:
            if any(k in r for k in ('call_oi','ce_oi','call_ltp','ce_ltp')):
                out[(strike,'CE')]={'oi':_n(r.get('call_oi',r.get('ce_oi'))),'volume':_n(r.get('call_volume',r.get('ce_volume'))),'ltp':_n(r.get('call_ltp',r.get('ce_ltp'))),'iv':_n(r.get('call_iv',r.get('ce_iv')))}
            if any(k in r for k in ('put_oi','pe_oi','put_ltp','pe_ltp')):
                out[(strike,'PE')]={'oi':_n(r.get('put_oi',r.get('pe_oi'))),'volume':_n(r.get('put_volume',r.get('pe_volume'))),'ltp':_n(r.get('put_ltp',r.get('pe_ltp'))),'iv':_n(r.get('put_iv',r.get('pe_iv')))}
    return out

def ingest(symbol, spot, chain):
    if not isinstance(chain,dict) or chain.get('status')!='OK': return
    rows=_rows(chain)
    if not rows:return
    now=time.time(); snap={'t':now,'spot':_n(spot),'expiry':chain.get('expiry'),'rows':rows}
    with _LOCK:
        h=_H[symbol]
        if h and now-h[-1]['t'] < MIN_SNAPSHOT_SECONDS:return
        h.append(snap)

def _past(h,seconds):
    target=h[-1]['t']-seconds
    return min(h,key=lambda s:abs(s['t']-target)) if h else None

def _pct(a,b):
    return ((a-b)/abs(b)*100.0) if a is not None and b not in (None,0) else None

def _window(cur,old,atm,step_count=5):
    if not old:return None
    strikes=sorted({k[0] for k in cur['rows']})
    if not strikes:return None
    near=sorted(strikes,key=lambda x:abs(x-atm))[:max(6,step_count*2+1)]
    ce_oi=pe_oi=ce_prem=pe_prem=ce_vol=pe_vol=0.0; nce=npe=0
    for strike in near:
        for typ in ('CE','PE'):
            a=cur['rows'].get((strike,typ)); b=old['rows'].get((strike,typ))
            if not a or not b:continue
            doi=(a['oi']-b['oi']) if a['oi'] is not None and b['oi'] is not None else 0
            dp=_pct(a['ltp'],b['ltp']) or 0
            dv=(a['volume']-b['volume']) if a['volume'] is not None and b['volume'] is not None else 0
            if typ=='CE': ce_oi+=doi; ce_prem+=dp; ce_vol+=max(0,dv); nce+=1
            else: pe_oi+=doi; pe_prem+=dp; pe_vol+=max(0,dv); npe+=1
    ce_prem=ce_prem/max(1,nce); pe_prem=pe_prem/max(1,npe)
    spot_pct=_pct(cur['spot'],old['spot']) or 0
    # Bullish structure: PE OI build + CE OI unwind + spot/CE premium strength.
    oi_scale=max(1,abs(ce_oi)+abs(pe_oi)); vol_scale=max(1,ce_vol+pe_vol)
    bull=(pe_oi-ce_oi)/oi_scale*35 + max(-1,min(1,spot_pct/.12))*25 + max(-1,min(1,(ce_prem-pe_prem)/8))*25 + ((ce_vol-pe_vol)/vol_scale)*15
    score=max(-100,min(100,bull))
    return {'score':round(score,1),'spot_change_pct':round(spot_pct,3),'ce_oi_change':round(ce_oi),'pe_oi_change':round(pe_oi),'ce_premium_pct':round(ce_prem,2),'pe_premium_pct':round(pe_prem,2),'ce_volume_add':round(ce_vol),'pe_volume_add':round(pe_vol)}

def analyze(symbol):
    with _LOCK:h=list(_H.get(symbol,[]))
    if len(h)<2:return {'status':'WARMING UP','bias':'WAIT','phase':'COLLECTING','strength':0,'snapshots':len(h),'message':'Collecting live option-chain snapshots.'}
    cur=h[-1]; strikes=sorted({k[0] for k in cur['rows']}); spot=cur['spot']
    if not strikes or spot is None:return {'status':'NO DATA','bias':'WAIT','phase':'NO DATA','strength':0}
    atm=min(strikes,key=lambda x:abs(x-spot))
    windows={}
    for label,sec in [('1m',60),('3m',180),('5m',300),('15m',900)]:
        old=_past(h,sec)
        # Don't pretend a 15m window exists from 2m of history.
        if old and cur['t']-old['t'] >= sec*.65: windows[label]=_window(cur,old,atm)
    vals=[v['score'] for v in windows.values() if v]
    if not vals:return {'status':'WARMING UP','bias':'WAIT','phase':'COLLECTING','strength':0,'snapshots':len(h),'atm':atm,'message':'Need more snapshot history for position-shift windows.'}
    weights={'1m':.35,'3m':.30,'5m':.22,'15m':.13}; den=sum(weights[k] for k in windows); score=sum(windows[k]['score']*weights[k] for k in windows)/den
    strength=round(abs(score)); bias='BULLISH' if score>=22 else 'BEARISH' if score<=-22 else 'NEUTRAL'
    seq=[windows[k]['score'] for k in ('15m','5m','3m','1m') if k in windows]
    if bias=='NEUTRAL':phase='MIXED'
    elif len(seq)>=2 and abs(seq[-1])>=abs(seq[-2])+8:phase='BUILDING'
    elif len(seq)>=2 and abs(seq[-1])+8<abs(seq[-2]):phase='FADING'
    else:phase='CONFIRMED' if strength>=45 else 'WATCH'
    action='CE BUY WATCH' if bias=='BULLISH' else 'PE BUY WATCH' if bias=='BEARISH' else 'WAIT'
    return {'status':'OK','bias':bias,'phase':phase,'strength':strength,'score':round(score,1),'action':action,'atm':atm,'expiry':cur['expiry'],'snapshots':len(h),'history_minutes':round((cur['t']-h[0]['t'])/60,1),'windows':windows,'source':'NSE option-chain snapshots + Kotak live spot','note':'Intraday inference from successive snapshots; not FII/DII live order flow.'}
