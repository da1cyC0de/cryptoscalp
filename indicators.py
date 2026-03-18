"""
Technical Indicators Module untuk XAUUSD Scalp Signal
Menghitung RSI, ADX, ATR, Bollinger Bands, dan indikator lainnya
"""

import pandas as pd
import numpy as np


def calculate_rsi(data: pd.Series, period: int = 14) -> pd.Series:
    """Hitung Relative Strength Index"""
    delta = data.diff()
    gain = delta.where(delta > 0, 0.0)
    loss = -delta.where(delta < 0, 0.0)

    avg_gain = gain.rolling(window=period, min_periods=period).mean()
    avg_loss = loss.rolling(window=period, min_periods=period).mean()

    # Smoothed averages (Wilder's method)
    for i in range(period, len(data)):
        avg_gain.iloc[i] = (avg_gain.iloc[i - 1] * (period - 1) + gain.iloc[i]) / period
        avg_loss.iloc[i] = (avg_loss.iloc[i - 1] * (period - 1) + loss.iloc[i]) / period

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi


def calculate_atr(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14) -> pd.Series:
    """Hitung Average True Range"""
    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
    atr = tr.rolling(window=period, min_periods=period).mean()

    # Wilder's smoothing
    for i in range(period, len(close)):
        atr.iloc[i] = (atr.iloc[i - 1] * (period - 1) + tr.iloc[i]) / period

    return atr


def calculate_adx(high: pd.Series, low: pd.Series, close: pd.Series, period: int = 14):
    """Hitung Average Directional Index dengan Wilder's smoothing penuh"""
    plus_dm = high.diff()
    minus_dm = -low.diff()

    plus_dm = plus_dm.where((plus_dm > minus_dm) & (plus_dm > 0), 0.0)
    minus_dm = minus_dm.where((minus_dm > plus_dm) & (minus_dm > 0), 0.0)

    tr1 = high - low
    tr2 = abs(high - close.shift(1))
    tr3 = abs(low - close.shift(1))
    tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)

    # Wilder's smoothing untuk ATR, +DM, -DM
    atr_smooth = tr.rolling(window=period, min_periods=period).sum()
    plus_dm_smooth = plus_dm.rolling(window=period, min_periods=period).sum()
    minus_dm_smooth = minus_dm.rolling(window=period, min_periods=period).sum()

    for i in range(period, len(close)):
        atr_smooth.iloc[i] = atr_smooth.iloc[i - 1] - (atr_smooth.iloc[i - 1] / period) + tr.iloc[i]
        plus_dm_smooth.iloc[i] = plus_dm_smooth.iloc[i - 1] - (plus_dm_smooth.iloc[i - 1] / period) + plus_dm.iloc[i]
        minus_dm_smooth.iloc[i] = minus_dm_smooth.iloc[i - 1] - (minus_dm_smooth.iloc[i - 1] / period) + minus_dm.iloc[i]

    plus_di = 100 * (plus_dm_smooth / atr_smooth)
    minus_di = 100 * (minus_dm_smooth / atr_smooth)

    dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di)

    # ADX: Wilder's smoothing pada DX
    adx = dx.copy()
    first_adx_idx = period * 2 - 1
    if first_adx_idx < len(dx):
        adx.iloc[first_adx_idx] = dx.iloc[period:period * 2].mean()
        for i in range(first_adx_idx + 1, len(dx)):
            adx.iloc[i] = (adx.iloc[i - 1] * (period - 1) + dx.iloc[i]) / period
        # Set sebelum first_adx_idx ke NaN
        adx.iloc[:first_adx_idx] = np.nan

    return adx, plus_di, minus_di


def calculate_bollinger_bands(data: pd.Series, period: int = 20, std_dev: float = 2.0):
    """Hitung Bollinger Bands"""
    middle = data.rolling(window=period).mean()
    std = data.rolling(window=period).std()
    upper = middle + (std_dev * std)
    lower = middle - (std_dev * std)
    bb_width = (upper - lower) / middle
    return upper, middle, lower, bb_width


