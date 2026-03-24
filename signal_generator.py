"""
XAUUSD Scalp Signal Generator — AI-Powered (v2 - High Accuracy)
================================================================
1. Baca market dulu (trend analysis) sebelum kirim signal
2. Gemini AI sebagai konfirmasi, BUKAN decision maker utama
3. Trend validation: TIDAK BOLEH BUY di downtrend, TIDAK BOLEH SELL di uptrend
4. SL ketat berdasarkan S/R + ATR kecil
5. Model cascade: 2.5-flash-lite → 2.5-flash → 3-flash-preview → 3.1-flash-lite-preview
"""

import json
import logging
import os
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


# ============================================================
# STEP 1: BACA MARKET — Tentukan trend SEBELUM signal
# ============================================================

def _read_market_trend(indicators: dict) -> dict:
    """
    Baca kondisi market secara objektif.
    Returns: direction, score, strength
    """
    score = 0  # Positif = bullish, negatif = bearish

    price = indicators['price']
    ema_9 = indicators['ema_9']
    ema_21 = indicators['ema_21']
    ema_50 = indicators['ema_50']
    macd_hist = indicators.get('macd_histogram', 0)
    macd_line = indicators.get('macd', 0)
    macd_signal = indicators.get('macd_signal', 0)
    rsi = indicators['rsi']
    adx = indicators['adx']
    plus_di = indicators['plus_di']
    minus_di = indicators['minus_di']
    stoch_k = indicators['stoch_k']
    ema_trend = indicators.get('ema_trend', 'mixed')
    momentum = indicators.get('momentum_dir', 'flat')
    vwap = indicators.get('vwap', 0)

    # === 1. EMA ALIGNMENT (bobot 5 — paling penting) ===
    if ema_trend == 'strong_bullish':
        score += 5
    elif ema_trend == 'bullish':
        score += 3
    elif ema_trend == 'strong_bearish':
        score -= 5
    elif ema_trend == 'bearish':
        score -= 3

    # === 2. PRICE vs EMAs (bobot 3) ===
    if price > ema_9 > ema_21:
        score += 3
    elif price < ema_9 < ema_21:
        score -= 3
    elif price > ema_9:
        score += 1
    elif price < ema_9:
        score -= 1

    # === 3. MACD (bobot 3) ===
    if macd_hist > 0 and macd_line > macd_signal:
        score += 3
    elif macd_hist < 0 and macd_line < macd_signal:
        score -= 3
    elif macd_hist > 0:
        score += 1
    elif macd_hist < 0:
        score -= 1

    # === 4. ADX + DI (bobot 2) ===
    if adx > 20:
        if plus_di > minus_di:
            score += 2
        else:
            score -= 2

    # === 5. MOMENTUM (bobot 2) ===
    if momentum == 'bullish':
        score += 2
    elif momentum == 'bearish':
        score -= 2

    # === 6. VWAP (bobot 1) ===
    if vwap > 0:
        if price > vwap:
            score += 1
        else:
            score -= 1

    # === 7. RSI context (bobot 1, HANYA sejalan trend) ===
    if rsi > 60 and score > 0:
        score += 1
    elif rsi < 40 and score < 0:
        score -= 1

    # === 8. Stochastic (bobot 1, HANYA sejalan trend) ===
    if stoch_k > 60 and score > 0:
        score += 1
    elif stoch_k < 40 and score < 0:
        score -= 1

    max_score = 19
    strength = abs(score) / max_score * 100

    if score >= 8:
        direction = 'STRONG_BULLISH'
    elif score >= 4:
        direction = 'BULLISH'
    elif score <= -8:
        direction = 'STRONG_BEARISH'
    elif score <= -4:
        direction = 'BEARISH'
    else:
        direction = 'MIXED'

    logger.info(f"📊 Market Read: score={score}, direction={direction}, strength={strength:.0f}%")

    return {
        'direction': direction,
        'score': score,
        'strength': round(strength, 1),
    }


# ============================================================
# STEP 2: SL/TP KETAT — based on S/R + small ATR buffer
# ============================================================

