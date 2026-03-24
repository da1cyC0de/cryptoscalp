"""
Telegram Sender Module
Mengirim signal ke Telegram channel/group via HTTP API (simple & reliable)
"""

import logging
import requests

logger = logging.getLogger(__name__)


def send_telegram_message(bot_token: str, chat_id: str, message: str) -> bool:
    """Kirim pesan ke Telegram via HTTP API. Simple, sync, no async issues."""
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": message,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    try:
        resp = requests.post(url, json=payload, timeout=30)
        data = resp.json()
        if data.get("ok"):
            return True
        logger.error(f"❌ Telegram API: {data.get('description')}")
        return False
    except Exception as e:
        logger.error(f"❌ Gagal kirim ke Telegram: {e}")
        return False


def format_signal_message(signal_data: dict) -> str:
    """
    Format signal data menjadi pesan Telegram yang cantik.
    Mirip format dari gambar contoh.
    """
    signal_type = signal_data.get('signal', 'NEUTRAL')
    price = signal_data.get('price', 0)
    stop_loss = signal_data.get('stop_loss', 0)
    tp1 = signal_data.get('tp1', 0)
    tp2 = signal_data.get('tp2', 0)
    tp3 = signal_data.get('tp3', 0)
    prob_up = signal_data.get('prob_up', 0)
    prob_down = signal_data.get('prob_down', 0)
    adx = signal_data.get('adx', 0)
    atr = signal_data.get('atr', 0)
    spread = signal_data.get('spread', 0)
    rsi = signal_data.get('rsi', 0)
    bb_width = signal_data.get('bb_width', 0)
    timestamp = signal_data.get('timestamp', '')
    bot_name = signal_data.get('bot_name', 'XAUUSD Scalp Signal')

    # Emoji berdasarkan signal
    if signal_type == 'BUY':
        signal_emoji = "🟢"
        signal_icon = "🚀"
    elif signal_type == 'SELL':
        signal_emoji = "🔴"
        signal_icon = "📉"
    else:
        signal_emoji = "🟡"
        signal_icon = "⏸️"

    # Strength bar
    strength = signal_data.get('strength', 0)
    filled = int(strength / 10)
    bar = "█" * filled + "░" * (10 - filled)

    message = f"""<b>XAUUSD - {bot_name}</b>
<code>========================</code>

{signal_icon} <b>Signal: {signal_type}</b>
💰 <b>Price:</b> {price:.2f}
🔴 <b>Stop Loss:</b> {stop_loss:.2f}
🎯 <b>TP1:</b> {tp1:.2f}
🎯 <b>TP2:</b> {tp2:.2f}
🎯 <b>TP3:</b> {tp3:.2f}

📊 <b>Prob Up:</b> {prob_up:.2f}% | <b>Prob Down:</b> {prob_down:.2f}%
📈 <b>Strength:</b> [{bar}] {strength:.0f}%

⚡ <b>ADX:</b> {adx} | <b>ATR:</b> {atr} | <b>Spread:</b> {spread}
📉 <b>RSI:</b> {rsi} | <b>BB Width:</b> {bb_width}

🕐 <b>Executed:</b> {timestamp}

<i>⚠️ Signal ini hanya referensi, bukan financial advice.
Selalu gunakan risk management yang baik.</i>"""

    return message
