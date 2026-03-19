import logging, os
logging.basicConfig(level=logging.INFO, format='%(levelname)s | %(message)s')
from dotenv import load_dotenv
load_dotenv()
from price_fetcher import fetch_xauusd_data
from indicators import calculate_all_indicators
from signal_generator import _fallback_analysis, generate_signal_with_gemini

df = fetch_xauusd_data('15m')
ind = calculate_all_indicators(df)

print(f"\nPRICE: {ind['price']:.2f} | RSI: {ind['rsi']:.1f} | Stoch: {ind['stoch_k']:.0f}")
print(f"EMA Trend: {ind.get('ema_trend')} | Momentum: {ind.get('momentum_dir')}")
print(f"MACD Hist: {ind['macd_histogram']:.3f} | EMA9: {ind['ema_9']:.2f}")
print(f"Price vs EMA9: {'above' if ind['price'] > ind['ema_9'] else 'below'}")

print(f"\n--- FALLBACK TEST ---")
fb = _fallback_analysis(ind)
print(f"Signal: {fb['signal']} | Conf: {fb['confidence']}%")
print(f"Prob Up: {fb['prob_up']}% | Down: {fb['prob_down']}%")
print(f"Reasoning: {fb['reasoning']}")

print(f"\n--- GEMINI AI TEST ---")
api_key = os.getenv('GEMINI_API_KEY', '')
result = generate_signal_with_gemini(ind, api_key)
print(f"Signal: {result['signal']} | Conf: {result['confidence']}%")
print(f"Reasoning: {result['reasoning']}")
