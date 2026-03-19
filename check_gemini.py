import httpx

API_KEY = 'AIzaSyDsXvBmEFQyyQiuy-rFDxU-Y3j9XXI2Maw'

# List available models
r = httpx.get(f'https://generativelanguage.googleapis.com/v1beta/models?key={API_KEY}', timeout=15)
print(f'Status: {r.status_code}')
if r.status_code == 200:
    models = r.json().get('models', [])
    for m in models:
        name = m.get('name', '')
        display = m.get('displayName', '')
        methods = m.get('supportedGenerationMethods', [])
        if 'generateContent' in methods:
            print(f'{name:55s} | {display}')
else:
    print(r.text[:500])

# Test a quick call
print('\n=== QUICK TEST: gemini-2.0-flash-lite ===')
try:
    r2 = httpx.post(
        f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash-lite:generateContent?key={API_KEY}',
        json={'contents': [{'parts': [{'text': 'Say hi in 3 words'}]}]},
        timeout=15
    )
    print(f'Status: {r2.status_code}')
    if r2.status_code == 200:
        text = r2.json()['candidates'][0]['content']['parts'][0]['text']
        print(f'Response: {text}')
    else:
        print(r2.text[:300])
except Exception as e:
    print(f'Error: {e}')

print('\n=== QUICK TEST: gemini-2.0-flash ===')
try:
    r3 = httpx.post(
        f'https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={API_KEY}',
        json={'contents': [{'parts': [{'text': 'Say hi in 3 words'}]}]},
        timeout=15
    )
    print(f'Status: {r3.status_code}')
    if r3.status_code == 200:
        text = r3.json()['candidates'][0]['content']['parts'][0]['text']
        print(f'Response: {text}')
    else:
        print(r3.text[:300])
except Exception as e:
    print(f'Error: {e}')