def _calculate_smart_levels(indicators: dict, signal_type: str) -> dict:
    """
    SL/TP ketat berdasarkan S/R levels.
    SL: behind nearest S/R + small buffer
    TP: realistic scalp targets with good R:R
    """
    price = indicators['price']
    atr = indicators['atr']
    nearest_support = indicators.get('nearest_support', price - 10)
    nearest_resistance = indicators.get('nearest_resistance', price + 10)

    if signal_type == 'BUY':
        sl_by_sr = nearest_support - (atr * 0.15)
        sl_by_atr = price - (atr * 0.6)
        stop_loss = max(sl_by_sr, sl_by_atr)

        risk = price - stop_loss
        if risk < atr * 0.3:
            risk = atr * 0.3
            stop_loss = price - risk
        if risk > atr * 0.8:
            risk = atr * 0.7
            stop_loss = price - risk

        tp1 = round(price + (risk * 1.0), 2)
        tp2 = round(price + (risk * 1.5), 2)
        tp3 = round(price + (risk * 2.2), 2)

    else:  # SELL
        sl_by_sr = nearest_resistance + (atr * 0.15)
        sl_by_atr = price + (atr * 0.6)
        stop_loss = min(sl_by_sr, sl_by_atr)

        risk = stop_loss - price
        if risk < atr * 0.3:
            risk = atr * 0.3
            stop_loss = price + risk
        if risk > atr * 0.8:
            risk = atr * 0.7
            stop_loss = price + risk

        tp1 = round(price - (risk * 1.0), 2)
        tp2 = round(price - (risk * 1.5), 2)
        tp3 = round(price - (risk * 2.2), 2)

    return {
        'stop_loss': round(stop_loss, 2),
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'risk': round(risk, 2),
    }


# ============================================================
# STEP 3: GEMINI AI — Konfirmasi (harus sejalan trend)
# ============================================================

