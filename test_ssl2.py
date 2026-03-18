import urllib.request
import ssl
import json

# Create a more permissive SSL context
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
ctx.set_ciphers('DEFAULT:@SECLEVEL=0')

# Test Swissquote
print("=== Swissquote (urllib) ===")
try:
    req = urllib.request.Request(
        "https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        data = json.loads(resp.read())
        ticks = data[0]["spreadProfilePrices"][0]
        bid = float(ticks["bid"])
        ask = float(ticks["ask"])
        print(f"  Bid: {bid}, Ask: {ask}, Mid: {(bid+ask)/2:.2f}")
except Exception as e:
    print(f"  FAILED: {e}")

# Test metals.live
print("\n=== metals.live (urllib) ===")
try:
    req = urllib.request.Request(
        "https://api.metals.live/v1/spot",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        data = json.loads(resp.read())
        for item in data:
            if item.get("gold"):
                print(f"  Gold: {item['gold']}")
                break
except Exception as e:
    print(f"  FAILED: {e}")

# Test FCSApi (free, no key needed for basic)
print("\n=== FCSApi ===")
try:
    req = urllib.request.Request(
        "https://fcsapi.com/api-v3/forex/latest?symbol=XAU/USD&access_key=API_KEY",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        data = json.loads(resp.read())
        print(f"  Response: {str(data)[:300]}")
except Exception as e:
    print(f"  FAILED: {e}")
    
# Test Yahoo direct for both GC=F and GLD (gold ETF)
print("\n=== Yahoo: GC=F vs GLD*10 (spot estimate) ===")
try:
    req = urllib.request.Request(
        "https://query1.finance.yahoo.com/v8/finance/chart/GC=F?interval=1m&range=1d",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        data = json.loads(resp.read())
        gcf_price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        print(f"  GC=F (futures): {gcf_price}")
except Exception as e:
    print(f"  GC=F FAILED: {e}")

try:
    req = urllib.request.Request(
        "https://query1.finance.yahoo.com/v8/finance/chart/GLD?interval=1m&range=1d",
        headers={"User-Agent": "Mozilla/5.0"}
    )
    with urllib.request.urlopen(req, context=ctx, timeout=10) as resp:
        data = json.loads(resp.read())
        gld_price = data["chart"]["result"][0]["meta"]["regularMarketPrice"]
        print(f"  GLD (ETF):     {gld_price}")
        print(f"  GLD*10 ≈ spot: {gld_price * 10:.2f}")
except Exception as e:
    print(f"  GLD FAILED: {e}")
