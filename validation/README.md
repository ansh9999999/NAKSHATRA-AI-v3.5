NAKSHATRA Validation Pack v1.0
Put backtest.py and test_decision_engine.py inside a validation/ folder.
Decision test: python validation/test_decision_engine.py
Historical backtest: python -m validation.backtest data/btc_5m.csv --symbol BTCUSD --horizons 3,6,12 --output results/btc
Horizons are 5-minute candles: 3=15m, 6=30m, 12=60m.
Outputs:
signals CSV: every signal and forward result
summary CSV: trades, wins, win rate and average return
confidence CSV: empirical performance by confidence bucket
A displayed confidence percentage is NOT assumed to be a true probability; the confidence report is what we use to calibrate it.
