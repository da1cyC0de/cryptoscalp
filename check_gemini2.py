import httpx

API_KEY = 'AIzaSyDsXvBmEFQyyQiuy-rFDxU-Y3j9XXI2Maw'

# Test newer models that might have separate quotas
models_to_test = [
    'gemini-2.5-flash',
    'gemini-2.5-flash-lite', 
    'gemini-3-flash-preview',
    'gemini-3-pro-preview',
    'gemini-3.1-flash-lite-preview',
]

for model in models_to_test:
    try:
        r = httpx.post(
            f'https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={API_KEY}',
            json={'contents': [{'parts': [{'text': 'Say hi'}]}]},
            timeout=15
        )
        status = r.status_code
        if status == 200:
            text = r.json()['candidates'][0]['content']['parts'][0]['text']
            print(f'✅ {model:45s} | {status} | {text[:50]}')
        else:
            err = r.json().get('error', {}).get('message', '')[:80]
            print(f'❌ {model:45s} | {status} | {err}')
    except Exception as e:
        print(f'❌ {model:45s} | ERR | {str(e)[:60]}')
