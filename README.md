NAKSHATRA AI v4.0 - Loading/Data Fix
Files to replace
Copy these files into the matching project locations:
main.py -> project root
history.py -> project root
templates/dashboard.html
static/app.js
static/style.css
What this fixes
Historical candles are fetched concurrently instead of sequentially.
Each timeframe has isolated failure handling.
Analysis is cached for 8 seconds, so dashboard and scanner do not duplicate the same Delta requests.
/api/live?symbol=BTCUSD returns ticker + analysis in one request.
/api/debug-data?symbol=BTCUSD shows exactly how many candles arrived for every timeframe.
The dashboard shows an explicit API/data error instead of staying on Loading....
Important
The existing analysis.signal.generate_signal() engine is called unchanged.
After deployment, test:
/health
/api/debug-data?symbol=BTCUSD
/api/live?symbol=BTCUSD
/dashboard
If /api/debug-data shows 5m rows > 0 but another timeframe is 0, the dashboard can still produce the primary 5m analysis; the failed timeframe will be shown as UNKNOWN.
