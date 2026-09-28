from __future__ import annotations
import time, html, requests, xml.etree.ElementTree as ET
from datetime import timezone
from email.utils import parsedate_to_datetime
_CACHE={"ts":0,"data":None}; TTL=300
UA={"User-Agent":"Mozilla/5.0 (NakshatraAI/2.13)"}
FEEDS=[
 ("INDIA","RBI","https://www.rbi.org.in/Scripts/RSS.aspx?Id=180"),
 ("WORLD","FED","https://www.federalreserve.gov/feeds/press_monetary.xml"),
 ("INDIA","MARKET NEWS","https://news.google.com/rss/search?q=India+Nifty+RBI+inflation+markets&hl=en-IN&gl=IN&ceid=IN:en"),
 ("WORLD","GLOBAL NEWS","https://news.google.com/rss/search?q=Federal+Reserve+CPI+jobs+oil+gold+markets&hl=en-US&gl=US&ceid=US:en"),
]
KEYS={
 "rbi":("HIGH",["NIFTY","BANKNIFTY","INR"],"Rates/liquidity can change bank, bond and INR expectations."),
 "repo":("HIGH",["NIFTY","BANKNIFTY","INR"],"Policy-rate/liquidity expectations can reprice rate-sensitive assets."),
 "inflation":("HIGH",["NIFTY","BANKNIFTY","GOLD","INR"],"Inflation surprise can change rate expectations and yields."),
 "cpi":("HIGH",["NIFTY","GOLD","USD"],"Inflation surprise can move yields, USD and risk assets."),
 "federal reserve":("HIGH",["NIFTY","GOLD","USD"],"Fed expectations can move global yields, USD and risk appetite."),
 "fomc":("HIGH",["NIFTY","GOLD","USD"],"Fed expectations can move global yields, USD and risk appetite."),
 "jobs":("HIGH",["NIFTY","GOLD","USD"],"US labour data can change Fed-rate expectations."),
 "payroll":("HIGH",["NIFTY","GOLD","USD"],"US labour data can change Fed-rate expectations."),
 "crude":("MEDIUM",["NIFTY","INR","CRUDEOIL"],"Oil moves can affect Indian inflation, INR and energy-sensitive sectors."),
 "oil":("MEDIUM",["NIFTY","INR","CRUDEOIL"],"Oil moves can affect Indian inflation, INR and energy-sensitive sectors."),
}
def _effect(title):
    low=title.lower()
    for k,v in KEYS.items():
        if k in low:return v
    return "MEDIUM",["NIFTY"],"Headline may affect risk sentiment; confirm with live price/volume before acting."
def _parse(url,region,source):
    r=requests.get(url,headers=UA,timeout=8); r.raise_for_status(); root=ET.fromstring(r.content); out=[]
    for item in root.findall(".//item")[:8]:
        title=html.unescape((item.findtext("title") or "").strip()); link=(item.findtext("link") or "").strip(); pub=(item.findtext("pubDate") or "").strip()
        try:
            dt=parsedate_to_datetime(pub)
            if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
            iso=dt.isoformat()
        except:iso=None
        imp,assets,effect=_effect(title)
        out.append({"type":"NEWS","region":region,"source":source,"title":title,"time":iso,"importance":imp,"assets":assets,"effect":effect,"url":link})
    return out
def get_market_catalysts(symbol="NIFTY50",expiry=None):
    now=time.time()
    if _CACHE["data"] is not None and now-_CACHE["ts"]<TTL:items=list(_CACHE["data"])
    else:
        items=[]
        for region,source,url in FEEDS:
            try:items.extend(_parse(url,region,source))
            except Exception:pass
        items.sort(key=lambda x:x.get("time") or "",reverse=True); _CACHE.update(ts=now,data=items[:20]); items=list(_CACHE["data"])
    if expiry:
        items.insert(0,{"type":"EVENT","region":"INDIA","source":"NSE OPTION EXPIRY","title":f"{symbol} option expiry {expiry}","time":None,"importance":"HIGH","assets":[symbol],"effect":"Expiry can amplify gamma/hedging flows; use live OI, premium and position-shift confirmation.","url":None})
    return {"status":"OK" if items else "PARTIAL","items":items[:10],"note":"News/event impact is contextual, not a guaranteed direction. Trade only after live price/volume confirmation."}
