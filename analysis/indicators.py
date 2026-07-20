import pandas as pd


def sma(series, period):
    return series.rolling(period).mean()


def ema(series, period):
    return series.ewm(span=period, adjust=False).mean()


def ema9(series):
    return ema(series, 9)


def ema20(series):
    return ema(series, 20)


def ema50(series):
    return ema(series, 50)


def ema200(series):
    return ema(series, 200)


def rsi(series, period=14):
    delta = series.diff()

    gain = delta.where(delta > 0, 0).rolling(period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(period).mean()

    rs = gain / loss

    return 100 - (100 / (1 + rs))


def macd(series):
    ema12 = ema(series, 12)
    ema26 = ema(series, 26)

    macd_line = ema12 - ema26
    signal_line = ema(macd_line, 9)
    histogram = macd_line - signal_line

    return macd_line, signal_line, histogram


def atr(high, low, close, period=14):
    tr = pd.concat([
        high - low,
        (high - close.shift()).abs(),
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)

    return tr.rolling(period).mean()


def trend_strength(close):
    e9 = ema(close, 9).iloc[-1]
    e50 = ema(close, 50).iloc[-1]
    e200 = ema(close, 200).iloc[-1]

    if e9 > e50 > e200:
        return "STRONG_BULL"

    if e9 > e50:
        return "BULL"

    if e9 < e50 < e200:
        return "STRONG_BEAR"

    if e9 < e50:
        return "BEAR"

    return "SIDEWAYS"
