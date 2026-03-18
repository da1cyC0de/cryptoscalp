"""
Gemini AI Signal Generator
Menggunakan Google Gemini untuk analisis dan generate signal XAUUSD
"""

import json
import logging
import google.generativeai as genai

logger = logging.getLogger(__name__)


def setup_gemini(api_key: str):
    """Konfigurasi Gemini API"""
    genai.configure(api_key=api_key)


def generate_signal_with_gemini(indicators: dict, api_key: str) -> dict:
    """
    Gunakan Gemini AI untuk menganalisis indikator teknikal
    dan menghasilkan signal trading XAUUSD.
    
    Args:
        indicators: dict berisi semua nilai indikator teknikal
        api_key: Gemini API key
        
    Returns:
        dict dengan signal, TP, SL, probabilitas, dll.
    """
    setup_gemini(api_key)

    prompt = f"""Kamu adalah seorang expert XAUUSD scalp trader profesional dengan pengalaman 15+ tahun.
Analisis data teknikal berikut dan berikan signal trading yang akurat.

DATA TEKNIKAL XAUUSD SAAT INI:
================================
Harga Saat Ini: {indicators['price']:.2f}
High: {indicators['high']:.2f}
Low: {indicators['low']:.2f}

INDIKATOR:
- RSI (14): {indicators['rsi']}
- ADX (14): {indicators['adx']}
- +DI: {indicators['plus_di']}
- -DI: {indicators['minus_di']}
- ATR (14): {indicators['atr']}
- Bollinger Upper: {indicators['bb_upper']}
- Bollinger Middle: {indicators['bb_middle']}
- Bollinger Lower: {indicators['bb_lower']}
- Bollinger Width: {indicators['bb_width']}
- MACD Line: {indicators['macd']}
- MACD Signal: {indicators['macd_signal']}
- MACD Histogram: {indicators['macd_histogram']}
- EMA 9: {indicators['ema_9']}
- EMA 21: {indicators['ema_21']}
- EMA 50: {indicators['ema_50']}
- Stochastic K: {indicators['stoch_k']}
- Stochastic D: {indicators['stoch_d']}

ATURAN ANALISIS:
1. Tentukan signal: BUY, SELL, atau NEUTRAL
2. Hitung Stop Loss berdasarkan ATR (1.5x ATR dari harga)
3. Hitung 3 Take Profit levels:
   - TP1: ~1x ATR dari entry
   - TP2: ~2x ATR dari entry  
   - TP3: ~2.5x ATR dari entry
4. Estimasi probabilitas naik dan turun (total bisa < 100% karena ada prob sideways)
5. Berikan strength score 0-100

PERTIMBANGAN:
- RSI > 70 = overbought (cenderung sell), RSI < 30 = oversold (cenderung buy)
- ADX > 25 = trend kuat, ADX < 20 = sideways
- +DI > -DI = bullish, -DI > +DI = bearish
- MACD histogram positif = bullish momentum
- Harga di bawah BB lower = potential buy, di atas BB upper = potential sell
- EMA 9 > EMA 21 > EMA 50 = strong uptrend
- Stochastic K > 80 = overbought, K < 20 = oversold

RESPOND HANYA DALAM FORMAT JSON BERIKUT (tanpa markdown, tanpa code block):
{{
    "signal": "BUY atau SELL atau NEUTRAL",
    "confidence": 75,
    "stop_loss": 0.00,
    "tp1": 0.00,
    "tp2": 0.00,
    "tp3": 0.00,
    "prob_up": 0.00,
    "prob_down": 0.00,
    "strength": 75,
    "reasoning": "penjelasan singkat"
}}"""

    # Coba beberapa model free Gemini (fallback jika quota habis)
    free_models = [
        'gemini-2.0-flash-lite',
        'gemini-2.0-flash',
        'gemini-1.5-flash',
    ]

    response_text = None
    for model_name in free_models:
        try:
            logger.info(f"   Mencoba model: {model_name}")
            model = genai.GenerativeModel(model_name)
            response = model.generate_content(
                prompt,
                generation_config=genai.types.GenerationConfig(
                    temperature=0.3,
                    max_output_tokens=1000,
                )
            )
            response_text = response.text.strip()
            logger.info(f"   ✅ Berhasil dengan model: {model_name}")
            break
        except Exception as model_err:
            logger.warning(f"   ⚠️ Model {model_name} gagal: {model_err}")
            continue

    if response_text is None:
        logger.error("❌ Semua model Gemini gagal. Gunakan fallback.")
        return _fallback_signal(indicators)

    try:

        # Bersihkan response dari markdown code blocks
        if response_text.startswith("```"):
            lines = response_text.split("\n")
            # Remove first and last lines (``` markers)
            lines = [l for l in lines if not l.strip().startswith("```")]
            response_text = "\n".join(lines)

        signal_data = json.loads(response_text)

        # Validasi dan lengkapi data
        required_keys = ['signal', 'stop_loss', 'tp1', 'tp2', 'tp3',
                         'prob_up', 'prob_down', 'strength']
        for key in required_keys:
            if key not in signal_data:
                logger.warning(f"Key '{key}' tidak ditemukan di response Gemini")
                signal_data[key] = 0

        # Validasi signal type
        if signal_data['signal'] not in ['BUY', 'SELL', 'NEUTRAL']:
            signal_data['signal'] = 'NEUTRAL'

        logger.info(f"✅ Gemini analysis: {signal_data['signal']} "
                     f"(confidence: {signal_data.get('confidence', 'N/A')}%)")
        logger.info(f"   Reasoning: {signal_data.get('reasoning', 'N/A')}")

        return signal_data

    except json.JSONDecodeError as e:
        logger.error(f"❌ Gagal parse JSON dari Gemini: {e}")
        logger.error(f"   Response: {response_text[:500]}")
        return _fallback_signal(indicators)
    except Exception as e:
        logger.error(f"❌ Error saat memanggil Gemini API: {e}")
        return _fallback_signal(indicators)


