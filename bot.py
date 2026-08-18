import telebot
import yt_dlp
import os
import requests

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

# Database o'rniga oddiy dict
users = {}
channels = []
LIMIT = 20

def check_subscription(user_id):
    if not channels:
        return True
    for channel in channels:
        try:
            member = bot.get_chat_member(channel, user_id)
            if member.status in ['left', 'kicked']:
                return False
        except:
            return False
    return True

def get_subscribe_markup():
    markup = telebot.types.InlineKeyboardMarkup()
    for i, channel in enumerate(channels):
        markup.add(telebot.types.InlineKeyboardButton(f"📢 Kanal {i+1}", url=f"https://t.me/{channel.replace('@', '')}"))
    markup.add(telebot.types.InlineKeyboardButton("✅ Tekshirish", callback_data="check_sub"))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    user_id = message.chat.id
    if user_id not in users:
        users[user_id] = {"count": 0, "name": message.from_user.first_name}
    bot.send_message(user_id,
        f"Salom, {message.from_user.first_name}! 👋\n\n"
