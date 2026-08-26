"""NAKSHATRA AI - Historical Validation / Backtest Engine v1.0
Input: 5-minute OHLCV CSV with timestamp,open,high,low,close,volume.
No trades are placed.
"""
from __future__ import annotations
import argparse, importlib
from pathlib import Path
import numpy as np
import pandas as pd

def load_ohlcv(path):
    df = pd.read_csv(path)
    df.columns = [c.lower().strip() for c in df.columns]
    required = {"timestamp","open","high","low","close","volume"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"Missing CSV columns: {sorted(missing)}")
    ts = pd.to_datetime(df["timestamp"], errors="coerce", utc=True)
    bad = ts.isna()
    if bad.any():
        raw = pd.to_numeric(df.loc[bad,"timestamp"], errors="coerce")
        ts.loc[bad] = pd.to_datetime(raw, unit="ms", errors="coerce", utc=True)
        still = ts.loc[bad].isna()
        if still.any():
            ts.loc[bad] = pd.to_datetime(raw[still], unit="s", errors="coerce", utc=True)
    if ts.isna().any():
        raise ValueError("Unparseable timestamps found.")
    df["timestamp"] = ts
    df = df.set_index("timestamp").sort_index()
    for c in ["open","high","low","close","volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    return df.dropna(subset=["open","high","low","close","volume"]).loc[~df.index.duplicated(keep="last")]

def resample(df, rule):
    return df.resample(rule).agg({
        "open":"first","high":"max","low":"min","close":"last","volume":"sum"
    }).dropna()

def build_data(df5, symbol):
    return {"5m":df5, "15m":resample(df5,"15min"),
            "1h":resample(df5,"1h"), "1d":resample(df5,"1D"),
            "symbol":symbol}

def forward_outcome(df, i, horizon, signal):
    j = i + horizon
    if j >= len(df): return None
    entry = float(df["close"].iloc[i]); future = float(df["close"].iloc[j])
    if entry == 0: return None
    market_pct = (future-entry)/entry*100
    signal_pct = market_pct if signal=="BUY" else (-market_pct if signal=="SELL" else 0)
    return entry, future, market_pct, signal_pct

def run_backtest(csv_path, symbol="BTCUSD", horizons=(3,6,12), step=1, min_history=250):
    df5 = load_ohlcv(csv_path)
    generate_signal = importlib.import_module("analysis.signal").generate_signal
    rows = []
    for i in range(min_history, len(df5), max(1,step)):
        try:
            result = generate_signal(build_data(df5.iloc[:i+1].copy(), symbol))
            signal = str(result.get("recommendation","WAIT")).upper()
            confidence = float(result.get("overall_confidence",0) or 0)
            agreement = result.get("agreement","")
            direction = result.get("direction","")
            error = ""
        except Exception as exc:
            signal, confidence, agreement, direction, error = "ERROR", np.nan, "", "", repr(exc)
        for h in horizons:
            out = forward_outcome(df5,i,h,signal)
            if out is None: continue
            entry,future,market_pct,signal_pct = out
            rows.append({"timestamp":df5.index[i],"signal":signal,"confidence":confidence,
                         "agreement":agreement,"direction":direction,"horizon":h,
                         "entry":entry,"future":future,"market_return_pct":market_pct,
                         "signal_return_pct":signal_pct,"error":error})
    results = pd.DataFrame(rows)
    if results.empty: raise RuntimeError("No backtest rows produced.")
    summaries=[]
    for h in horizons:
        x=results[(results.horizon==h)&results.signal.isin(["BUY","SELL"])]
        wins=int((x.signal_return_pct>0).sum())
        summaries.append({"horizon":h,"trades":len(x),"wins":wins,
                          "losses":len(x)-wins,
                          "win_rate_pct":round(wins/len(x)*100,2) if len(x) else 0,
                          "avg_return_pct":round(x.signal_return_pct.mean(),4) if len(x) else 0})
    summary=pd.DataFrame(summaries)
    x=results[results.signal.isin(["BUY","SELL"])].copy()
    confidence=[]
    if not x.empty:
        bins=[0,50,60,70,80,90,100.0001]
        labels=["<50","50-59","60-69","70-79","80-89","90-100"]
        x["confidence_bucket"]=pd.cut(x.confidence,bins=bins,labels=labels,right=False)
        for bucket,g in x.groupby("confidence_bucket",observed=False):
            if len(g):
                confidence.append({"confidence_bucket":str(bucket),"trades":len(g),
                    "wins":int((g.signal_return_pct>0).sum()),
                    "win_rate_pct":round((g.signal_return_pct>0).mean()*100,2),
                    "avg_return_pct":round(g.signal_return_pct.mean(),4)})
    return results, summary, pd.DataFrame(confidence)

def main():
    p=argparse.ArgumentParser()
    p.add_argument("csv"); p.add_argument("--symbol",default="BTCUSD")
    p.add_argument("--horizons",default="3,6,12"); p.add_argument("--step",type=int,default=1)
    p.add_argument("--min-history",type=int,default=250); p.add_argument("--output",default="nakshatra_backtest")
    a=p.parse_args(); horizons=[int(x) for x in a.horizons.split(",") if x.strip()]
    results,summary,confidence=run_backtest(a.csv,a.symbol,horizons,a.step,a.min_history)
    prefix=Path(a.output)
    prefix.parent.mkdir(parents=True,exist_ok=True)
    results.to_csv(str(prefix)+"_signals.csv",index=False)
    summary.to_csv(str(prefix)+"_summary.csv",index=False)
    confidence.to_csv(str(prefix)+"_confidence.csv",index=False)
    print("\n=== SUMMARY ===\n",summary.to_string(index=False))
    if not confidence.empty: print("\n=== CONFIDENCE ===\n",confidence.to_string(index=False))

if __name__=="__main__": main()
