import requests

# Test 1: Swissquote
print("=== Test Swissquote ===")
try:
    r = requests.get("https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD", timeout=10)
    data = r.json()
    ticks = data[0]["spreadProfilePrices"][0]
    bid = float(ticks["bid"])
    ask = float(ticks["ask"])
    print(f"  Bid: {bid}, Ask: {ask}, Mid: {(bid+ask)/2:.2f}")
except Exception as e:
    print(f"  FAILED: {e}")

# Test 2: metals.live  
print("\n=== Test metals.live ===")
try:
    r = requests.get("https://api.metals.live/v1/spot", timeout=10)
    data = r.json()
    for item in data:
        if item.get("gold"):
            print(f"  Gold: {item['gold']}")
            break
except Exception as e:
    print(f"  FAILED: {e}")

# Test 3: goldapi.io (no key, just test)
print("\n=== Test Open Exchange (via FX API) ===")
try:
    r = requests.get("https://open.er-api.com/v6/latest/USD", timeout=10)
    data = r.json()
    # This won't have XAU but let's check
    print(f"  Has XAU: {'XAU' in data.get('rates', {})}")
    print(f"  Rates sample: {list(data.get('rates', {}).keys())[:10]}")
except Exception as e:
    print(f"  FAILED: {e}")

# Test 4: Yahoo Finance chart API v8
print("\n=== Test Yahoo Finance Chart API ===")
try:
    r = requests.get(
        "https://query1.finance.yahoo.com/v8/finance/chart/GC=F",
        params={"interval": "1m", "range": "1d"},
        headers={"User-Agent": "Mozilla/5.0"},
        timeout=10,
    )
    data = r.json()
    meta = data["chart"]["result"][0]["meta"]
    print(f"  GC=F price: {meta['regularMarketPrice']}")
except Exception as e:
    print(f"  FAILED: {e}")

# Test 5: Via Google Finance (scraping quote)
print("\n=== Test via Twelve Data (free) ===")
try:
    r = requests.get(
        "https://api.twelvedata.com/price?symbol=XAU/USD&apikey=demo",
        timeout=10,
    )
    data = r.json()
    if "price" in data:
        print(f"  XAU/USD: {data['price']}")
    else:
        print(f"  Response: {data}")
except Exception as e:
    print(f"  FAILED: {e}")
