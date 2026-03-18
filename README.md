# 🏆 XAUUSD Scalp Signal Bot

Bot otomatis untuk generate signal scalping XAUUSD menggunakan **Gemini AI** + **Technical Analysis**, dan mengirim hasilnya ke **Telegram**.

## 📋 Fitur

- ✅ Analisis teknikal otomatis (RSI, ADX, ATR, Bollinger Bands, MACD, Stochastic, EMA)
- ✅ Signal generator berbasis AI (Google Gemini)
- ✅ Fallback rule-based signal jika Gemini gagal
- ✅ Kirim signal otomatis ke Telegram
- ✅ Scheduler - signal dikirim setiap X menit
- ✅ Format signal yang rapi dan informatif
- ✅ Probabilitas BUY/SELL
- ✅ 3 level Take Profit + Stop Loss

## 🚀 Cara Install

### 1. Install Python Dependencies

```bash
pip install -r requirements.txt
```

### 2. Dapatkan API Keys

#### Gemini API Key
1. Buka https://aistudio.google.com/apikey
2. Klik "Create API Key"
3. Copy API key

#### Telegram Bot Token
1. Buka Telegram, cari **@BotFather**
2. Kirim `/newbot`
3. Ikuti instruksi, dapatkan bot token
4. Tambahkan bot ke channel/group kamu

#### Telegram Chat ID
1. Buka Telegram, cari **@userinfobot** atau **@getidsbot**
2. Untuk channel: forward pesan dari channel ke bot tersebut
3. Untuk group: tambahkan bot ke group, kirim pesan, lalu gunakan:
   ```
   https://api.telegram.org/bot<TOKEN>/getUpdates
   ```

### 3. Konfigurasi

Edit file `.env` dan isi:

```env
GEMINI_API_KEY=your_gemini_api_key_here
TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
TELEGRAM_CHAT_ID=your_chat_id_here
SIGNAL_INTERVAL_MINUTES=15
TIMEFRAME=15m
BOT_NAME=XAUUSD Scalp Signal
```

### 4. Jalankan Bot

```bash
python main.py
```

## 📊 Contoh Output Signal

```
XAUUSD - XAUUSD Scalp Signal
========================

🚀 Signal: BUY
💰 Price: 3045.20
🔴 Stop Loss: 3038.50
🎯 TP1: 3049.67
🎯 TP2: 3054.14
🎯 TP3: 3056.37

📊 Prob Up: 78.50% | Prob Down: 12.30%
📈 Strength: [███████░░░] 70%

⚡ ADX: 28.45 | ATR: 4.47 | Spread: 0.30
📉 RSI: 42.15 | BB Width: 0.2304

🕐 Executed: 03-19-2026 14:30:00
```

## 📁 Struktur File

```
xauusd/
├── .env                  # Konfigurasi API keys
├── main.py               # Entry point utama
├── price_fetcher.py      # Ambil data harga XAUUSD
├── indicators.py         # Hitung indikator teknikal
├── signal_generator.py   # Gemini AI signal analysis
├── telegram_sender.py    # Kirim ke Telegram
├── requirements.txt      # Python dependencies
└── README.md             # Dokumentasi
```

## ⚠️ Disclaimer

Signal ini hanya untuk referensi dan edukasi. **Bukan financial advice.**
Selalu gunakan risk management yang baik dan jangan trading dengan uang yang tidak siap Anda kehilangan.

## 🔧 Konfigurasi Timeframe

| Timeframe | Cocok untuk |
|-----------|-------------|
| `1m`      | Ultra-scalp (sangat cepat) |
| `5m`      | Scalping agresif |
| `15m`     | Scalping normal (recommended) |
| `1h`      | Intraday trading |