def _ask_ai_trader(indicators: dict, market_trend: dict, api_key: str) -> dict:
    """
    Gemini AI menganalisis market. Hasilnya HARUS sejalan dengan trend.
    """
    trend_dir = market_trend['direction']
    trend_score = market_trend['score']

    prompt = f"""Kamu adalah analis XAUUSD profesional. BACA MARKET DULU sebelum kirim signal.

=== TREND SAAT INI (WAJIB DIIKUTI) ===
Trend Score: {trend_score} (positif=bullish, negatif=bearish)
Trend Direction: {trend_dir}

=== HARGA ===
Price: {indicators['price']:.2f} | High: {indicators['high']:.2f} | Low: {indicators['low']:.2f}

=== EMA (PALING PENTING) ===
EMA 9: {indicators['ema_9']:.2f} | EMA 21: {indicators['ema_21']:.2f} | EMA 50: {indicators['ema_50']:.2f} | EMA 200: {indicators['ema_200']:.2f}
EMA Trend: {indicators.get('ema_trend', 'N/A')}
Price vs EMA9: {"DI ATAS" if indicators['price'] > indicators['ema_9'] else "DI BAWAH"}
Price vs EMA21: {"DI ATAS" if indicators['price'] > indicators['ema_21'] else "DI BAWAH"}

=== MACD ===
MACD: {indicators['macd']:.3f} | Signal: {indicators['macd_signal']:.3f} | Hist: {indicators['macd_histogram']:.3f}
MACD Status: {"BULLISH (histogram positif)" if indicators['macd_histogram'] > 0 else "BEARISH (histogram negatif)"}

=== MOMENTUM ===
ADX: {indicators['adx']:.1f} | +DI: {indicators['plus_di']:.1f} | -DI: {indicators['minus_di']:.1f}
RSI: {indicators['rsi']:.1f} | Stoch K: {indicators['stoch_k']:.1f} | D: {indicators['stoch_d']:.1f}
Momentum candle: {indicators.get('momentum_dir', 'N/A')}

=== VOLATILITY & LEVELS ===
ATR: {indicators['atr']:.2f}
BB: Upper={indicators['bb_upper']:.2f} Mid={indicators['bb_middle']:.2f} Lower={indicators['bb_lower']:.2f}
Support: {indicators.get('nearest_support', 'N/A')} | Resistance: {indicators.get('nearest_resistance', 'N/A')}
VWAP: {indicators.get('vwap', 0):.2f}

=== PATTERNS ===
Candle: {indicators.get('candle_pattern', 'none')} ({indicators.get('candle_bias', 'neutral')})
RSI Divergence: {indicators.get('rsi_divergence', 'none')}

=== ATURAN KETAT (WAJIB) ===
1. BACA TREND DULU! Kalau price < EMA9 < EMA21, MACD negatif → DOWNTREND → HARUS SELL
2. Kalau price > EMA9 > EMA21, MACD positif → UPTREND → HARUS BUY
3. DILARANG BUY di downtrend meskipun RSI oversold — itu selling pressure kuat
4. DILARANG SELL di uptrend meskipun RSI overbought — itu buying pressure kuat
5. Signal HARUS sejalan dengan trend direction: {trend_dir}
6. Reversal HANYA boleh kalau ada: divergence + candle reversal + momentum sudah balik
7. Confidence 30-90 realistis. Prob Up + Prob Down = 100

Output HANYA JSON (tanpa markdown/backtick):
{{"signal":"BUY atau SELL","confidence":30-90,"prob_up":10-90,"prob_down":10-90,"reasoning":"2-3 kalimat alasan Bahasa Indonesia"}}"""

    models_to_try = [
        'gemini-2.5-flash-lite',
        'gemini-2.5-flash',
        'gemini-3-flash-preview',
        'gemini-3.1-flash-lite-preview',
    ]

    client = genai.Client(api_key=api_key)
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=300,
                ),
            )
            text = response.text.strip()

            if text.startswith('```'):
                text = text.split('\n', 1)[1] if '\n' in text else text[3:]
            if text.endswith('```'):
                text = text[:-3].strip()
            if text.startswith('json'):
                text = text[4:].strip()

            result = json.loads(text)

            signal = result.get('signal', '').upper()
            if signal not in ('BUY', 'SELL'):
                logger.warning(f"⚠️ Gemini {model_name} invalid signal: {signal}")
                continue

            confidence = max(30, min(90, int(result.get('confidence', 50))))
            prob_up = max(10, min(90, float(result.get('prob_up', 50))))
            prob_down = max(10, min(90, float(result.get('prob_down', 50))))
            reasoning = result.get('reasoning', '')

            logger.info(f"🤖 Gemini ({model_name}): {signal} | Confidence: {confidence}%")
            logger.info(f"   Reasoning: {reasoning}")

            return {
                'signal': signal,
                'confidence': confidence,
                'prob_up': prob_up,
                'prob_down': prob_down,
                'reasoning': reasoning,
            }

        except json.JSONDecodeError as e:
            logger.warning(f"⚠️ Gemini {model_name} JSON error: {e}")
            logger.warning(f"   Raw: {text[:200]}")
            continue
        except Exception as e:
            err_str = str(e)
            if '429' in err_str or 'RESOURCE_EXHAUSTED' in err_str:
                logger.warning(f"⚠️ Gemini {model_name} quota habis, next model...")
                continue
            else:
                logger.warning(f"⚠️ Gemini {model_name} error: {e}")
            continue

    logger.warning("⚠️ Semua model Gemini gagal, pakai analisis teknikal")
    return None


# ============================================================
# STEP 4: TREND VALIDATION — Tolak signal melawan trend
# ============================================================

def _validate_signal(signal: str, market_trend: dict) -> str:
    """
    Signal HARUS sejalan dengan trend.
    AI bilang BUY tapi market BEARISH → paksa SELL.
    """
    direction = market_trend['direction']
    score = market_trend['score']

    if direction in ('STRONG_BEARISH', 'BEARISH') and signal == 'BUY':
        logger.warning(f"🚫 DITOLAK: AI bilang BUY tapi trend {direction} (score={score}) → SELL")
        return 'SELL'

    if direction in ('STRONG_BULLISH', 'BULLISH') and signal == 'SELL':
        logger.warning(f"🚫 DITOLAK: AI bilang SELL tapi trend {direction} (score={score}) → BUY")
        return 'BUY'

    return signal


