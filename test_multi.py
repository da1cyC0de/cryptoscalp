import logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s | %(message)s')
from dotenv import load_dotenv
load_dotenv()

from price_fetcher import fetch_btcusd_data, fetch_xauusd_data
from indicators import calculate_all_indicators
from signal_generator import generate_signal

# Test BTC
print("\n===== BTCUSD TEST =====")
df_btc = fetch_btcusd_data('15m')
ind_btc = calculate_all_indicators(df_btc)
print(f"BTC Price: {ind_btc['price']:.2f} | RSI: {ind_btc['rsi']:.1f} | EMA Trend: {ind_btc.get('ema_trend')}")
result_btc = generate_signal(ind_btc, 'BTCUSD')
print(f"Signal: {result_btc['signal']} | Conf: {result_btc['confidence']}%")
print(f"SL: {result_btc['stop_loss']:.2f} | TP1: {result_btc['tp1']:.2f} | TP2: {result_btc['tp2']:.2f}")
print(f"Reasoning: {result_btc['reasoning']}")

# Test XAUUSD
print("\n===== XAUUSD TEST =====")
df_xau = fetch_xauusd_data('15m')
ind_xau = calculate_all_indicators(df_xau)
print(f"XAU Price: {ind_xau['price']:.2f} | RSI: {ind_xau['rsi']:.1f} | EMA Trend: {ind_xau.get('ema_trend')}")
result_xau = generate_signal(ind_xau, 'XAUUSD')
print(f"Signal: {result_xau['signal']} | Conf: {result_xau['confidence']}%")
print(f"SL: {result_xau['stop_loss']:.2f} | TP1: {result_xau['tp1']:.2f} | TP2: {result_xau['tp2']:.2f}")
print(f"Reasoning: {result_xau['reasoning']}")
