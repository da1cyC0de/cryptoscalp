"""
XAUUSD Scalp Signal Generator — AI-Powered
Gemini AI menganalisis semua data teknikal dan memutuskan BUY/SELL.
Technical indicators sebagai input data, AI sebagai trader yang menganalisis.
"""

import json
import logging
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


def _calculate_smart_levels(indicators: dict, signal_type: str) -> dict:
    """
    SL/TP untuk SCALPING — ketat dan realistis.
    """
    price = indicators['price']
    atr = indicators['atr']
    nearest_support = indicators.get('nearest_support', price - 15)
    nearest_resistance = indicators.get('nearest_resistance', price + 15)

    if signal_type == 'BUY':
        sl_by_sr = nearest_support - (atr * 0.2)
        sl_by_atr = price - (atr * 1.0)
        stop_loss = max(sl_by_sr, sl_by_atr)

        risk = price - stop_loss
        if risk < atr * 0.4:
            risk = atr * 0.6
            stop_loss = price - risk
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
# GEMINI AI — THE TRADER
# ============================================================

def _ask_gemini_trader(indicators: dict, api_key: str) -> dict:
    """
    Kirim semua data teknikal ke Gemini AI.
    Gemini menganalisis seperti trader pro dan return JSON: signal, confidence, reasoning.
    """

    prompt = f"""Kamu adalah trader XAUUSD profesional kelas dunia yang sangat handal dalam scalping.
Analisis data teknikal berikut dan tentukan apakah harus BUY atau SELL saat ini.

=== DATA MARKET XAUUSD ===
Harga: {indicators['price']:.2f}
High: {indicators['high']:.2f} | Low: {indicators['low']:.2f}

=== TREND ===
EMA 9: {indicators['ema_9']:.2f} | EMA 21: {indicators['ema_21']:.2f} | EMA 50: {indicators['ema_50']:.2f}
EMA Trend: {indicators.get('ema_trend', 'N/A')}
ADX: {indicators['adx']:.1f} | +DI: {indicators['plus_di']:.1f} | -DI: {indicators['minus_di']:.1f}

=== MOMENTUM ===
RSI (14): {indicators['rsi']:.1f}
MACD: {indicators['macd']:.3f} | Signal: {indicators['macd_signal']:.3f} | Histogram: {indicators['macd_histogram']:.3f}
Stochastic K: {indicators['stoch_k']:.1f} | D: {indicators['stoch_d']:.1f}
Momentum Direction: {indicators.get('momentum_dir', 'N/A')}

=== VOLATILITY ===
ATR (14): {indicators['atr']:.2f}
Bollinger Upper: {indicators['bb_upper']:.2f} | Middle: {indicators['bb_middle']:.2f} | Lower: {indicators['bb_lower']:.2f}
BB Width: {indicators['bb_width']:.4f}

=== KEY LEVELS ===
Nearest Support: {indicators.get('nearest_support', 'N/A')}
Nearest Resistance: {indicators.get('nearest_resistance', 'N/A')}
VWAP: {indicators.get('vwap', 0):.2f}

=== PATTERNS ===
Candle Pattern: {indicators.get('candle_pattern', 'none')} ({indicators.get('candle_bias', 'neutral')})
RSI Divergence: {indicators.get('rsi_divergence', 'none')}

=== ATURAN ANALISIS ===
1. Kamu HARUS memilih BUY atau SELL — tidak boleh netral/wait
2. Analisis seperti trader pro: perhatikan trend, momentum, oversold/overbought, support/resistance, dan pola candle
3. Jika RSI sangat oversold (<30) dan Stoch juga oversold (<20), kemungkinan besar akan bounce — pertimbangkan BUY
4. Jika RSI sangat overbought (>70) dan Stoch juga overbought (>80), kemungkinan besar akan turun — pertimbangkan SELL
5. Jangan blindly follow trend — kalau sudah overextended, cari reversal
6. Confidence antara 30-90 (tidak pernah 100% yakin di market)
7. Prob Up + Prob Down harus = 100, range masing-masing 10-90

Jawab HANYA dalam format JSON berikut, tanpa markdown atau teks tambahan:
{{"signal": "BUY atau SELL", "confidence": angka 30-90, "prob_up": angka 10-90, "prob_down": angka 10-90, "reasoning": "analisis singkat 2-3 kalimat dalam bahasa Indonesia"}}"""

    client = genai.Client(api_key=api_key)
    free_models = ['gemini-2.0-flash-lite', 'gemini-2.0-flash']

    for model_name in free_models:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.4,
                    max_output_tokens=300,
                ),
            )
            text = response.text.strip()

            # Clean markdown code blocks if any
            if text.startswith('```'):
                text = text.split('\n', 1)[1] if '\n' in text else text[3:]
            if text.endswith('```'):
                text = text[:-3].strip()
            if text.startswith('json'):
                text = text[4:].strip()

            result = json.loads(text)

            # Validate response
            signal = result.get('signal', '').upper()
            if signal not in ('BUY', 'SELL'):
                signal = 'BUY'  # default

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
            logger.warning(f"⚠️ Gemini {model_name} JSON parse error: {e}")
            logger.warning(f"   Raw response: {text[:200]}")
            continue
        except Exception as e:
            logger.warning(f"⚠️ Gemini {model_name} error: {e}")
            continue

    # Fallback: simple technical analysis jika Gemini gagal
    logger.warning("⚠️ Gemini gagal, menggunakan fallback teknikal")
    return _fallback_analysis(indicators)


