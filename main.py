"""
XAUUSD Scalp Signal Bot
========================
Bot otomatis untuk generate signal scalping XAUUSD
menggunakan Gemini AI + Technical Analysis
dan mengirimnya ke Telegram.

Cara pakai:
1. Isi file .env dengan API key Gemini dan Telegram bot token
2. Install: pip install -r requirements.txt
3. Jalankan: python main.py
"""

import os
import sys
import logging
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.schedulers.blocking import BlockingScheduler

from price_fetcher import fetch_xauusd_data, get_spread_estimate
from indicators import calculate_all_indicators
from signal_generator import generate_signal_with_gemini
from telegram_sender import send_telegram_message, format_signal_message

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s | %(levelname)s | %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('xauusd_signal.log', encoding='utf-8')
    ]
)
logger = logging.getLogger(__name__)


# Load environment variables
load_dotenv()

GEMINI_API_KEY = os.getenv('GEMINI_API_KEY', '')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
SIGNAL_INTERVAL = int(os.getenv('SIGNAL_INTERVAL_MINUTES', '15'))
TIMEFRAME = os.getenv('TIMEFRAME', '15m')
BOT_NAME = os.getenv('BOT_NAME', 'XAUUSD Scalp Signal')


def validate_config():
    """Validasi semua konfigurasi sudah diisi"""
    errors = []
    if not GEMINI_API_KEY or GEMINI_API_KEY == 'your_gemini_api_key_here':
        errors.append("❌ GEMINI_API_KEY belum diisi di file .env")
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'your_telegram_bot_token_here':
        errors.append("❌ TELEGRAM_BOT_TOKEN belum diisi di file .env")
    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == 'your_chat_id_here':
        errors.append("❌ TELEGRAM_CHAT_ID belum diisi di file .env")

    if errors:
        logger.error("="*50)
        logger.error("KONFIGURASI BELUM LENGKAP!")
        logger.error("="*50)
        for err in errors:
            logger.error(err)
        logger.error("")
        logger.error("Cara mendapatkan:")
        logger.error("1. Gemini API Key: https://aistudio.google.com/apikey")
        logger.error("2. Telegram Bot Token: Chat @BotFather di Telegram")
        logger.error("3. Chat ID: Chat @userinfobot atau @getidsbot di Telegram")
        logger.error("="*50)
        return False
    return True


def run_signal():
    """
    Fungsi utama yang dijalankan setiap interval:
    1. Ambil data harga XAUUSD
    2. Hitung indikator teknikal
    3. Analisis dengan Gemini AI
    4. Kirim signal ke Telegram
    """
    logger.info("="*50)
    logger.info("🔄 Mulai generate signal XAUUSD...")
    logger.info("="*50)

    # Step 1: Ambil data harga
    logger.info("📡 Mengambil data harga XAUUSD...")
    df = fetch_xauusd_data(timeframe=TIMEFRAME, lookback_days=7)

    if df.empty:
        logger.error("❌ Gagal mengambil data harga. Skip signal ini.")
        return

    logger.info(f"✅ Data diterima: {len(df)} candle, "
                f"Harga terakhir: {df['Close'].iloc[-1]:.2f}")

    # Step 2: Hitung indikator teknikal
    logger.info("📊 Menghitung indikator teknikal...")
    indicators = calculate_all_indicators(df)
    logger.info(f"   RSI: {indicators['rsi']} | ADX: {indicators['adx']} | "
                f"ATR: {indicators['atr']} | BB Width: {indicators['bb_width']}")

    # Step 3: Analisis dengan Gemini AI
    logger.info("🤖 Menganalisis dengan Gemini AI...")
    signal_result = generate_signal_with_gemini(indicators, GEMINI_API_KEY)

    if not signal_result:
        logger.error("❌ Gagal generate signal. Skip.")
        return

    # Step 4: Siapkan data signal lengkap
    spread = get_spread_estimate()
    now = datetime.now().strftime("%m-%d-%Y %H:%M:%S")

    signal_data = {
        'signal': signal_result['signal'],
        'price': indicators['price'],
        'stop_loss': signal_result['stop_loss'],
        'tp1': signal_result['tp1'],
        'tp2': signal_result['tp2'],
        'tp3': signal_result['tp3'],
        'prob_up': signal_result['prob_up'],
        'prob_down': signal_result['prob_down'],
        'strength': signal_result['strength'],
        'adx': indicators['adx'],
        'atr': indicators['atr'],
        'spread': spread,
        'rsi': indicators['rsi'],
        'bb_width': indicators['bb_width'],
        'timestamp': now,
        'bot_name': BOT_NAME,
    }

    # Step 5: Format dan kirim ke Telegram
    message = format_signal_message(signal_data)

    logger.info(f"\n{'='*50}")
    logger.info(f"📣 SIGNAL: {signal_result['signal']}")
    logger.info(f"💰 Price: {indicators['price']:.2f}")
    logger.info(f"🛑 SL: {signal_result['stop_loss']}")
    logger.info(f"🎯 TP1: {signal_result['tp1']} | TP2: {signal_result['tp2']} | TP3: {signal_result['tp3']}")
    logger.info(f"📈 Prob Up: {signal_result['prob_up']}% | Down: {signal_result['prob_down']}%")
    logger.info(f"{'='*50}")

    success = send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message)
    if success:
        logger.info("✅ Signal berhasil dikirim ke Telegram!")
    else:
        logger.error("❌ Gagal mengirim signal ke Telegram")
        # Print message ke console sebagai backup
        logger.info(f"\n{message}")

    logger.info(f"⏰ Signal berikutnya dalam {SIGNAL_INTERVAL} menit\n")


def main():
    """Entry point utama"""
    print("""
╔══════════════════════════════════════════════════╗
║       XAUUSD SCALP SIGNAL BOT                   ║
║       Powered by Gemini AI + Technical Analysis  ║
╚══════════════════════════════════════════════════╝
    """)

    # Validasi konfigurasi
    if not validate_config():
        sys.exit(1)

    logger.info(f"⚙️  Timeframe: {TIMEFRAME}")
    logger.info(f"⚙️  Interval: setiap {SIGNAL_INTERVAL} menit")
    logger.info(f"⚙️  Bot Name: {BOT_NAME}")
    logger.info("")

    # Jalankan signal pertama langsung
    logger.info("🚀 Menjalankan signal pertama...")
    run_signal()

    # Schedule signal berikutnya
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_signal,
        'interval',
        minutes=SIGNAL_INTERVAL,
        id='xauusd_signal_job',
        max_instances=1,
        misfire_grace_time=60
    )

    logger.info(f"📅 Scheduler aktif - signal setiap {SIGNAL_INTERVAL} menit")
    logger.info("   Tekan Ctrl+C untuk berhenti\n")

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        logger.info("\n🛑 Bot dihentikan oleh user")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
