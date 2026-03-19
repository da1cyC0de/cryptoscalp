"""
XAUUSD Scalp Signal Generator — AI-Powered
Gemini AI menganalisis semua data teknikal dan memutuskan BUY/SELL.
Technical indicators sebagai input data, AI sebagai trader yang menganalisis.
"""

import json
import time
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
    Retry dengan delay jika rate limited.
    """

    prompt = f"""Kamu adalah trader XAUUSD profesional. Analisis data ini dan putuskan BUY atau SELL.

=== HARGA ===
Price: {indicators['price']:.2f} | High: {indicators['high']:.2f} | Low: {indicators['low']:.2f}

=== TREND (PALING PENTING — ikuti trend!) ===
EMA 9: {indicators['ema_9']:.2f} | EMA 21: {indicators['ema_21']:.2f} | EMA 50: {indicators['ema_50']:.2f}
EMA Trend: {indicators.get('ema_trend', 'N/A')}
ADX: {indicators['adx']:.1f} | +DI: {indicators['plus_di']:.1f} | -DI: {indicators['minus_di']:.1f}
MACD: {indicators['macd']:.3f} | Signal: {indicators['macd_signal']:.3f} | Hist: {indicators['macd_histogram']:.3f}

=== MOMENTUM ===
RSI: {indicators['rsi']:.1f} | Stoch K: {indicators['stoch_k']:.1f} | D: {indicators['stoch_d']:.1f}
Momentum: {indicators.get('momentum_dir', 'N/A')}

=== VOLATILITY & LEVELS ===
ATR: {indicators['atr']:.2f}
BB: Upper={indicators['bb_upper']:.2f} Mid={indicators['bb_middle']:.2f} Lower={indicators['bb_lower']:.2f}
Support: {indicators.get('nearest_support', 'N/A')} | Resistance: {indicators.get('nearest_resistance', 'N/A')}
VWAP: {indicators.get('vwap', 0):.2f}

=== PATTERNS ===
Candle: {indicators.get('candle_pattern', 'none')} ({indicators.get('candle_bias', 'neutral')})
RSI Divergence: {indicators.get('rsi_divergence', 'none')}

=== ATURAN WAJIB ===
1. TREND IS KING — kalau trend bearish (EMA9 < EMA21, price < EMA, MACD negatif) → SELL
2. TREND IS KING — kalau trend bullish (EMA9 > EMA21, price > EMA, MACD positif) → BUY
3. JANGAN MELAWAN TREND! RSI oversold di downtrend BUKAN sinyal BUY — itu artinya trend masih kuat turun
4. RSI overbought di uptrend BUKAN sinyal SELL — itu artinya trend masih kuat naik
5. Hanya reversal jika ada SEMUA ini: candle reversal + divergence + momentum sudah balik arah
6. Confidence 30-90, Prob Up + Prob Down = 100 (masing-masing 10-90)

Output HANYA JSON (tanpa markdown):
{{"signal":"BUY atau SELL","confidence":30-90,"prob_up":10-90,"prob_down":10-90,"reasoning":"2-3 kalimat Indonesia"}}"""

    client = genai.Client(api_key=api_key)
    models_to_try = ['gemini-2.0-flash-lite', 'gemini-2.0-flash']

    for attempt in range(3):  # Max 3 attempts with retry
        for model_name in models_to_try:
            try:
                response = client.models.generate_content(
                    model=model_name,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        temperature=0.3,
                        max_output_tokens=300,
                    ),
                )
                text = response.text.strip()

                # Clean markdown code blocks
                if text.startswith('```'):
                    text = text.split('\n', 1)[1] if '\n' in text else text[3:]
                if text.endswith('```'):
                    text = text[:-3].strip()
                if text.startswith('json'):
                    text = text[4:].strip()

                result = json.loads(text)

                signal = result.get('signal', '').upper()
                if signal not in ('BUY', 'SELL'):
                    logger.warning(f"⚠️ Gemini returned invalid signal: {signal}")
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
                logger.warning(f"⚠️ Gemini {model_name} JSON parse error: {e}")
                logger.warning(f"   Raw response: {text[:200]}")
                continue
            except Exception as e:
                err_str = str(e)
                if '429' in err_str or 'RESOURCE_EXHAUSTED' in err_str:
                    logger.warning(f"⚠️ Gemini {model_name} rate limited, retry in 60s...")
                    if attempt < 2:
                        time.sleep(60)
                        break  # break inner loop to retry
                else:
                    logger.warning(f"⚠️ Gemini {model_name} error: {e}")
                continue

    # Fallback: trend-following analysis jika Gemini gagal
    logger.warning("⚠️ Gemini gagal semua attempt, menggunakan fallback teknikal")
    return _fallback_analysis(indicators)


def _fallback_analysis(indicators: dict) -> dict:
    """
    Fallback TREND-FOLLOWING jika Gemini AI tidak tersedia.
    Trend = raja. RSI oversold di downtrend = SELL, bukan BUY.
    """
    rsi = indicators['rsi']
    stoch_k = indicators['stoch_k']
    ema_trend = indicators.get('ema_trend', 'mixed')
    momentum = indicators.get('momentum_dir', 'flat')
    macd_hist = indicators.get('macd_histogram', 0)
    price = indicators['price']
    ema_9 = indicators['ema_9']
    ema_21 = indicators['ema_21']
    vwap = indicators.get('vwap', 0)

    buy_pts = 0
    sell_pts = 0

    # 1. EMA TREND — bobot 3 (paling penting)
    if ema_trend in ('strong_bullish', 'bullish'):
        buy_pts += 3
    elif ema_trend in ('strong_bearish', 'bearish'):
        sell_pts += 3

    # 2. MACD — bobot 2
    if macd_hist > 0:
        buy_pts += 2
    elif macd_hist < 0:
        sell_pts += 2

    # 3. Price vs EMA9 — bobot 1
    if price > ema_9:
        buy_pts += 1
    else:
        sell_pts += 1

    # 4. Momentum — bobot 1
    if momentum == 'bullish':
        buy_pts += 1
    elif momentum == 'bearish':
        sell_pts += 1

    # 5. VWAP — bobot 1
    if vwap > 0:
        if price > vwap:
            buy_pts += 1
        else:
            sell_pts += 1

    # RSI/Stoch HANYA jadi faktor kalau sejalan dengan trend
    if ema_trend in ('strong_bullish', 'bullish') and rsi > 50:
        buy_pts += 1
    elif ema_trend in ('strong_bearish', 'bearish') and rsi < 50:
        sell_pts += 1

    total = max(buy_pts + sell_pts, 1)
    if buy_pts > sell_pts:
        signal = 'BUY'
        confidence = max(30, min(90, int(buy_pts / total * 100)))
        prob_up = max(10, min(90, round(buy_pts / total * 100)))
        prob_down = max(10, min(90, round(sell_pts / total * 100)))
    else:
        signal = 'SELL'
        confidence = max(30, min(90, int(sell_pts / total * 100)))
        prob_up = max(10, min(90, round(buy_pts / total * 100)))
        prob_down = max(10, min(90, round(sell_pts / total * 100)))

    return {
        'signal': signal,
        'confidence': confidence,
        'prob_up': prob_up,
        'prob_down': prob_down,
        'reasoning': f"Fallback (trend-following): EMA={ema_trend}, MACD={'+'if macd_hist>0 else '-'}, RSI={rsi:.0f}",
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