def _fallback_analysis(indicators: dict) -> dict:
    """Fallback sederhana jika Gemini AI tidak tersedia."""
    rsi = indicators['rsi']
    stoch_k = indicators['stoch_k']
    ema_trend = indicators.get('ema_trend', 'mixed')
    momentum = indicators.get('momentum_dir', 'flat')

    buy_points = 0
    sell_points = 0

    # RSI
    if rsi < 35:
        buy_points += 2
    elif rsi > 65:
        sell_points += 2

    # Stochastic
    if stoch_k < 20:
        buy_points += 1
    elif stoch_k > 80:
        sell_points += 1

    # EMA trend
    if ema_trend in ('strong_bullish', 'bullish'):
        buy_points += 1
    elif ema_trend in ('strong_bearish', 'bearish'):
        sell_points += 1

    # Momentum
    if momentum == 'bullish':
        buy_points += 1
    elif momentum == 'bearish':
        sell_points += 1

    if buy_points >= sell_points:
        signal = 'BUY'
        total = max(buy_points + sell_points, 1)
        confidence = max(30, min(90, int(buy_points / total * 100)))
    else:
        signal = 'SELL'
        total = max(buy_points + sell_points, 1)
        confidence = max(30, min(90, int(sell_points / total * 100)))

    return {
        'signal': signal,
        'confidence': confidence,
        'prob_up': max(10, min(90, buy_points / max(total, 1) * 100)),
        'prob_down': max(10, min(90, sell_points / max(total, 1) * 100)),
        'reasoning': f"Fallback analysis: RSI={rsi:.0f}, Stoch={stoch_k:.0f}, Trend={ema_trend}",
    }


# ============================================================
# MAIN SIGNAL GENERATION
# ============================================================

def generate_signal_with_gemini(indicators: dict, api_key: str) -> dict:
    """
    Generate signal XAUUSD — Gemini AI sebagai trader yang menganalisis market.
    """
    logger.info("🤖 Mengirim data ke Gemini AI untuk analisis...")

    # Gemini AI analyzes and decides
    ai_result = _ask_gemini_trader(indicators, api_key)

    signal_type = ai_result['signal']
    confidence = ai_result['confidence']
    prob_up = ai_result['prob_up']
    prob_down = ai_result['prob_down']
    reasoning = ai_result['reasoning']

    # Calculate SL/TP levels
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

    logger.info(f"✅ Signal: {signal_type} | Confidence: {confidence}% | "
                f"Risk: {levels['risk']} | R:R = 1:{round(abs(levels['tp2'] - indicators['price']) / max(levels['risk'], 0.01), 1)}")

    return result
