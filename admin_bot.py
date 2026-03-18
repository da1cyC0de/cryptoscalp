"""
Admin Bot Module - Powered by aiogram 3
Telegram bot handler untuk admin commands.
Admin bisa trigger signal manual, cek status, dll.
"""

import logging
import asyncio
import threading
from aiogram import Bot, Dispatcher, Router, F
from aiogram.types import Message, BotCommand
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties

logger = logging.getLogger(__name__)

router = Router()

# Global references (diset saat init)
_admin_ids: list = []
_signal_callback = None
_config: dict = {}


def _is_admin(user_id: int) -> bool:
    logger.info(f"🔍 Check admin: user_id={user_id}, admin_ids={_admin_ids}, match={user_id in _admin_ids}")
    return user_id in _admin_ids


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

    await message.answer(
        "🔄 <b>Generating signal...</b>\n"
        "Mohon tunggu, sedang mengambil data & analisis..."
    )

    try:
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, _signal_callback)
        await message.answer("✅ Signal berhasil dikirim ke channel!")
    except Exception as e:
        logger.error(f"Error saat manual signal: {e}")
        await message.answer(f"❌ Error: {e}")


@router.message(Command("status"))
async def cmd_status(message: Message):
    if not _is_admin(message.from_user.id):
        await message.answer("⛔ Kamu bukan admin bot ini.")
        return

    interval = _config.get('interval', 15)
    timeframe = _config.get('timeframe', '15m')
    bot_name = _config.get('bot_name', 'XAUUSD Scalp Signal')

    await message.answer(
        "📊 <b>Bot Status</b>\n"
        "<code>====================</code>\n\n"
        f"🟢 <b>Status:</b> Running\n"
        f"📛 <b>Bot Name:</b> {bot_name}\n"
        f"⏱️ <b>Interval:</b> {interval} menit\n"
        f"📈 <b>Timeframe:</b> {timeframe}\n\n"
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
        "/signal - Generate & kirim signal sekarang juga\n"
        "  → Tidak perlu tunggu interval\n"
        "  → Signal langsung dikirim ke channel\n\n"
        "/status - Lihat status bot saat ini\n"
        "/help - Tampilkan pesan ini\n\n"
        "📌 <b>Catatan:</b>\n"
        "• Hanya admin yang bisa akses command ini\n"
        "• Signal otomatis tetap jalan sesuai interval\n"
        "• Bot harus di-add ke channel sebagai admin"
    )


class AdminBot:
    """Telegram Admin Bot menggunakan aiogram 3"""

    def __init__(self, bot_token: str, admin_ids: list, signal_callback, config: dict):
        global _admin_ids, _signal_callback, _config
        _admin_ids = admin_ids
        _signal_callback = signal_callback
        _config = config
        self.bot_token = bot_token

    def start(self):
        """Jalankan admin bot di background thread"""
        def _run():
            async def _start():
                bot = Bot(
                    token=self.bot_token,
                    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
                )
                dp = Dispatcher()
                dp.include_router(router)

                # Set bot commands
                await bot.set_my_commands([
                    BotCommand(command="signal", description="🚀 Generate & kirim signal sekarang"),
                    BotCommand(command="status", description="📊 Cek status bot"),
                    BotCommand(command="help", description="❓ Bantuan"),
                ])

                logger.info("🤖 Admin bot (aiogram) started! Kirim /signal untuk trigger manual")
                await dp.start_polling(bot, skip_updates=True)

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(_start())

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread
