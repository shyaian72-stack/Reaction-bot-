import logging
import os
import threading
from flask import Flask, jsonify
import telebot
from telebot import types
from telebot.apihelper import ApiTelegramException

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
)
log = logging.getLogger("auto_reaction_bot")

BOT_TOKEN = os.getenv("BOT_TOKEN", "").strip()
ADMIN_ID_RAW = os.getenv("ADMIN_ID", "").strip()

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is missing.")
if not ADMIN_ID_RAW:
    raise RuntimeError("ADMIN_ID environment variable is missing.")
try:
    ADMIN_ID = int(ADMIN_ID_RAW)
except ValueError as exc:
    raise RuntimeError("ADMIN_ID must be your numeric Telegram user ID.") from exc

bot = telebot.TeleBot(BOT_TOKEN)
app = Flask(__name__)

state = {
    "enabled": True,
    "last_error": None,
    "last_reaction": "🔥❤️‍🔥",
}

# Telegram Bot API can set only a limited number of reactions on one message.
# This bot intentionally sets ONE allowed emoji reaction per new channel post.
REACTION_EMOJI = "🔥❤️‍🔥"


def admin_keyboard():
    markup = types.InlineKeyboardMarkup(row_width=2)
    markup.add(
        types.InlineKeyboardButton("▶️ ON", callback_data="bot_on"),
        types.InlineKeyboardButton("⏸ OFF", callback_data="bot_off"),
        types.InlineKeyboardButton("📊 Status", callback_data="bot_status"),
    )
    return markup


def is_admin(message):
    return bool(message.from_user and message.from_user.id == ADMIN_ID)


@bot.message_handler(commands=["start", "admin"])
def start_handler(message):
    if not is_admin(message):
        bot.reply_to(message, "⛔ Admin only.")
        return
    bot.send_message(
        message.chat.id,
        "🤖 Auto Reaction Bot\\nChoose an option below.",
        reply_markup=admin_keyboard(),
    )


@bot.message_handler(commands=["on"])
def on_handler(message):
    if not is_admin(message):
        bot.reply_to(message, "⛔ Admin only.")
        return
    state["enabled"] = True
    bot.reply_to(message, "✅ Auto reaction is ON.", reply_markup=admin_keyboard())


@bot.message_handler(commands=["off"])
def off_handler(message):
    if not is_admin(message):
        bot.reply_to(message, "⏸ Auto reaction is OFF.")
        return
    state["enabled"] = False
    bot.reply_to(message, "⏸ Auto reaction is OFF.", reply_markup=admin_keyboard())


@bot.message_handler(commands=["status"])
def status_handler(message):
    if not is_admin(message):
        bot.reply_to(message, "⛔ Admin only.")
        return
    text = (
        f"Status: {'ON' if state['enabled'] else 'OFF'}\\n"
        f"Reaction: {REACTION_EMOJI}\\n"
        f"Last error: {state['last_error'] or 'None'}"
    )
    bot.reply_to(message, text, reply_markup=admin_keyboard())


@bot.callback_query_handler(func=lambda call: call.data in {"bot_on", "bot_off", "bot_status"})
def admin_callback(call):
    if not call.from_user or call.from_user.id != ADMIN_ID:
        bot.answer_callback_query(call.id, "Admin only.", show_alert=True)
        return
    if call.data == "bot_on":
        state["enabled"] = True
        text = "✅ Auto reaction is ON."
    elif call.data == "bot_off":
        state["enabled"] = False
        text = "⏸ Auto reaction is OFF."
    else:
        text = (
            f"Status: {'ON' if state['enabled'] else 'OFF'}\\n"
            f"Reaction: {REACTION_EMOJI}\\n"
            f"Last error: {state['last_error'] or 'None'}"
        )
    try:
        bot.answer_callback_query(call.id)
        bot.edit_message_text(
            text,
            chat_id=call.message.chat.id,
            message_id=call.message.message_id,
            reply_markup=admin_keyboard(),
        )
    except ApiTelegramException:
        bot.send_message(call.message.chat.id, text, reply_markup=admin_keyboard())


@bot.channel_post_handler(func=lambda message: True)
def channel_post_handler(message):
    if not state["enabled"]:
        return
    try:
        result = bot.set_message_reaction(
            chat_id=message.chat.id,
            message_id=message.message_id,
            reaction=[types.ReactionTypeEmoji(emoji=REACTION_EMOJI)],
            is_big=True,
        )
        state["last_error"] = None
        state["last_reaction"] = REACTION_EMOJI
        log.info(
            "Reaction request sent: channel=%s message_id=%s result=%s",
            message.chat.id, message.message_id, result,
        )
    except Exception as exc:
        state["last_error"] = str(exc)
        log.exception(
            "Could not react to channel post %s: %s",
            message.message_id, exc,
        )


@app.get("/")
def home():
    return "Telegram Auto Reaction Bot is running.", 200


@app.get("/health")
def health():
    return jsonify({
        "status": "ok",
        "bot_enabled": state["enabled"],
        "last_error": state["last_error"],
    }), 200


def run_web():
    port = int(os.getenv("PORT", "10000"))
    log.info("Starting health web server on port %s", port)
    app.run(host="0.0.0.0", port=port, use_reloader=False)


def run_bot():
    log.info("Starting Telegram polling.")
    # Remove a stale webhook before using long polling.
    try:
        bot.remove_webhook()
    except Exception:
        log.exception("Could not remove existing webhook.")
    bot.infinity_polling(
        skip_pending=True,
        timeout=30,
        long_polling_timeout=30,
        allowed_updates=["message", "callback_query", "channel_post"],
    )


if __name__ == "__main__":
    threading.Thread(target=run_web, daemon=True).start()
    run_bot()
