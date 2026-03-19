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
import asyncio
import logging
from datetime import datetime
from dotenv import load_dotenv
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from aiogram import Bot, Dispatcher, Router
from aiogram.types import Message, BotCommand
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

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

# Gemini key is loaded internally by signal_generator
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN', '')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID', '')
SIGNAL_INTERVAL = int(os.getenv('SIGNAL_INTERVAL_MINUTES', '15'))
TIMEFRAME = os.getenv('TIMEFRAME', '15m')
BOT_NAME = os.getenv('BOT_NAME', 'XAUUSD Scalp Signal')

# Admin IDs
_admin_raw = os.getenv('ADMIN_IDS', '')
ADMIN_IDS = [int(x.strip()) for x in _admin_raw.split(',') if x.strip().isdigit()]

# Aiogram router for admin commands
router = Router()


def validate_config():
    errors = []
    if not os.getenv('GEMINI_API_KEY', ''):
        errors.append("❌ GEMINI_API_KEY belum diisi di file .env")
    if not TELEGRAM_BOT_TOKEN or TELEGRAM_BOT_TOKEN == 'your_telegram_bot_token_here':
        errors.append("❌ TELEGRAM_BOT_TOKEN belum diisi di file .env")
    if not TELEGRAM_CHAT_ID or TELEGRAM_CHAT_ID == 'your_chat_id_here':
        errors.append("❌ TELEGRAM_CHAT_ID belum diisi di file .env")
    if errors:
        for err in errors:
            logger.error(err)
        return False
    return True


def run_signal():
    """Generate signal dan kirim ke Telegram (sync)"""
    logger.info("=" * 50)
    logger.info("🔄 Mulai generate signal XAUUSD...")
    logger.info("=" * 50)

    logger.info("📡 Mengambil data harga XAUUSD...")
    df = fetch_xauusd_data(timeframe=TIMEFRAME, lookback_days=7)
    if df.empty:
        logger.error("❌ Gagal mengambil data harga. Skip signal ini.")
        return

    logger.info(f"✅ Data diterima: {len(df)} candle, "
                f"Harga terakhir: {df['Close'].iloc[-1]:.2f}")

    logger.info("📊 Menghitung indikator teknikal...")
    indicators = calculate_all_indicators(df)
    logger.info(f"   RSI: {indicators['rsi']} | ADX: {indicators['adx']} | "
                f"ATR: {indicators['atr']} | BB Width: {indicators['bb_width']}")
    logger.info(f"   EMA Trend: {indicators.get('ema_trend')} | "
                f"Candle: {indicators.get('candle_pattern')} ({indicators.get('candle_bias')}) | "
                f"Momentum: {indicators.get('momentum_dir')}")
    logger.info(f"   S/R: Support={indicators.get('nearest_support')} | "
                f"Resistance={indicators.get('nearest_resistance')}")

    logger.info("🤖 Menganalisis dengan Gemini AI...")
    signal_result = generate_signal_with_gemini(indicators)
    if not signal_result:
        logger.error("❌ Gagal generate signal. Skip.")
        return

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

    message = format_signal_message(signal_data)

    logger.info(f"📣 SIGNAL: {signal_result['signal']} | "
                f"Price: {indicators['price']:.2f} | "
                f"SL: {signal_result['stop_loss']} | "
                f"TP1: {signal_result['tp1']}")

    success = send_telegram_message(TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID, message)
    if success:
        logger.info("✅ Signal berhasil dikirim ke Telegram!")
    else:
        logger.error("❌ Gagal mengirim signal ke Telegram")

    logger.info(f"⏰ Signal berikutnya dalam {SIGNAL_INTERVAL} menit\n")


# ==================== ADMIN BOT COMMANDS ====================

def _is_admin(user_id: int) -> bool:
    result = user_id in ADMIN_IDS
    logger.info(f"🔍 Admin check: user={user_id}, admins={ADMIN_IDS}, ok={result}")
    return result


