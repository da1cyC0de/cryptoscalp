"""Full signal generation test"""
import logging, os
logging.basicConfig(level=logging.INFO, format='%(message)s')
from dotenv import load_dotenv
load_dotenv()

from price_fetcher import fetch_xauusd_data, fetch_higher_timeframe
from indicators import calculate_all_indicators, calculate_htf_trend
from signal_generator import generate_signal_with_gemini

df = fetch_xauusd_data(timeframe='15m', lookback_days=7)
ind = calculate_all_indicators(df)

df_htf = fetch_higher_timeframe(timeframe_htf='1h', lookback_days=14)
htf_data = calculate_htf_trend(df_htf) if not df_htf.empty else None

result = generate_signal_with_gemini(ind, htf_data=htf_data)

print("\n========== FINAL SIGNAL ==========")
print("Signal:", result["signal"])
print("Confidence:", str(result["confidence"]) + "%")
print("Entry:", round(ind["price"], 2))
print("SL:", result["stop_loss"])
print("TP1:", result["tp1"], "| TP2:", result["tp2"], "| TP3:", result["tp3"])
print("Prob Up:", str(result["prob_up"]) + "% | Down:", str(result["prob_down"]) + "%")
print("Reason:", result["reasoning"])
print("==================================")
