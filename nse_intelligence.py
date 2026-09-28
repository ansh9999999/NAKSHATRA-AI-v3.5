from __future__ import annotations
from datetime import date,timedelta
import csv,io,math,threading,time,requests
_CACHE={};_LOCK=threading.Lock();TTL=900
HEADERS={'User-Agent':'Mozilla/5.0 Chrome/126 Safari/537.36','Accept':'application/json,text/plain,*/*','Referer':'https://www.nseindia.com/'}
def _num(v,d=None):
 try:
  x=float(str(v).replace(',','').replace('₹','').strip());return x if math.isfinite(x) else d
 except:return d
def _cached(k,fn):
 now=time.time()
 with _LOCK:
  h=_CACHE.get(k)
  if h and now-h[0]<TTL:return h[1]
 try:v=fn()
 except Exception as e:v={'status':'ERROR','rows':[],'error':str(e)}
 with _LOCK:_CACHE[k]=(now,v)
 return v
def _session():
 s=requests.Session();s.headers.update(HEADERS)
 try:s.get('https://www.nseindia.com/',timeout=8)
 except:pass
 return s
def _fii_dii():
 def load():
  errors=[]
  try:
   r=_session().get('https://www.nseindia.com/api/fiidiiTradeReact',timeout=12);r.raise_for_status();raw=r.json();rows=[]
   for x in raw if isinstance(raw,list) else []:
    c=str(x.get('category') or x.get('Category') or '').upper();name='FII/FPI' if ('FII' in c or 'FPI' in c) else ('DII' if 'DII' in c else None)
    if name:rows.append({'category':name,'date':x.get('date') or x.get('Date'),'buy_cr':_num(x.get('buyValue') or x.get('buy_value')),'sell_cr':_num(x.get('sellValue') or x.get('sell_value')),'net_cr':_num(x.get('netValue') or x.get('net_value'))})
   if rows:return {'status':'OK','rows':rows,'source':'NSE official API','data_type':'EOD/provisional'}
   errors.append('official API returned no rows')
  except Exception as e:errors.append('official API: '+str(e))
  try:
   from nselib import capital_market
   df=capital_market.fii_dii_trading_activity();raw=df.reset_index().to_dict('records');rows=[]
   for x in raw:
    joined=' '.join(map(str,x.values())).upper();name='FII/FPI' if ('FII' in joined or 'FPI' in joined) else ('DII' if 'DII' in joined else None)
    if not name:continue
    def pick(t):
     for k,v in x.items():
      if t in ''.join(c for c in str(k).lower() if c.isalnum()):return v
    rows.append({'category':name,'date':pick('date'),'buy_cr':_num(pick('buy')),'sell_cr':_num(pick('sell')),'net_cr':_num(pick('net'))})
   if rows:return {'status':'OK','rows':rows,'source':'NSE/nselib','data_type':'EOD/provisional'}
  except Exception as e:errors.append('nselib: '+str(e))
  return {'status':'ERROR','rows':[],'source':'NSE','error':' | '.join(errors)}
 return _cached('fii211',load)
def _archive(kind):
 errs=[]
 for i in range(10):
  d=date.today()-timedelta(days=i)
  if d.weekday()>=5:continue
  url=f"https://nsearchives.nseindia.com/content/nsccl/fao_participant_{kind}_{d.strftime('%d%m%Y')}.csv"
  try:
   r=requests.get(url,headers=HEADERS,timeout=12)
   if r.status_code!=200 or len(r.content)<80:errs.append(f'{d} HTTP {r.status_code}');continue
   rows=list(csv.DictReader(io.StringIO(r.content.decode('utf-8-sig',errors='replace'))))
   if rows:return {'status':'OK','date':d.isoformat(),'rows':rows,'source':'NSE official archive','data_type':'EOD'}
  except Exception as e:errs.append(f'{d} {e}')
 return {'status':'NO DATA','rows':[],'source':'NSE official archive','error':'; '.join(errs[-4:])}
