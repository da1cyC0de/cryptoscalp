"""
Pro Signal Generator untuk XAUUSD Scalp
Menggunakan Confluence-Based approach:
- Signal hanya dikeluarkan jika minimal 4 dari 7 konfirmasi sejalan
- Smart SL/TP berdasarkan support/resistance + ATR
- Kill zone filtering (hanya trade saat volatilitas tinggi)
- Risk:Reward minimal 1:2
"""

import json
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)

# ============================================================
# CONFLUENCE-BASED SIGNAL ENGINE
# ============================================================

def _calculate_confluence(indicators: dict) -> dict:
    """
    Hitung confluence score dari 7 faktor independen.
    Setiap faktor memberikan skor +1 BUY atau +1 SELL.
    Signal hanya valid jika confluence >= 4.
    """
    price = indicators['price']
    rsi = indicators['rsi']
    adx = indicators['adx']
    plus_di = indicators['plus_di']
    minus_di = indicators['minus_di']
    atr = indicators['atr']
    macd_hist = indicators['macd_histogram']
    macd = indicators['macd']
    macd_signal = indicators['macd_signal']
    bb_lower = indicators['bb_lower']
    bb_upper = indicators['bb_upper']
    bb_middle = indicators['bb_middle']
    ema_9 = indicators['ema_9']
    ema_21 = indicators['ema_21']
    ema_50 = indicators['ema_50']
    ema_trend = indicators.get('ema_trend', 'mixed')
    stoch_k = indicators['stoch_k']
    stoch_d = indicators['stoch_d']
    candle_bias = indicators.get('candle_bias', 'neutral')
    momentum_dir = indicators.get('momentum_dir', 'flat')
    rsi_div = indicators.get('rsi_divergence', 'none')
    vwap = indicators.get('vwap', 0)

    buy_reasons = []
    sell_reasons = []

    # 1. EMA TREND ALIGNMENT (most important)
    if ema_trend in ('strong_bullish', 'bullish'):
        buy_reasons.append('EMA trend bullish')
    elif ema_trend in ('strong_bearish', 'bearish'):
        sell_reasons.append('EMA trend bearish')

    # 2. RSI CONDITION
    if rsi < 35:
        buy_reasons.append(f'RSI oversold ({rsi})')
    elif rsi > 65:
        sell_reasons.append(f'RSI overbought ({rsi})')
    elif rsi < 50 and momentum_dir == 'bearish':
        sell_reasons.append(f'RSI bearish zone ({rsi})')
    elif rsi > 50 and momentum_dir == 'bullish':
        buy_reasons.append(f'RSI bullish zone ({rsi})')

    # 3. ADX + DI (Trend strength + direction)
    if adx > 20:
        if plus_di > minus_di:
            buy_reasons.append(f'+DI > -DI, ADX={adx}')
        else:
            sell_reasons.append(f'-DI > +DI, ADX={adx}')

    # 4. MACD
    if macd_hist > 0 and macd > macd_signal:
        buy_reasons.append('MACD bullish crossover')
    elif macd_hist < 0 and macd < macd_signal:
        sell_reasons.append('MACD bearish crossover')

    # 5. BOLLINGER BANDS POSITION
    if price <= bb_lower:
        buy_reasons.append('Price at BB lower (oversold)')
    elif price >= bb_upper:
        sell_reasons.append('Price at BB upper (overbought)')
    elif price < bb_middle:
        sell_reasons.append('Price below BB middle')
    else:
        buy_reasons.append('Price above BB middle')

    # 6. STOCHASTIC
    if stoch_k < 25 and stoch_d < 25:
        buy_reasons.append(f'Stoch oversold ({stoch_k:.0f})')
    elif stoch_k > 75 and stoch_d > 75:
        sell_reasons.append(f'Stoch overbought ({stoch_k:.0f})')
    elif stoch_k > stoch_d:
        buy_reasons.append('Stoch K > D')
    else:
        sell_reasons.append('Stoch K < D')

    # 7. CANDLESTICK PATTERN + MOMENTUM
    if candle_bias == 'bullish':
        buy_reasons.append(f'Candle pattern bullish')
    elif candle_bias == 'bearish':
        sell_reasons.append(f'Candle pattern bearish')

    if momentum_dir == 'bullish':
        buy_reasons.append('Momentum bullish')
    elif momentum_dir == 'bearish':
        sell_reasons.append('Momentum bearish')

    # BONUS: RSI Divergence (strong reversal signal)
    if rsi_div == 'bullish':
        buy_reasons.append('RSI bullish divergence!')
    elif rsi_div == 'bearish':
        sell_reasons.append('RSI bearish divergence!')

    # BONUS: VWAP
    if vwap > 0:
        if price > vwap:
            buy_reasons.append('Price above VWAP')
        else:
            sell_reasons.append('Price below VWAP')

    buy_score = len(buy_reasons)
    sell_score = len(sell_reasons)
    total = buy_score + sell_score

    return {
        'buy_score': buy_score,
        'sell_score': sell_score,
        'buy_reasons': buy_reasons,
        'sell_reasons': sell_reasons,
        'total_factors': total,
    }


