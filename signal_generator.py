"""
XAUUSD Scalp Signal Generator — AI-Powered (v3 - Pro Chart Reading)
====================================================================
SEPERTI TRADER BACA CHART:
1. Lihat struktur harga dulu (HH/HL atau LH/LL) — ini trend UTAMA
2. Cek higher timeframe (1H) — jangan trade melawan trend besar
3. Baca candle terakhir (body size, bukan cuma arah) — momentum REAL
4. Konfirmasi dengan indikator (MACD, EMA, ADX)
5. Gemini AI sebagai second opinion, BUKAN decision maker
6. STRICT validation: signal HARUS sejalan dengan semua konfirmasi
"""

import json
import logging
import os
from google import genai
from google.genai import types

logger = logging.getLogger(__name__)


# ============================================================
# STEP 1: BACA CHART SEPERTI TRADER PRO
# ============================================================

def _read_market_trend(indicators: dict, htf_data: dict = None) -> dict:
    """
    Baca kondisi market SEPERTI TRADER BUKA CHART.
    
    Urutan trader baca chart:
    1. Price Structure (HH/HL/LH/LL) — trend utama
    2. HTF trend (1H) — big picture
    3. Candle body momentum — siapa yang menang (bull vs bear POWER)
    4. Recent net move — harga gerak ke mana
    5. MACD — momentum konfirmasi
    6. Price vs EMA — positioning
    7. ADX/RSI/Stoch — fine tuning
    """
    score = 0  # Positif = bullish, negatif = bearish
    reasons = []

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
    momentum_net = indicators.get('momentum_net', 0)
    bullish_candles = indicators.get('bullish_candles', 0)
    bearish_candles = indicators.get('bearish_candles', 0)
    body_ratio = indicators.get('body_ratio', 0)
    vwap = indicators.get('vwap', 0)
    atr = indicators.get('atr', 10)

    # Price structure
    structure = indicators.get('price_structure', 'unknown')
    
    # ============================================================
    # 1. PRICE STRUCTURE — PALING PENTING (bobot 7)
    # Trader pertama kali lihat: market bikin HH/HL atau LH/LL?
    # ============================================================
    if structure == 'downtrend':
        score -= 7
        reasons.append(f"🔻 STRUCTURE: Downtrend (LH+LL)")
    elif structure == 'uptrend':
        score += 7
        reasons.append(f"🔺 STRUCTURE: Uptrend (HH+HL)")
    elif structure == 'distribution':
        score -= 4
        reasons.append(f"🔻 STRUCTURE: Distribution (topping)")
    elif structure == 'accumulation':
        score += 4
        reasons.append(f"🔺 STRUCTURE: Accumulation (bottoming)")
    elif structure == 'ranging':
        reasons.append(f"↔️ STRUCTURE: Ranging")
    
    # ============================================================
    # 2. HIGHER TIMEFRAME TREND (bobot 6) — Big Picture
    # Kalau 1H bearish tapi 15m bullish = JANGAN BUY
    # ============================================================
    if htf_data and htf_data.get('htf_trend', 'unknown') != 'unknown':
        htf_trend = htf_data['htf_trend']
        htf_score_val = htf_data.get('htf_score', 0)
        if htf_trend == 'BULLISH':
            score += 6
            reasons.append(f"🔺 HTF 1H: BULLISH (score={htf_score_val})")
        elif htf_trend == 'LEAN_BULLISH':
            score += 3
            reasons.append(f"🔺 HTF 1H: Lean bullish")
        elif htf_trend == 'BEARISH':
            score -= 6
            reasons.append(f"🔻 HTF 1H: BEARISH (score={htf_score_val})")
        elif htf_trend == 'LEAN_BEARISH':
            score -= 3
            reasons.append(f"🔻 HTF 1H: Lean bearish")
    
    # ============================================================
    # 3. CANDLE BODY MOMENTUM (bobot 5) — Siapa yang menang?
    # Bukan cuma hitung 3 green 2 red. Tapi TOTAL BODY SIZE.
    # 1 red besar > 3 green kecil = BEARISH
    # ============================================================
    if body_ratio < -0.5:
        score -= 5
        reasons.append(f"🔻 BODY: Bear dominasi kuat ({body_ratio:.2f})")
    elif body_ratio < -0.2:
        score -= 3
        reasons.append(f"🔻 BODY: Bear lebih kuat ({body_ratio:.2f})")
    elif body_ratio > 0.5:
        score += 5
        reasons.append(f"🔺 BODY: Bull dominasi kuat ({body_ratio:.2f})")
    elif body_ratio > 0.2:
        score += 3
        reasons.append(f"🔺 BODY: Bull lebih kuat ({body_ratio:.2f})")
    
    # ============================================================
    # 4. NET MOVE — arah harga aktual (bobot 4)
    # ============================================================
    if momentum_net < -(atr * 0.5):
        score -= 4
        reasons.append(f"🔻 NET: Turun signifikan ({momentum_net:.2f})")
    elif momentum_net < -(atr * 0.2):
        score -= 2
    elif momentum_net > (atr * 0.5):
        score += 4
        reasons.append(f"🔺 NET: Naik signifikan ({momentum_net:.2f})")
    elif momentum_net > (atr * 0.2):
        score += 2

    # ============================================================
    # 5. MACD (bobot 3) — momentum konfirmasi
    # ============================================================
    if macd_hist > 0 and macd_line > macd_signal:
        score += 3
        reasons.append(f"🔺 MACD: Bullish (hist={macd_hist:.3f})")
    elif macd_hist < 0 and macd_line < macd_signal:
        score -= 3
        reasons.append(f"🔻 MACD: Bearish (hist={macd_hist:.3f})")
    elif macd_hist > 0:
        score += 1
    elif macd_hist < 0:
        score -= 1

    # ============================================================
    # 6. PRICE vs EMA CLUSTER (bobot 3) — positioning
    # ============================================================
    below_all = price < ema_9 and price < ema_21
    above_all = price > ema_9 and price > ema_21
    if above_all and ema_9 > ema_21:
        score += 3
        reasons.append(f"🔺 EMA: Price > EMA9 > EMA21")
    elif below_all and ema_9 < ema_21:
        score -= 3
        reasons.append(f"🔻 EMA: Price < EMA9 < EMA21")
    elif price > ema_9:
        score += 1
    elif price < ema_9:
        score -= 1

    # ============================================================
    # 7. ADX + DI (bobot 2) — trend strength
    # ============================================================
    if adx > 25:
        if plus_di > minus_di:
            score += 2
        else:
            score -= 2

    # ============================================================
    # 8. VWAP (bobot 1) — institutional level
    # ============================================================
    if vwap > 0:
        if price > vwap:
            score += 1
        else:
            score -= 1

    # ============================================================
    # 9. RSI extreme (bobot 1, hanya kalau sejalan)
    # ============================================================
    if rsi > 65 and score > 0:
        score += 1
    elif rsi < 35 and score < 0:
        score -= 1

    # --- TOTAL ---
    max_score = 35  # Updated max: 7+6+5+4+3+3+2+1+1 = 32, round up
    strength = abs(score) / max_score * 100

    if score >= 12:
        direction = 'STRONG_BULLISH'
    elif score >= 5:
        direction = 'BULLISH'
    elif score <= -12:
        direction = 'STRONG_BEARISH'
    elif score <= -5:
        direction = 'BEARISH'
    else:
        direction = 'MIXED'

    # Log all reasons
    logger.info(f"📊 === MARKET READ ===")
    logger.info(f"📊 Final: score={score}/{max_score}, direction={direction}, strength={strength:.0f}%")
    for r in reasons:
        logger.info(f"   {r}")
    logger.info(f"   Extra: RSI={rsi:.0f} | Stoch={stoch_k:.0f} | ADX={adx:.0f} | "
                f"Bull={bullish_candles} Bear={bearish_candles} | Net={momentum_net:.2f}")

    return {
        'direction': direction,
        'score': score,
        'strength': round(strength, 1),
        'reasons': reasons,
    }


