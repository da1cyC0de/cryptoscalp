import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s | %(message)s')
from dotenv import load_dotenv
load_dotenv()
from price_fetcher import fetch_btcusd_data
from indicators import calculate_all_indicators
from signal_generator import generate_signal_with_gemini

print('=== BTCUSD TEST ===')
df = fetch_btcusd_data('15m')
ind = calculate_all_indicators(df)
print(f"PRICE: {ind['price']:.2f} | RSI: {ind['rsi']:.1f} | EMA Trend: {ind.get('ema_trend')}")

result = generate_signal_with_gemini(ind, symbol='BTCUSD')
print(f"Signal: {result['signal']} | Conf: {result['confidence']}%")
print(f"SL: {result['stop_loss']} | TP1: {result['tp1']} | TP2: {result['tp2']}")
print(f"Reasoning: {result['reasoning']}")