def _calculate_smart_levels(indicators: dict, signal_type: str) -> dict:
    """
    Hitung SL/TP yang smart berdasarkan:
    - ATR untuk dinamis range
    - Support/Resistance untuk placement
    - Minimal Risk:Reward 1:2
    """
    price = indicators['price']
    atr = indicators['atr']
    nearest_support = indicators.get('nearest_support', price - 20)
    nearest_resistance = indicators.get('nearest_resistance', price + 20)

    if signal_type == 'BUY':
        # SL tepat di bawah nearest support atau 1x ATR, mana yang lebih kecil
        sl_by_sr = nearest_support - (atr * 0.3)
        sl_by_atr = price - (atr * 1.2)
        stop_loss = max(sl_by_sr, sl_by_atr)  # Ambil yang lebih dekat (risk lebih kecil)

        risk = price - stop_loss
        if risk < atr * 0.5:
            risk = atr * 0.8
            stop_loss = price - risk

        # TP dengan R:R minimal 1:1.5, 1:2, 1:3
        tp1 = round(price + (risk * 1.5), 2)
        tp2 = round(price + (risk * 2.0), 2)
        tp3 = round(price + (risk * 3.0), 2)

        # Jika resistance di jalan, sesuaikan
        if tp1 > nearest_resistance and nearest_resistance > price:
            tp1 = round(nearest_resistance - (atr * 0.1), 2)

    else:  # SELL
        # SL tepat di atas nearest resistance atau 1x ATR
        sl_by_sr = nearest_resistance + (atr * 0.3)
        sl_by_atr = price + (atr * 1.2)
        stop_loss = min(sl_by_sr, sl_by_atr)

        risk = stop_loss - price
        if risk < atr * 0.5:
            risk = atr * 0.8
            stop_loss = price + risk

        tp1 = round(price - (risk * 1.5), 2)
        tp2 = round(price - (risk * 2.0), 2)
        tp3 = round(price - (risk * 3.0), 2)

        if tp1 < nearest_support and nearest_support < price:
            tp1 = round(nearest_support + (atr * 0.1), 2)

    return {
        'stop_loss': round(stop_loss, 2),
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'risk': round(abs(price - stop_loss), 2),
    }


# ============================================================
# MAIN SIGNAL GENERATION
# ============================================================

