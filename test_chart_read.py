"""Test chart reading accuracy"""
import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')

from price_fetcher import fetch_xauusd_data, fetch_higher_timeframe
from indicators import calculate_all_indicators, calculate_htf_trend
from signal_generator import _read_market_trend

# Fetch 15m data
df = fetch_xauusd_data(timeframe='15m', lookback_days=7)
if df.empty:
    print("No data!")
    exit()

ind = calculate_all_indicators(df)
print(f"\n=== 15M INDICATORS ===")
print(f"Price: {ind['price']:.2f}")
print(f"Structure: {ind['price_structure']} (HH={ind['hh_count']} HL={ind['hl_count']} LH={ind['lh_count']} LL={ind['ll_count']})")
print(f"Body Ratio: {ind['body_ratio']:.3f} (Bull={ind['bullish_power']:.2f} Bear={ind['bearish_power']:.2f})")
print(f"MACD Hist: {ind['macd_histogram']:.3f}")
print(f"EMA: 9={ind['ema_9']:.2f} 21={ind['ema_21']:.2f} 50={ind['ema_50']:.2f}")
print(f"RSI: {ind['rsi']:.1f} | ADX: {ind['adx']:.1f} | Stoch: {ind['stoch_k']:.1f}")
print(f"Momentum: {ind['momentum_dir']} net={ind['momentum_net']:.2f}")

# Fetch HTF 1H
df_htf = fetch_higher_timeframe(timeframe_htf='1h', lookback_days=14)
htf_data = None
if not df_htf.empty:
    htf_data = calculate_htf_trend(df_htf)
    print(f"\n=== 1H HTF TREND ===")
    print(f"HTF: {htf_data['htf_trend']} (score={htf_data['htf_score']})")
else:
    print("\nHTF data empty")

# Final trend reading
print(f"\n=== CHART READING ===")
trend = _read_market_trend(ind, htf_data=htf_data)
print(f"DIRECTION: {trend['direction']}")
print(f"SCORE: {trend['score']}")
print(f"STRENGTH: {trend['strength']}%")
print(f"Reasons:")
for r in trend.get('reasons', []):
    print(f"  {r}")