# ============================================================
# STEP 2: SL/TP FIXED 30 PIP — main kecil bersyukur
# ============================================================

def _calculate_smart_levels(indicators: dict, signal_type: str) -> dict:
    """
    SL/TP fixed ~30 pip ($3.00) untuk XAUUSD.
    1 pip XAUUSD = $0.10, jadi 30 pip = $3.00
    """
    price = indicators['price']
    risk = 3.00  # 30 pip = $3.00

    if signal_type == 'BUY':
        stop_loss = round(price - risk, 2)
        tp1 = round(price + (risk * 0.8), 2)   # 24 pip
        tp2 = round(price + (risk * 1.2), 2)   # 36 pip
        tp3 = round(price + (risk * 1.8), 2)   # 54 pip
    else:  # SELL
        stop_loss = round(price + risk, 2)
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
# STEP 3: GEMINI AI — Konfirmasi (harus sejalan trend)
# ============================================================

def _ask_ai_trader(indicators: dict, market_trend: dict, api_key: str) -> dict:
    """
    Gemini AI sebagai second opinion. Prompt simple dan fokus.
    """
    trend_dir = market_trend['direction']
    trend_score = market_trend['score']
    reasons_text = '\n'.join(market_trend.get('reasons', []))

    prompt = f"""Kamu analis XAUUSD. Analisis teknikal sudah dilakukan dengan hasil:

TREND: {trend_dir} (score: {trend_score})
ALASAN:
{reasons_text}

DATA MARKET:
Price: {indicators['price']:.2f}
EMA: 9={indicators['ema_9']:.2f} 21={indicators['ema_21']:.2f} 50={indicators['ema_50']:.2f}
MACD Hist: {indicators['macd_histogram']:.3f}
RSI: {indicators['rsi']:.1f} | ADX: {indicators['adx']:.1f} | +DI: {indicators['plus_di']:.1f} -DI: {indicators['minus_di']:.1f}
Structure: {indicators.get('price_structure', 'unknown')}
Body Ratio: {indicators.get('body_ratio', 0):.2f} (negatif=bear dominan, positif=bull dominan)
Candle: {indicators.get('candle_pattern', 'none')} ({indicators.get('candle_bias', 'neutral')})

ATURAN:
1. Signal HARUS sejalan trend: {trend_dir}
2. Kalau BEARISH → SELL. Kalau BULLISH → BUY
3. DILARANG melawan trend kecuali ada divergence + candle reversal
4. Confidence realistis 30-85

Output JSON saja (tanpa backtick/markdown):
{{"signal":"BUY/SELL","confidence":30-85,"prob_up":10-90,"prob_down":10-90,"reasoning":"Alasan singkat"}}"""

    models_to_try = [
        'gemini-2.5-flash',              # Paling pintar & reliable
        'gemini-3-flash-preview',        # Newest flash
        'gemini-2.5-flash-lite',         # Fallback
    ]

    client = genai.Client(api_key=api_key)
    for model_name in models_to_try:
        try:
            response = client.models.generate_content(
                model=model_name,
                contents=prompt,
                config=types.GenerateContentConfig(
                    temperature=0.2,
                    max_output_tokens=1024,
                ),
            )
            text = response.text.strip()

            if text.startswith('```'):
                text = text.split('\n', 1)[1] if '\n' in text else text[3:]
            if text.endswith('```'):
                text = text[:-3].strip()
            if text.startswith('json'):
                text = text[4:].strip()

            # Fix newlines inside JSON string (Gemini suka multiline)
            text = text.replace('\n', ' ').replace('\r', ' ')

            # Try parse JSON, kalau gagal coba repair
            try:
                result = json.loads(text)
            except json.JSONDecodeError:
                # Coba extract manual dari partial JSON
                import re
                sig_m = re.search(r'"signal"\s*:\s*"(BUY|SELL)"', text, re.IGNORECASE)
                conf_m = re.search(r'"confidence"\s*:\s*(\d+)', text)
                pu_m = re.search(r'"prob_up"\s*:\s*(\d+)', text)
                pd_m = re.search(r'"prob_down"\s*:\s*(\d+)', text)
                if sig_m:
                    result = {
                        'signal': sig_m.group(1).upper(),
                        'confidence': int(conf_m.group(1)) if conf_m else 50,
                        'prob_up': int(pu_m.group(1)) if pu_m else 50,
                        'prob_down': int(pd_m.group(1)) if pd_m else 50,
                        'reasoning': 'Parsed from partial response',
                    }
                    logger.info(f"🔧 Gemini {model_name}: repaired partial JSON")
                else:
                    logger.warning(f"⚠️ Gemini {model_name} JSON unfixable: {text[:150]}")
                    continue

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

def generate_signal_with_gemini(indicators: dict, api_key: str = None, htf_data: dict = None) -> dict:
    """
    Generate signal XAUUSD — BACA CHART SEPERTI TRADER PRO.

    Flow:
    1. _read_market_trend() → full chart analysis (structure + HTF + momentum)
    2. _ask_ai_trader() → Gemini sebagai second opinion
    3. _validate_signal() → tolak kalau melawan trend
    4. _calculate_smart_levels() → SL/TP ketat
    """
    # STEP 1: Baca chart seperti trader
    market_trend = _read_market_trend(indicators, htf_data=htf_data)
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