def _fallback_analysis(indicators: dict, market_trend: dict) -> dict:
    """
    Fallback kalau Gemini gagal — signal 100% berdasarkan trend reading.
    """
    score = market_trend['score']
    strength = market_trend['strength']

    if score > 0:
        signal = 'BUY'
        confidence = min(90, max(35, int(strength)))
        prob_up = min(90, max(10, int(50 + score * 3)))
        prob_down = max(10, 100 - prob_up)
    else:
        signal = 'SELL'
        confidence = min(90, max(35, int(strength)))
        prob_down = min(90, max(10, int(50 + abs(score) * 3)))
        prob_up = max(10, 100 - prob_down)

    ema_trend = indicators.get('ema_trend', 'mixed')
    macd_hist = indicators.get('macd_histogram', 0)
    rsi = indicators['rsi']

    return {
        'signal': signal,
        'confidence': confidence,
        'prob_up': prob_up,
        'prob_down': prob_down,
        'reasoning': f"Teknikal: trend={ema_trend}, MACD={'+'if macd_hist>0 else '-'}, RSI={rsi:.0f}, score={score}",
    }


# ============================================================
# MAIN: Generate Signal (baca market → AI → validasi → levels)
# ============================================================

def generate_signal_with_gemini(indicators: dict, api_key: str = None) -> dict:
    """
    Generate signal XAUUSD — BACA MARKET DULU baru kirim signal.

    Flow:
    1. _read_market_trend() → tentukan trend objektif
    2. _ask_ai_trader() → Gemini analisis sebagai konfirmasi
    3. _validate_signal() → tolak kalau AI melawan trend
    4. _calculate_smart_levels() → SL/TP ketat
    """
    # STEP 1: Baca market
    market_trend = _read_market_trend(indicators)
    logger.info(f"📊 Trend: {market_trend['direction']} (score={market_trend['score']}, "
                f"strength={market_trend['strength']}%)")

    # STEP 2: AI analysis
    api_key = os.getenv('GEMINI_API_KEY', '')
    if api_key:
        ai_result = _ask_ai_trader(indicators, market_trend, api_key)
    else:
        ai_result = None

    if ai_result is None:
        ai_result = _fallback_analysis(indicators, market_trend)
        logger.info("📋 Menggunakan fallback analysis (Gemini unavailable)")

    # STEP 3: VALIDASI — signal harus sejalan trend
    original_signal = ai_result['signal']
    validated_signal = _validate_signal(original_signal, market_trend)

    if validated_signal != original_signal:
        logger.warning(f"🔄 Signal diubah: {original_signal} → {validated_signal} (ikut trend)")
        if validated_signal == 'SELL':
            ai_result['prob_down'] = max(ai_result['prob_down'], 60)
            ai_result['prob_up'] = 100 - ai_result['prob_down']
        else:
            ai_result['prob_up'] = max(ai_result['prob_up'], 60)
            ai_result['prob_down'] = 100 - ai_result['prob_up']
        ai_result['reasoning'] += f" [Override: ikut trend {market_trend['direction']}]"

    signal_type = validated_signal
    confidence = ai_result['confidence']
    prob_up = ai_result['prob_up']
    prob_down = ai_result['prob_down']
    reasoning = ai_result['reasoning']

    # STEP 4: SL/TP ketat
    levels = _calculate_smart_levels(indicators, signal_type)

    result = {
        'signal': signal_type,
        'confidence': confidence,
        'stop_loss': levels['stop_loss'],
        'tp1': levels['tp1'],
        'tp2': levels['tp2'],
        'tp3': levels['tp3'],
        'prob_up': round(prob_up, 2),
        'prob_down': round(prob_down, 2),
        'strength': confidence,
        'reasoning': reasoning,
    }

    rr_ratio = round(abs(levels['tp2'] - indicators['price']) / max(levels['risk'], 0.01), 1)
    logger.info(f"✅ Signal: {signal_type} | Confidence: {confidence}% | "
                f"Risk: {levels['risk']} | R:R = 1:{rr_ratio} | Trend: {market_trend['direction']}")

    return result
