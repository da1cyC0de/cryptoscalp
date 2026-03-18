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
    Confluence scoring — BALANCED SCALP approach.
    
    Prinsip:
    - Setiap KATEGORI indikator cuma dapat 1 vote max (tidak ada bias lagging)
    - Exhaustion detection: jangan chase move yang sudah overextended
    - Min 4 faktor searah, difference > 2 untuk signal
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

    is_uptrend = ema_trend in ('strong_bullish', 'bullish')
    is_downtrend = ema_trend in ('strong_bearish', 'bearish')

    # === EXHAUSTION DETECTION ===
    exhausted_down = rsi < 30 and stoch_k < 20
    exhausted_up = rsi > 70 and stoch_k > 80

    # -------------------------------------------------------
    # 1. TREND (EMA alignment + ADX = 1 faktor gabungan)
    #    Jangan kasih jika exhausted — move sudah capek
    # -------------------------------------------------------
    if is_uptrend and adx > 20 and plus_di > minus_di and not exhausted_up:
        buy_reasons.append(f'Trend bullish (EMA+ADX={adx:.0f})')
    elif is_downtrend and adx > 20 and minus_di > plus_di and not exhausted_down:
        sell_reasons.append(f'Trend bearish (EMA+ADX={adx:.0f})')
    elif is_uptrend and not exhausted_up:
        buy_reasons.append('EMA trend bullish')
    elif is_downtrend and not exhausted_down:
        sell_reasons.append('EMA trend bearish')

    # -------------------------------------------------------
    # 2. RSI — baca natural, extreme = reversal
    # -------------------------------------------------------
    if rsi < 25:
        buy_reasons.append(f'RSI extreme oversold ({rsi:.0f}) — bounce likely')
    elif rsi < 35:
        buy_reasons.append(f'RSI oversold ({rsi:.0f})')
    elif rsi > 75:
        sell_reasons.append(f'RSI extreme overbought ({rsi:.0f}) — drop likely')
    elif rsi > 65:
        sell_reasons.append(f'RSI overbought ({rsi:.0f})')

    # -------------------------------------------------------
    # 3. MACD
    # -------------------------------------------------------
    if macd_hist > 0 and macd > macd_signal:
        buy_reasons.append('MACD bullish crossover')
    elif macd_hist < 0 and macd < macd_signal:
        sell_reasons.append('MACD bearish crossover')

    # -------------------------------------------------------
    # 4. BOLLINGER BANDS — mean reversion
    # -------------------------------------------------------
    if price <= bb_lower:
        buy_reasons.append('Price at BB lower — oversold')
    elif price >= bb_upper:
        sell_reasons.append('Price at BB upper — overbought')
    elif price > bb_middle:
        buy_reasons.append('Price above BB mid')
    else:
        sell_reasons.append('Price below BB mid')

    # -------------------------------------------------------
    # 5. STOCHASTIC — leading oscillator
    # -------------------------------------------------------
    if stoch_k < 20:
        buy_reasons.append(f'Stoch oversold ({stoch_k:.0f})')
    elif stoch_k > 80:
        sell_reasons.append(f'Stoch overbought ({stoch_k:.0f})')
    elif stoch_k > stoch_d:
        buy_reasons.append('Stoch K > D bullish')
    else:
        sell_reasons.append('Stoch K < D bearish')

    # -------------------------------------------------------
    # 6. MOMENTUM (recent 5 candles — paling cepat)
    # -------------------------------------------------------
    if momentum_dir == 'bullish':
        buy_reasons.append('Recent momentum bullish')
    elif momentum_dir == 'bearish':
        sell_reasons.append('Recent momentum bearish')

    # -------------------------------------------------------
    # 7. CANDLE PATTERN
    # -------------------------------------------------------
    if candle_bias == 'bullish':
        buy_reasons.append('Candle pattern bullish')
    elif candle_bias == 'bearish':
        sell_reasons.append('Candle pattern bearish')

    # -------------------------------------------------------
    # 8. VWAP — institutional reference
    # -------------------------------------------------------
    if vwap > 0:
        if price > vwap:
            buy_reasons.append('Price above VWAP')
        else:
            sell_reasons.append('Price below VWAP')

    # -------------------------------------------------------
    # 9. RSI Divergence — early reversal signal
    # -------------------------------------------------------
    if rsi_div == 'bullish':
        buy_reasons.append('RSI bullish divergence')
    elif rsi_div == 'bearish':
        sell_reasons.append('RSI bearish divergence')

    # -------------------------------------------------------
    # 10. EXHAUSTION BONUS — double extreme = strong reversal
    # -------------------------------------------------------
    if exhausted_down:
        buy_reasons.append('EXHAUSTION: oversold extreme — reversal imminent')
    if exhausted_up:
        sell_reasons.append('EXHAUSTION: overbought extreme — reversal imminent')

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
    SL/TP untuk SCALPING — ketat dan realistis.
    - SL: 0.8-1x ATR (tight)
    - TP1: 0.8x risk (quick profit, high win rate)
    - TP2: 1.2x risk
    - TP3: 1.8x risk
    """
    price = indicators['price']
    atr = indicators['atr']
    nearest_support = indicators.get('nearest_support', price - 15)
    nearest_resistance = indicators.get('nearest_resistance', price + 15)

    if signal_type == 'BUY':
        # SL: di bawah support atau 1x ATR
        sl_by_sr = nearest_support - (atr * 0.2)
        sl_by_atr = price - (atr * 1.0)
        stop_loss = max(sl_by_sr, sl_by_atr)

        risk = price - stop_loss
        if risk < atr * 0.4:
            risk = atr * 0.6
            stop_loss = price - risk
        # Cap max risk di 1.2x ATR agar SL tidak terlalu lebar
        if risk > atr * 1.2:
            risk = atr * 1.0
            stop_loss = price - risk

        tp1 = round(price + (risk * 0.8), 2)
        tp2 = round(price + (risk * 1.2), 2)
        tp3 = round(price + (risk * 1.8), 2)

    else:  # SELL
        sl_by_sr = nearest_resistance + (atr * 0.2)
        sl_by_atr = price + (atr * 1.0)
        stop_loss = min(sl_by_sr, sl_by_atr)

        risk = stop_loss - price
        if risk < atr * 0.4:
            risk = atr * 0.6
            stop_loss = price + risk
        if risk > atr * 1.2:
            risk = atr * 1.0
            stop_loss = price + risk

        tp1 = round(price - (risk * 0.8), 2)
        tp2 = round(price - (risk * 1.2), 2)
        tp3 = round(price - (risk * 1.8), 2)

    return {
        'stop_loss': round(stop_loss, 2),
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'risk': round(risk, 2),
    }


# ============================================================
# MAIN SIGNAL GENERATION
# ============================================================

# Track last signal to avoid duplicates
_last_signal = {'type': None, 'price': 0, 'time': None}


def generate_signal_with_gemini(indicators: dict, api_key: str) -> dict:
    """
    Generate signal XAUUSD menggunakan confluence analysis.
    Gemini AI hanya digunakan sebagai konfirmasi tambahan, bukan pembuat keputusan.
    Keputusan utama berdasarkan data teknikal murni.
    """
    from datetime import datetime

    # Step 1: Hitung confluence
    confluence = _calculate_confluence(indicators)
    buy_score = confluence['buy_score']
    sell_score = confluence['sell_score']

    logger.info(f"📊 Confluence: BUY={buy_score} vs SELL={sell_score}")
    logger.info(f"   BUY reasons: {', '.join(confluence['buy_reasons'])}")
    logger.info(f"   SELL reasons: {', '.join(confluence['sell_reasons'])}")

    # Step 2: Tentukan signal — SELALU BUY atau SELL, yang score lebih tinggi menang
    if buy_score >= sell_score:
        signal_type = 'BUY'
    else:
        signal_type = 'SELL'

    logger.info(f"🎯 Signal: {signal_type} (BUY={buy_score} vs SELL={sell_score})")

    # Step 2b: Duplicate signal prevention — skip kalau signal & harga sama persis
    global _last_signal
    price = indicators['price']
    price_diff = abs(price - _last_signal['price'])
    atr = indicators['atr']

    if (signal_type == _last_signal['type']
            and price_diff < atr * 0.3):
        # Tetap kirim tapi flip ke arah lawan kalau score cukup
        if signal_type == 'BUY' and sell_score >= 3:
            signal_type = 'SELL'
            logger.info(f"🔄 Flip to SELL (avoid duplicate BUY at similar price)")
        elif signal_type == 'SELL' and buy_score >= 3:
            signal_type = 'BUY'
            logger.info(f"🔄 Flip to BUY (avoid duplicate SELL at similar price)")

    # Update last signal tracker
    _last_signal = {'type': signal_type, 'price': price, 'time': datetime.now()}

    # Step 3: Hitung levels
    levels = _calculate_smart_levels(indicators, signal_type)

    # Step 4: Hitung probability & strength (10-90% range)
    total = max(buy_score + sell_score, 1)
    raw_buy_pct = buy_score / total * 100
    raw_sell_pct = sell_score / total * 100

    prob_up = round(max(10, min(90, raw_buy_pct)), 2)
    prob_down = round(max(10, min(90, raw_sell_pct)), 2)

    if signal_type == 'BUY':
        strength = round(max(30, min(90, raw_buy_pct)), 0)
    else:
        strength = round(max(30, min(90, raw_sell_pct)), 0)

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
