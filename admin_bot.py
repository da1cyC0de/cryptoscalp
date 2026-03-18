"""
Admin Bot Module
Telegram bot handler untuk admin commands.
Admin bisa trigger signal manual, cek status, ubah interval, dll.
"""

import logging
import threading
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
)

logger = logging.getLogger(__name__)


class AdminBot:
    """Telegram Admin Bot untuk kontrol signal bot"""

    def __init__(self, bot_token: str, admin_ids: list, signal_callback, config: dict):
        """
        Args:
            bot_token: Telegram bot token
            admin_ids: list of admin user IDs yang boleh akses
            signal_callback: fungsi run_signal() dari main.py
            config: dict config (interval, timeframe, dll)
        """
        self.bot_token = bot_token
        self.admin_ids = admin_ids
        self.signal_callback = signal_callback
        self.config = config
        self.app = None
        self._is_running = False

    def _is_admin(self, user_id: int) -> bool:
        """Cek apakah user adalah admin"""
        return user_id in self.admin_ids

    async def cmd_start(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler /start"""
        user = update.effective_user
        if not self._is_admin(user.id):
            await update.message.reply_text("⛔ Kamu bukan admin bot ini.")
            return

        await update.message.reply_text(
            f"👋 Halo <b>{user.first_name}</b>!\n\n"
            "🤖 <b>XAUUSD Scalp Signal Bot - Admin Panel</b>\n"
            "<code>=====================================</code>\n\n"
            "📋 <b>Commands:</b>\n"
            "/signal - 🚀 Generate & kirim signal sekarang\n"
            "/status - 📊 Cek status bot\n"
            "/help - ❓ Bantuan\n",
            parse_mode="HTML"
        )

    async def cmd_signal(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler /signal - Generate signal manual"""
        user = update.effective_user
        if not self._is_admin(user.id):
            await update.message.reply_text("⛔ Kamu bukan admin bot ini.")
            return

        await update.message.reply_text(
            "🔄 <b>Generating signal...</b>\n"
            "Mohon tunggu, sedang mengambil data & analisis...",
            parse_mode="HTML"
        )

        try:
            # Jalankan signal di thread terpisah supaya tidak block bot
            thread = threading.Thread(target=self.signal_callback)
            thread.start()
            thread.join(timeout=120)  # Max 2 menit

            if thread.is_alive():
                await update.message.reply_text("⚠️ Signal generation timeout (>2 menit)")
            else:
                await update.message.reply_text("✅ Signal berhasil dikirim ke channel!")

        except Exception as e:
            logger.error(f"Error saat manual signal: {e}")
            await update.message.reply_text(f"❌ Error: {e}")

    async def cmd_status(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler /status - Cek status bot"""
        user = update.effective_user
        if not self._is_admin(user.id):
            await update.message.reply_text("⛔ Kamu bukan admin bot ini.")
            return

        interval = self.config.get('interval', 15)
        timeframe = self.config.get('timeframe', '15m')
        bot_name = self.config.get('bot_name', 'XAUUSD Scalp Signal')

        await update.message.reply_text(
            "📊 <b>Bot Status</b>\n"
            "<code>====================</code>\n\n"
            f"🟢 <b>Status:</b> Running\n"
            f"📛 <b>Bot Name:</b> {bot_name}\n"
            f"⏱️ <b>Interval:</b> {interval} menit\n"
            f"📈 <b>Timeframe:</b> {timeframe}\n\n"
            "💡 Kirim /signal untuk generate signal manual",
            parse_mode="HTML"
        )

    async def cmd_help(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handler /help"""
        user = update.effective_user
        if not self._is_admin(user.id):
            await update.message.reply_text("⛔ Kamu bukan admin bot ini.")
            return

        await update.message.reply_text(
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
            "• Bot harus di-add ke channel sebagai admin",
            parse_mode="HTML"
        )

    async def _post_init(self, application):
        """Set bot commands setelah init"""
        commands = [
            BotCommand("signal", "🚀 Generate & kirim signal sekarang"),
            BotCommand("status", "📊 Cek status bot"),
            BotCommand("help", "❓ Bantuan"),
        ]
        await application.bot.set_my_commands(commands)

    def start(self):
        """Jalankan admin bot di background thread"""
        def _run():
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

            self.app = (
                ApplicationBuilder()
                .token(self.bot_token)
                .post_init(self._post_init)
                .build()
            )

            # Register handlers
            self.app.add_handler(CommandHandler("start", self.cmd_start))
            self.app.add_handler(CommandHandler("signal", self.cmd_signal))
            self.app.add_handler(CommandHandler("status", self.cmd_status))
            self.app.add_handler(CommandHandler("help", self.cmd_help))

            logger.info("🤖 Admin bot started! Kirim /signal di chat bot untuk trigger manual")
            self._is_running = True

            loop.run_until_complete(self.app.run_polling(drop_pending_updates=True))

        thread = threading.Thread(target=_run, daemon=True)
        thread.start()
        return thread