def _fallback_signal(indicators: dict) -> dict:
    """
    Fallback signal generator menggunakan logika rule-based
    jika Gemini API gagal.
    """
    logger.info("📊 Menggunakan fallback rule-based signal...")

    price = indicators['price']
    rsi = indicators['rsi']
    adx = indicators['adx']
    plus_di = indicators['plus_di']
    minus_di = indicators['minus_di']
    atr = indicators['atr']
    macd_hist = indicators['macd_histogram']
    bb_lower = indicators['bb_lower']
    bb_upper = indicators['bb_upper']
    ema_9 = indicators['ema_9']
    ema_21 = indicators['ema_21']

    # Score system
    buy_score = 0
    sell_score = 0

    # RSI
    if rsi < 30:
        buy_score += 2
    elif rsi < 40:
        buy_score += 1
    elif rsi > 70:
        sell_score += 2
    elif rsi > 60:
        sell_score += 1

    # DI
    if plus_di > minus_di:
        buy_score += 1
    else:
        sell_score += 1

    # ADX (trend strength)
    trend_strong = adx > 25

    # MACD
    if macd_hist > 0:
        buy_score += 1
    elif macd_hist < 0:
        sell_score += 1

    # Bollinger
    if price <= bb_lower:
        buy_score += 2
    elif price >= bb_upper:
        sell_score += 2

    # EMA
    if ema_9 > ema_21:
        buy_score += 1
    else:
        sell_score += 1

    # Determine signal
    total = buy_score + sell_score
    if total == 0:
        total = 1

    if buy_score > sell_score and (trend_strong or buy_score >= 3):
        signal = 'BUY'
        prob_up = round((buy_score / total) * 85, 2)
        prob_down = round((sell_score / total) * 85, 2)
        stop_loss = round(price - (atr * 1.5), 2)
        tp1 = round(price + (atr * 1.0), 2)
        tp2 = round(price + (atr * 2.0), 2)
        tp3 = round(price + (atr * 2.5), 2)
    elif sell_score > buy_score and (trend_strong or sell_score >= 3):
        signal = 'SELL'
        prob_up = round((buy_score / total) * 85, 2)
        prob_down = round((sell_score / total) * 85, 2)
        stop_loss = round(price + (atr * 1.5), 2)
        tp1 = round(price - (atr * 1.0), 2)
        tp2 = round(price - (atr * 2.0), 2)
        tp3 = round(price - (atr * 2.5), 2)
    else:
        signal = 'NEUTRAL'
        prob_up = round((buy_score / total) * 50, 2)
        prob_down = round((sell_score / total) * 50, 2)
        stop_loss = round(price - (atr * 1.5), 2)
        tp1 = round(price + (atr * 0.5), 2)
        tp2 = round(price + (atr * 1.0), 2)
        tp3 = round(price + (atr * 1.5), 2)

    strength = round(max(buy_score, sell_score) / total * 100, 0)

    return {
        'signal': signal,
        'confidence': strength,
        'stop_loss': stop_loss,
        'tp1': tp1,
        'tp2': tp2,
        'tp3': tp3,
        'prob_up': prob_up,
        'prob_down': prob_down,
        'strength': strength,
        'reasoning': 'Fallback rule-based analysis (Gemini unavailable)'
    }
