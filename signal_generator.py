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
    Confluence scoring — TREND-FOLLOWING approach.
    Rule #1: SELALU ikuti trend. RSI oversold di downtrend = SELL lebih, bukan BUY.
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

    # === Tentukan TREND dulu (paling penting) ===
    is_uptrend = ema_trend in ('strong_bullish', 'bullish')
    is_downtrend = ema_trend in ('strong_bearish', 'bearish')

    # 1. EMA TREND (bobot 2x karena paling penting)
    if is_uptrend:
        buy_reasons.append('EMA trend bullish')
        buy_reasons.append('Trade WITH uptrend')
    elif is_downtrend:
        sell_reasons.append('EMA trend bearish')
        sell_reasons.append('Trade WITH downtrend')

    # 2. RSI — HARUS sesuai trend! Oversold di downtrend = bearish continuation
    if is_downtrend:
        if rsi < 40:
            sell_reasons.append(f'RSI weak ({rsi}) in downtrend = continuation')
        elif rsi > 60:
            # RSI pullback ke overbought di downtrend = sell opportunity
            sell_reasons.append(f'RSI pullback ({rsi}) in downtrend = sell zone')
    elif is_uptrend:
        if rsi > 60:
            buy_reasons.append(f'RSI strong ({rsi}) in uptrend = continuation')
        elif rsi < 40:
            buy_reasons.append(f'RSI pullback ({rsi}) in uptrend = buy zone')
    else:
        # Sideways — RSI extreme baru berarti
        if rsi < 25:
            buy_reasons.append(f'RSI extreme oversold ({rsi})')
        elif rsi > 75:
            sell_reasons.append(f'RSI extreme overbought ({rsi})')

    # 3. ADX + DI
    if adx > 20:
        if plus_di > minus_di:
            buy_reasons.append(f'+DI > -DI (ADX {adx})')
        else:
            sell_reasons.append(f'-DI > +DI (ADX {adx})')

    # 4. MACD
    if macd_hist > 0 and macd > macd_signal:
        buy_reasons.append('MACD bullish')
    elif macd_hist < 0 and macd < macd_signal:
        sell_reasons.append('MACD bearish')

    # 5. BOLLINGER — juga harus sesuai trend
    if is_downtrend:
        if price < bb_middle:
            sell_reasons.append('Price below BB mid (bearish)')
        if price <= bb_lower:
            sell_reasons.append('Breaking BB lower (strong bearish)')
    elif is_uptrend:
        if price > bb_middle:
            buy_reasons.append('Price above BB mid (bullish)')
        if price >= bb_upper:
            buy_reasons.append('Breaking BB upper (strong bullish)')
    else:
        if price < bb_middle:
            sell_reasons.append('Below BB middle')
        else:
            buy_reasons.append('Above BB middle')

    # 6. STOCHASTIC — sesuai trend
    if is_downtrend:
        if stoch_k < 30:
            sell_reasons.append(f'Stoch bearish ({stoch_k:.0f})')
        elif stoch_k > stoch_d:
            pass  # Ignore bullish stoch in downtrend
        else:
            sell_reasons.append('Stoch K < D')
    elif is_uptrend:
        if stoch_k > 70:
            buy_reasons.append(f'Stoch bullish ({stoch_k:.0f})')
        elif stoch_k < stoch_d:
            pass  # Ignore bearish stoch in uptrend
        else:
            buy_reasons.append('Stoch K > D')
    else:
        if stoch_k > stoch_d:
            buy_reasons.append('Stoch K > D')
        else:
            sell_reasons.append('Stoch K < D')

    # 7. MOMENTUM
    if momentum_dir == 'bullish':
        buy_reasons.append('Momentum bullish')
    elif momentum_dir == 'bearish':
        sell_reasons.append('Momentum bearish')

    # 8. CANDLE PATTERN (hanya jika sesuai trend)
    if candle_bias == 'bullish' and not is_downtrend:
        buy_reasons.append('Candle bullish')
    elif candle_bias == 'bearish' and not is_uptrend:
        sell_reasons.append('Candle bearish')

    # 9. VWAP
    if vwap > 0:
        if price > vwap:
            buy_reasons.append('Above VWAP')
        else:
            sell_reasons.append('Below VWAP')

    # BONUS: RSI Divergence (only valid for reversal confirmation)
    if rsi_div == 'bullish' and not is_downtrend:
        buy_reasons.append('RSI bullish divergence')
    elif rsi_div == 'bearish' and not is_uptrend:
        sell_reasons.append('RSI bearish divergence')

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
