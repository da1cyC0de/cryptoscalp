import logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(message)s")

from price_fetcher import _get_live_price_gcf, fetch_xauusd_data, get_current_price

live = _get_live_price_gcf()
print(f"\n=== LIVE PRICE (fast_info): {live:.2f} ===")

df = fetch_xauusd_data("15m")
if not df.empty:
    last = float(df["Close"].iloc[-1])
    print(f"=== LAST CANDLE (adjusted): {last:.2f} ===")
    print(f"=== DIFFERENCE: {abs(live - last):.2f} ===")
else:
    print("NO DATA")