@router.message(Command("start"))
async def cmd_start(message: Message):
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ Kamu bukan admin bot ini.")
        return
    await message.answer(
        f"👋 Halo <b>{message.from_user.first_name}</b>!\n\n"
        "🤖 <b>XAUUSD Scalp Signal Bot - Admin Panel</b>\n"
        "<code>=====================================</code>\n\n"
        "📋 <b>Commands:</b>\n"
        "/signal - 🚀 Generate & kirim signal sekarang\n"
        "/status - 📊 Cek status bot\n"
        "/help - ❓ Bantuan\n"
    )


@router.message(Command("signal"))
async def cmd_signal(message: Message):
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ Kamu bukan admin bot ini.")
        return
    await message.answer("🔄 <b>Generating signal...</b>\nMohon tunggu...")
    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, run_signal)
        await message.answer("✅ Signal berhasil dikirim ke channel!")
    except Exception as e:
        logger.error(f"Error manual signal: {e}")
        await message.answer(f"❌ Error: {e}")


@router.message(Command("status"))
async def cmd_status(message: Message):
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ Kamu bukan admin bot ini.")
        return
    await message.answer(
        "📊 <b>Bot Status</b>\n"
        "<code>====================</code>\n\n"
        f"🟢 <b>Status:</b> Running\n"
        f"📛 <b>Bot Name:</b> {BOT_NAME}\n"
        f"⏱️ <b>Interval:</b> {SIGNAL_INTERVAL} menit\n"
        f"📈 <b>Timeframe:</b> {TIMEFRAME}\n\n"
        "💡 Kirim /signal untuk generate signal manual"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ Kamu bukan admin bot ini.")
        return
    await message.answer(
        "❓ <b>Help - Admin Commands</b>\n"
        "<code>==========================</code>\n\n"
        "/signal - Generate & kirim signal sekarang\n"
        "/status - Lihat status bot\n"
        "/help - Tampilkan pesan ini\n\n"
        "📌 Hanya admin yang bisa akses command ini"
    )


# ==================== MAIN ====================

async def main():
    print("""
╔══════════════════════════════════════════════════╗
║       XAUUSD SCALP SIGNAL BOT                   ║
║       Powered by Gemini AI + Technical Analysis  ║
╚══════════════════════════════════════════════════╝
    """)

    if not validate_config():
        sys.exit(1)

    logger.info(f"⚙️  Timeframe: {TIMEFRAME}")
    logger.info(f"⚙️  Interval: setiap {SIGNAL_INTERVAL} menit")
    logger.info(f"⚙️  Bot Name: {BOT_NAME}")
    logger.info(f"⚙️  Admin IDs: {ADMIN_IDS}")

    # Setup aiogram bot + dispatcher
    bot = Bot(
        token=TELEGRAM_BOT_TOKEN,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML)
    )
    dp = Dispatcher()
    dp.include_router(router)

    # Hapus webhook lama & kill session lain agar tidak conflict
    await bot.delete_webhook(drop_pending_updates=True)
    logger.info("✅ Webhook cleared, siap polling...")

    # Set bot commands
    await bot.set_my_commands([
        BotCommand(command="signal", description="🚀 Generate & kirim signal sekarang"),
        BotCommand(command="status", description="📊 Cek status bot"),
        BotCommand(command="help", description="❓ Bantuan"),
    ])

    # Setup async scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        lambda: run_signal(),
        'interval',
        minutes=SIGNAL_INTERVAL,
        id='xauusd_signal_job',
        max_instances=1,
        misfire_grace_time=60,
    )

    # Jalankan signal pertama di background
    loop = asyncio.get_event_loop()
    loop.run_in_executor(None, run_signal)

    # Start scheduler
    scheduler.start()
    logger.info(f"📅 Scheduler aktif - signal setiap {SIGNAL_INTERVAL} menit")
    logger.info("🤖 Admin bot aktif! Kirim /signal ke bot untuk trigger manual")

    # Start polling (ini yang jalan terus)
    try:
        await dp.start_polling(bot, skip_updates=True)
    finally:
        scheduler.shutdown()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
