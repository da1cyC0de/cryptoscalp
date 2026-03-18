import ssl
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

class TLSAdapter(HTTPAdapter):
    def init_poolmanager(self, *args, **kwargs):
        ctx = create_urllib3_context()
        ctx.set_ciphers('DEFAULT:@SECLEVEL=1')
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        kwargs['ssl_context'] = ctx
        return super().init_poolmanager(*args, **kwargs)

s = requests.Session()
s.mount('https://', TLSAdapter())

# Test Swissquote
print("=== Swissquote (custom TLS) ===")
try:
    r = s.get("https://forex-data-feed.swissquote.com/public-quotes/bboquotes/instrument/XAU/USD", timeout=10, verify=False)
    data = r.json()
    ticks = data[0]["spreadProfilePrices"][0]
    bid = float(ticks["bid"])
    ask = float(ticks["ask"])
    mid = (bid + ask) / 2
    print(f"  Bid: {bid}, Ask: {ask}, Mid: {mid:.2f}")
except Exception as e:
    print(f"  FAILED: {e}")

# Test metals.live
print("\n=== metals.live (custom TLS) ===")
try:
    r = s.get("https://api.metals.live/v1/spot", timeout=10, verify=False)
    data = r.json()
    for item in data:
        if item.get("gold"):
            print(f"  Gold: {item['gold']}")
            break
except Exception as e:
    print(f"  FAILED: {e}")
