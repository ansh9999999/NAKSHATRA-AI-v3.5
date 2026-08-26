"""NAKSHATRA AI - Decision Engine v5.2 validation tests."""
from analysis.confidence_engine import calculate_decision

def check(name,t,a,n,rec,agr):
    r=calculate_decision({"signal":t,"confidence":90 if t!="NEUTRAL" else 0,"reasons":[]},
                         {"bias":a,"reasons":[]},{"bias":n,"reasons":[]})
    assert r["recommendation"]==rec,(name,r)
    assert r["agreement"]==agr,(name,r)
    print(f"PASS | {name} | {r['recommendation']} | {r['agreement']}")

def main():
    check("BUY+BULLISH+BULLISH","BUY","BULLISH","BULLISH","BUY","FULL AGREEMENT")
    check("SELL+BEARISH+BEARISH","SELL","BEARISH","BEARISH","SELL","FULL AGREEMENT")
    check("SELL+BEARISH+BUY","SELL","BEARISH","BUY","SELL","PARTIAL AGREEMENT")
    check("BUY+BULLISH+SELL","BUY","BULLISH","SELL","BUY","PARTIAL AGREEMENT")
    check("NEUTRAL+BEARISH+BUY","NEUTRAL","BEARISH","BUY","WAIT","NO AGREEMENT")
    check("NEUTRAL+NEUTRAL+NEUTRAL","NEUTRAL","NEUTRAL","NEUTRAL","WAIT","NO AGREEMENT")
    print("All tests passed.")
if __name__=="__main__": main()