def _participant_rows(rows):
 out=[]
 for r in rows or []:
  def val(*need):
   for k,v in r.items():
    nk=''.join(c for c in str(k).lower() if c.isalnum())
    if all(n in nk for n in need):return _num(v)
  p=None
  for k,v in r.items():
   if ''.join(c for c in str(k).lower() if c.isalnum()) in ('clienttype','participant','client'):p=str(v or '').strip().upper();break
  if p:out.append({'participant':p,'future_index_long':val('future','index','long'),'future_index_short':val('future','index','short'),'future_stock_long':val('future','stock','long'),'future_stock_short':val('future','stock','short'),'index_call_long':val('option','index','call','long'),'index_call_short':val('option','index','call','short'),'index_put_long':val('option','index','put','long'),'index_put_short':val('option','index','put','short')})
 return out
def _participant(kind):
 def load():
  x=_archive(kind)
  if x.get('rows'):x['rows']=_participant_rows(x['rows']);x['status']='OK' if x['rows'] else 'NO DATA'
  return x
 return _cached('part'+kind+'211',load)
def _vix():
 def load():
  try:
   from nselib import capital_market
   df=capital_market.india_vix_data(period='1M');r=df.reset_index().to_dict('records')
   if not r:return {'status':'NO DATA'}
   last=r[-1];prev=r[-2] if len(r)>1 else {}
   def pick(x):
    for k,v in x.items():
     if str(k).lower() in ('close','vix'):return _num(v)
   cur=pick(last);pv=pick(prev)
   return {'status':'OK','value':cur,'change':cur-pv if cur is not None and pv is not None else None,'source':'NSE/nselib'}
  except Exception as e:return {'status':'ERROR','error':str(e)}
 return _cached('vix211',load)
def _sentiment(fii,oi,vix):
 score=0.;reasons=[]
 for name,w in [('FII/FPI',2),('DII',1.5)]:
  r=next((x for x in fii.get('rows',[]) if x.get('category')==name),None)
  if r and r.get('net_cr') is not None:score+=max(-w,min(w,r['net_cr']/5000));reasons.append(f"{name} net ₹{r['net_cr']:+,.0f} Cr")
 fr=next((x for x in oi.get('rows',[]) if x.get('participant')=='FII'),None)
 if fr and fr.get('future_index_long') is not None and fr.get('future_index_short') is not None:
  l,s=fr['future_index_long'],fr['future_index_short'];score+=max(-1,min(1,(l-s)/(l+s))) if l+s else 0;reasons.append(f'FII index futures L/S {l:,.0f}/{s:,.0f}')
 if vix.get('value') is not None:score+=-.5 if vix['value']>=20 else .25 if vix['value']<14 else 0;reasons.append(f"India VIX {vix['value']:.2f}")
 bias='BULLISH' if score>=.8 else 'BEARISH' if score<=-.8 else 'NEUTRAL'
 return {'status':'OK' if reasons else 'NO DATA','bias':bias,'score':round(score,2),'reasons':reasons,'note':'Positioning context only; participant reports are EOD, not live order flow.'}
def get_nse_intelligence(symbol='NIFTY50'):
 fii=_fii_dii();oi=_participant('oi');vol=_participant('vol');vix=_vix();sent=_sentiment(fii,oi,vix);st=[fii.get('status'),oi.get('status'),vol.get('status'),vix.get('status')];ok=sum(x=='OK' for x in st)
 return {'status':'OK' if ok>=3 else 'PARTIAL' if ok else 'NO DATA','symbol':symbol,'as_of':oi.get('date') or vol.get('date'),'fii_dii':fii,'participant_oi':oi,'participant_volume':vol,'india_vix':vix,'sentiment':sent,'data_quality':{'ok_modules':ok,'total_modules':4,'statuses':st},'disclaimer':'FII/DII and participant reports are EOD/provisional positioning data, not live buy/sell order flow.'}