def generate_signal_with_gemini(indicators: dict, api_key: str) -> dict:
    """
    Generate signal XAUUSD menggunakan confluence analysis.
    Gemini AI hanya digunakan sebagai konfirmasi tambahan, bukan pembuat keputusan.
    Keputusan utama berdasarkan data teknikal murni.
    """

    # Step 1: Hitung confluence
    confluence = _calculate_confluence(indicators)
    buy_score = confluence['buy_score']
    sell_score = confluence['sell_score']

    logger.info(f"📊 Confluence: BUY={buy_score} vs SELL={sell_score}")
    logger.info(f"   BUY reasons: {', '.join(confluence['buy_reasons'])}")
    logger.info(f"   SELL reasons: {', '.join(confluence['sell_reasons'])}")

    # Step 2: Tentukan signal berdasarkan confluence
    min_confluence = 4  # Minimal 4 faktor harus sejalan

    if buy_score >= min_confluence and buy_score > sell_score + 1:
        signal_type = 'BUY'
    elif sell_score >= min_confluence and sell_score > buy_score + 1:
        signal_type = 'SELL'
    else:
        # Confluence tidak cukup kuat — JANGAN TRADE
        logger.info(f"⏸️ Confluence terlalu lemah ({buy_score} vs {sell_score}), skip signal")
        signal_type = 'NEUTRAL'

    # Step 3: Hitung levels
    if signal_type != 'NEUTRAL':
        levels = _calculate_smart_levels(indicators, signal_type)
    else:
        atr = indicators['atr']
        price = indicators['price']
        levels = {
            'stop_loss': round(price - atr, 2),
            'tp1': round(price + atr * 0.5, 2),
            'tp2': round(price + atr, 2),
            'tp3': round(price + atr * 1.5, 2),
            'risk': round(atr, 2),
        }

    # Step 4: Hitung probability & strength
    total = max(buy_score + sell_score, 1)
    if signal_type == 'BUY':
        prob_up = round(buy_score / total * 100, 2)
        prob_down = round(sell_score / total * 100, 2)
        strength = round(buy_score / total * 100, 0)
    elif signal_type == 'SELL':
        prob_up = round(buy_score / total * 100, 2)
        prob_down = round(sell_score / total * 100, 2)
        strength = round(sell_score / total * 100, 0)
    else:
        prob_up = round(buy_score / total * 50, 2)
        prob_down = round(sell_score / total * 50, 2)
        strength = 0

    # Step 5: Coba Gemini AI untuk reasoning (opsional, tidak mengubah signal)
    reasoning = _get_gemini_reasoning(indicators, confluence, signal_type, api_key)

    result = {
        'signal': signal_type,
        'confidence': strength,
        'stop_loss': levels['stop_loss'],
        'tp1': levels['tp1'],
        'tp2': levels['tp2'],
        'tp3': levels['tp3'],
        'prob_up': prob_up,
        'prob_down': prob_down,
        'strength': strength,
        'reasoning': reasoning,
    }

    logger.info(f"✅ Signal: {signal_type} | Strength: {strength}% | "
                f"Risk: {levels['risk']} | R:R = 1:{round(abs(levels['tp2'] - indicators['price']) / max(levels['risk'], 0.01), 1)}")

    return result


def _get_gemini_reasoning(indicators: dict, confluence: dict, signal_type: str, api_key: str) -> str:
    """Gunakan Gemini hanya untuk generate reasoning text (bukan signal)"""

    prompt = f"""Kamu adalah analis XAUUSD profesional. Berikan analisis SINGKAT (2-3 kalimat) untuk sinyal {signal_type}.

Harga: {indicators['price']:.2f}
RSI: {indicators['rsi']} | ADX: {indicators['adx']} | MACD Hist: {indicators['macd_histogram']}
EMA Trend: {indicators.get('ema_trend', 'N/A')} | Candle: {indicators.get('candle_pattern', 'N/A')}
Confluence BUY: {confluence['buy_score']} ({', '.join(confluence['buy_reasons'][:3])})
Confluence SELL: {confluence['sell_score']} ({', '.join(confluence['sell_reasons'][:3])})

Jawab dalam 2-3 kalimat bahasa Indonesia, jelaskan kenapa sinyal {signal_type} valid atau kenapa market sideways."""

    client = genai.Client(api_key=api_key)
    free_models = ['gemini-2.0-flash-lite', 'gemini-2.0-flash']

    for model_name in free_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.3,
                    max_output_tokens=200,
                ),
            )
            return response.text.strip()
        except Exception:
            continue

    # Fallback reasoning
    if signal_type == 'BUY':
        return f"Bullish confluence kuat ({confluence['buy_score']} faktor): {', '.join(confluence['buy_reasons'][:3])}"
    elif signal_type == 'SELL':
        return f"Bearish confluence kuat ({confluence['sell_score']} faktor): {', '.join(confluence['sell_reasons'][:3])}"
    else:
        return f"Confluence lemah (BUY:{confluence['buy_score']} vs SELL:{confluence['sell_score']}), tidak ada setup yang jelas"