def calculate_ema(data: pd.Series, period: int) -> pd.Series:
    """Hitung Exponential Moving Average"""
    return data.ewm(span=period, adjust=False).mean()


def calculate_macd(data: pd.Series, fast: int = 12, slow: int = 26, signal: int = 9):
    """Hitung MACD"""
    ema_fast = calculate_ema(data, fast)
    ema_slow = calculate_ema(data, slow)
    macd_line = ema_fast - ema_slow
    signal_line = calculate_ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def calculate_stochastic(high: pd.Series, low: pd.Series, close: pd.Series,
                         k_period: int = 14, d_period: int = 3):
    """Hitung Stochastic Oscillator"""
    lowest_low = low.rolling(window=k_period).min()
    highest_high = high.rolling(window=k_period).max()
    k = 100 * (close - lowest_low) / (highest_high - lowest_low)
    d = k.rolling(window=d_period).mean()
    return k, d


def calculate_all_indicators(df: pd.DataFrame) -> dict:
    """
    Hitung semua indikator teknikal dari dataframe OHLCV.
    Returns dictionary dengan semua nilai indikator terbaru.
    """
    close = df['Close']
    high = df['High']
    low = df['Low']

    # RSI
    rsi = calculate_rsi(close, 14)

    # ADX
    adx, plus_di, minus_di = calculate_adx(high, low, close, 14)

    # ATR
    atr = calculate_atr(high, low, close, 14)

    # Bollinger Bands
    bb_upper, bb_middle, bb_lower, bb_width = calculate_bollinger_bands(close, 20, 2.0)

    # MACD
    macd_line, signal_line, histogram = calculate_macd(close)

    # EMA
    ema_9 = calculate_ema(close, 9)
    ema_21 = calculate_ema(close, 21)
    ema_50 = calculate_ema(close, 50)

    # Stochastic
    stoch_k, stoch_d = calculate_stochastic(high, low, close)

    # Ambil nilai terbaru (non-NaN)
    latest = {
        'price': close.iloc[-1],
        'high': high.iloc[-1],
        'low': low.iloc[-1],
        'rsi': round(rsi.dropna().iloc[-1], 2) if not rsi.dropna().empty else 50.0,
        'adx': round(adx.dropna().iloc[-1], 2) if not adx.dropna().empty else 20.0,
        'plus_di': round(plus_di.dropna().iloc[-1], 2) if not plus_di.dropna().empty else 0,
        'minus_di': round(minus_di.dropna().iloc[-1], 2) if not minus_di.dropna().empty else 0,
        'atr': round(atr.dropna().iloc[-1], 2) if not atr.dropna().empty else 0,
        'bb_upper': round(bb_upper.dropna().iloc[-1], 2) if not bb_upper.dropna().empty else 0,
        'bb_middle': round(bb_middle.dropna().iloc[-1], 2) if not bb_middle.dropna().empty else 0,
        'bb_lower': round(bb_lower.dropna().iloc[-1], 2) if not bb_lower.dropna().empty else 0,
        'bb_width': round(bb_width.dropna().iloc[-1], 4) if not bb_width.dropna().empty else 0,
        'macd': round(macd_line.dropna().iloc[-1], 2) if not macd_line.dropna().empty else 0,
        'macd_signal': round(signal_line.dropna().iloc[-1], 2) if not signal_line.dropna().empty else 0,
        'macd_histogram': round(histogram.dropna().iloc[-1], 2) if not histogram.dropna().empty else 0,
        'ema_9': round(ema_9.dropna().iloc[-1], 2) if not ema_9.dropna().empty else 0,
        'ema_21': round(ema_21.dropna().iloc[-1], 2) if not ema_21.dropna().empty else 0,
        'ema_50': round(ema_50.dropna().iloc[-1], 2) if not ema_50.dropna().empty else 0,
        'stoch_k': round(stoch_k.dropna().iloc[-1], 2) if not stoch_k.dropna().empty else 50,
        'stoch_d': round(stoch_d.dropna().iloc[-1], 2) if not stoch_d.dropna().empty else 50,
    }

    return latest
