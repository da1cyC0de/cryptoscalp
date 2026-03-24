"""
Technical Indicators Module untuk XAUUSD Scalp Signal
Pro-grade: Multi-timeframe analysis, candlestick patterns, support/resistance
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


def calculate_vwap(df: pd.DataFrame, period: int = 20) -> pd.Series:
    """Hitung Volume Weighted Average Price (rolling)"""
    typical = (df['High'] + df['Low'] + df['Close']) / 3
    vol = df['Volume'].replace(0, 1)
    vwap = (typical * vol).rolling(period).sum() / vol.rolling(period).sum()
    return vwap


def detect_support_resistance(df: pd.DataFrame, lookback: int = 50) -> dict:
    """Deteksi level support dan resistance dari pivot points"""
    recent = df.tail(lookback)
    highs = recent['High']
    lows = recent['Low']

    # Swing highs (resistance)
    resistance_levels = []
    for i in range(2, len(highs) - 2):
        if highs.iloc[i] > highs.iloc[i-1] and highs.iloc[i] > highs.iloc[i-2] and \
           highs.iloc[i] > highs.iloc[i+1] and highs.iloc[i] > highs.iloc[i+2]:
            resistance_levels.append(highs.iloc[i])

    # Swing lows (support)
    support_levels = []
    for i in range(2, len(lows) - 2):
        if lows.iloc[i] < lows.iloc[i-1] and lows.iloc[i] < lows.iloc[i-2] and \
           lows.iloc[i] < lows.iloc[i+1] and lows.iloc[i] < lows.iloc[i+2]:
            support_levels.append(lows.iloc[i])

    price = float(df['Close'].iloc[-1])

    # Nearest resistance above price
    resistances_above = sorted([r for r in resistance_levels if r > price])
    nearest_resistance = resistances_above[0] if resistances_above else price + 20

    # Nearest support below price
    supports_below = sorted([s for s in support_levels if s < price], reverse=True)
    nearest_support = supports_below[0] if supports_below else price - 20

    return {
        'nearest_resistance': round(float(nearest_resistance), 2),
        'nearest_support': round(float(nearest_support), 2),
        'resistance_count': len(resistances_above),
        'support_count': len(supports_below),
    }


def detect_candlestick_patterns(df: pd.DataFrame) -> dict:
    """Deteksi pola candlestick terakhir"""
    if len(df) < 3:
        return {'pattern': 'none', 'bias': 'neutral'}

    c = df.iloc[-1]  # Current candle
    p = df.iloc[-2]  # Previous candle

    body = c['Close'] - c['Open']
    body_abs = abs(body)
    upper_wick = c['High'] - max(c['Open'], c['Close'])
    lower_wick = min(c['Open'], c['Close']) - c['Low']
    candle_range = c['High'] - c['Low']

    prev_body = p['Close'] - p['Open']

    if candle_range == 0:
        return {'pattern': 'doji', 'bias': 'neutral'}

    # Doji
    if body_abs < candle_range * 0.1:
        return {'pattern': 'doji', 'bias': 'reversal'}

    # Hammer (bullish reversal di downtrend)
    if lower_wick > body_abs * 2 and upper_wick < body_abs * 0.5 and prev_body < 0:
        return {'pattern': 'hammer', 'bias': 'bullish'}

    # Shooting Star (bearish reversal di uptrend)
    if upper_wick > body_abs * 2 and lower_wick < body_abs * 0.5 and prev_body > 0:
        return {'pattern': 'shooting_star', 'bias': 'bearish'}

    # Bullish Engulfing
    if body > 0 and prev_body < 0 and c['Open'] <= p['Close'] and c['Close'] >= p['Open']:
        return {'pattern': 'bullish_engulfing', 'bias': 'bullish'}

    # Bearish Engulfing
    if body < 0 and prev_body > 0 and c['Open'] >= p['Close'] and c['Close'] <= p['Open']:
        return {'pattern': 'bearish_engulfing', 'bias': 'bearish'}

    # Strong momentum candle
    if body_abs > candle_range * 0.7:
        bias = 'bullish' if body > 0 else 'bearish'
        return {'pattern': 'momentum', 'bias': bias}

    return {'pattern': 'none', 'bias': 'neutral'}


def calculate_momentum_score(df: pd.DataFrame, lookback: int = 5) -> dict:
    """Hitung momentum score dari beberapa candle terakhir — BODY-WEIGHTED"""
    recent = df.tail(lookback)
    closes = recent['Close'].values
    opens = recent['Open'].values

    # Candle body weighted momentum (bukan cuma arah, tapi UKURAN)
    bullish_count = 0
    bearish_count = 0
    bullish_power = 0.0  # Total body size bullish
    bearish_power = 0.0  # Total body size bearish
    for i in range(len(closes)):
        body = closes[i] - opens[i]
        if body > 0:
            bullish_count += 1
            bullish_power += abs(body)
        elif body < 0:
            bearish_count += 1
            bearish_power += abs(body)

    # Net movement
    net_move = closes[-1] - closes[0]

    # Volume trend (increasing = kuat)
    vols = recent['Volume'].values
    vol_increasing = vols[-1] > np.mean(vols[:-1]) if len(vols) > 1 and np.mean(vols[:-1]) > 0 else False

    # Body dominance: siapa yang menang body-nya
    total_power = bullish_power + bearish_power
    if total_power > 0:
        body_ratio = (bullish_power - bearish_power) / total_power  # -1 to +1
    else:
        body_ratio = 0.0

    return {
        'bullish_candles': bullish_count,
        'bearish_candles': bearish_count,
        'bullish_power': round(float(bullish_power), 2),
        'bearish_power': round(float(bearish_power), 2),
        'body_ratio': round(float(body_ratio), 3),  # -1 full bear, +1 full bull
        'net_move': round(float(net_move), 2),
        'vol_increasing': vol_increasing,
        'direction': 'bullish' if net_move > 0 else 'bearish' if net_move < 0 else 'flat',
    }


def calculate_price_structure(df: pd.DataFrame, lookback: int = 20) -> dict:
    """
    Analisis price structure: Higher Highs/Higher Lows vs Lower Highs/Lower Lows.
    Ini yang PERTAMA KALI dilihat trader saat buka chart.
    """
    if len(df) < lookback:
        return {'structure': 'unknown', 'hh_count': 0, 'll_count': 0, 'lh_count': 0, 'hl_count': 0}

    recent = df.tail(lookback)
    highs = recent['High'].values
    lows = recent['Low'].values

    # Detect swing points (mini pivots, setiap 3-5 candle)
    swing_highs = []
    swing_lows = []
    step = 4  # Group every 4 candles

    for i in range(0, len(highs) - step + 1, step):
        chunk_high = max(highs[i:i + step])
        chunk_low = min(lows[i:i + step])
        swing_highs.append(chunk_high)
        swing_lows.append(chunk_low)

    if len(swing_highs) < 2:
        return {'structure': 'unknown', 'hh_count': 0, 'll_count': 0, 'lh_count': 0, 'hl_count': 0}

    # Count HH, HL, LH, LL
    hh = lh = hl = ll = 0
    for i in range(1, len(swing_highs)):
        if swing_highs[i] > swing_highs[i - 1]:
            hh += 1
        else:
            lh += 1
        if swing_lows[i] > swing_lows[i - 1]:
            hl += 1
        else:
            ll += 1

    # Determine structure
    total = hh + lh
    if total == 0:
        structure = 'unknown'
    elif hh > lh and hl > ll:
        structure = 'uptrend'       # HH + HL = classic uptrend
    elif lh > hh and ll > hl:
        structure = 'downtrend'     # LH + LL = classic downtrend
    elif lh > hh and hl >= ll:
        structure = 'distribution'  # LH but HL = topping out
    elif hh >= lh and ll > hl:
        structure = 'accumulation'  # HH but LL = bottoming out
    else:
        structure = 'ranging'

    return {
        'structure': structure,
        'hh_count': hh,
        'll_count': ll,
        'lh_count': lh,
        'hl_count': hl,
    }


def calculate_htf_trend(df_htf: pd.DataFrame) -> dict:
    """
    Hitung trend dari higher timeframe (1h/4h).
    Simplified: EMA9/21 + MACD + recent direction.
    """
    if df_htf is None or df_htf.empty or len(df_htf) < 30:
        return {'htf_trend': 'unknown', 'htf_score': 0}

    close = df_htf['Close']

    # EMA
    ema9 = calculate_ema(close, 9).iloc[-1]
    ema21 = calculate_ema(close, 21).iloc[-1]
    price = close.iloc[-1]

    # MACD
    macd_line, signal_line, histogram = calculate_macd(close)
    macd_hist = histogram.dropna().iloc[-1] if not histogram.dropna().empty else 0

    # Last 5 candle direction on HTF
    last5 = close.tail(5).values
    htf_net = last5[-1] - last5[0]

    score = 0
    # EMA positioning (bobot 3)
    if price > ema9 > ema21:
        score += 3
    elif price > ema9:
        score += 1
    elif price < ema9 < ema21:
        score -= 3
    elif price < ema9:
        score -= 1

    # MACD (bobot 2)
    if macd_hist > 0:
        score += 2
    elif macd_hist < 0:
        score -= 2

    # HTF direction (bobot 2)
    atr = calculate_atr(df_htf['High'], df_htf['Low'], close, 14)
    atr_val = atr.dropna().iloc[-1] if not atr.dropna().empty else 10
    if htf_net > atr_val * 0.3:
        score += 2
    elif htf_net < -atr_val * 0.3:
        score -= 2

    if score >= 4:
        trend = 'BULLISH'
    elif score >= 2:
        trend = 'LEAN_BULLISH'
    elif score <= -4:
        trend = 'BEARISH'
    elif score <= -2:
        trend = 'LEAN_BEARISH'
    else:
        trend = 'NEUTRAL'

    return {'htf_trend': trend, 'htf_score': score}


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
    ema_200 = calculate_ema(close, 200)

    # Stochastic
    stoch_k, stoch_d = calculate_stochastic(high, low, close)

    # VWAP
    vwap = calculate_vwap(df)

    # Support/Resistance
    sr = detect_support_resistance(df)

    # Candlestick
    candle = detect_candlestick_patterns(df)

    # Momentum (body-weighted)
    momentum = calculate_momentum_score(df)

    # Price Structure (HH/HL/LH/LL)
    price_struct = calculate_price_structure(df)

    # Trend determination: EMA alignment
    ema9_val = ema_9.dropna().iloc[-1] if not ema_9.dropna().empty else 0
    ema21_val = ema_21.dropna().iloc[-1] if not ema_21.dropna().empty else 0
    ema50_val = ema_50.dropna().iloc[-1] if not ema_50.dropna().empty else 0
    ema200_val = ema_200.dropna().iloc[-1] if not ema_200.dropna().empty else 0
    price_val = close.iloc[-1]

    if ema9_val > ema21_val > ema50_val and price_val > ema50_val:
        ema_trend = 'strong_bullish'
    elif ema9_val > ema21_val and price_val > ema21_val:
        ema_trend = 'bullish'
    elif ema9_val < ema21_val < ema50_val and price_val < ema50_val:
        ema_trend = 'strong_bearish'
    elif ema9_val < ema21_val and price_val < ema21_val:
        ema_trend = 'bearish'
    else:
        ema_trend = 'mixed'

    # RSI divergence check (last 10 candles)
    rsi_div = 'none'
    if len(close) >= 10 and len(rsi.dropna()) >= 10:
        price_10 = close.iloc[-10:]
        rsi_10 = rsi.dropna().iloc[-10:]
        # Bearish divergence: price making higher high but RSI making lower high
        if price_10.iloc[-1] > price_10.iloc[-5] and rsi_10.iloc[-1] < rsi_10.iloc[-5]:
            rsi_div = 'bearish'
        # Bullish divergence: price making lower low but RSI making higher low
        elif price_10.iloc[-1] < price_10.iloc[-5] and rsi_10.iloc[-1] > rsi_10.iloc[-5]:
            rsi_div = 'bullish'

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
        'ema_9': round(ema9_val, 2),
        'ema_21': round(ema21_val, 2),
        'ema_50': round(ema50_val, 2),
        'ema_200': round(ema200_val, 2),
        'stoch_k': round(stoch_k.dropna().iloc[-1], 2) if not stoch_k.dropna().empty else 50,
        'stoch_d': round(stoch_d.dropna().iloc[-1], 2) if not stoch_d.dropna().empty else 50,
        'vwap': round(vwap.dropna().iloc[-1], 2) if not vwap.dropna().empty else 0,
        'nearest_resistance': sr['nearest_resistance'],
        'nearest_support': sr['nearest_support'],
        'candle_pattern': candle['pattern'],
        'candle_bias': candle['bias'],
        'momentum_dir': momentum['direction'],
        'momentum_net': momentum['net_move'],
        'momentum_vol_up': momentum['vol_increasing'],
        'bullish_candles': momentum['bullish_candles'],
        'bearish_candles': momentum['bearish_candles'],
        'body_ratio': momentum['body_ratio'],
        'bullish_power': momentum['bullish_power'],
        'bearish_power': momentum['bearish_power'],
        'price_structure': price_struct['structure'],
        'hh_count': price_struct['hh_count'],
        'll_count': price_struct['ll_count'],
        'lh_count': price_struct['lh_count'],
        'hl_count': price_struct['hl_count'],
        'ema_trend': ema_trend,
        'rsi_divergence': rsi_div,
    }

    return latest
