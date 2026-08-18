import telebot
import yt_dlp
import os

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "")

bot = telebot.TeleBot(TELEGRAM_TOKEN)
users = {}
channels = []
LIMIT = 20

def check_sub(user_id):
    if not channels:
        return True
    for ch in channels:
        try:
            m = bot.get_chat_member(ch, user_id)
            if m.status in ['left', 'kicked']:
                return False
        except:
            return False
    return True

def sub_markup():
    markup = telebot.types.InlineKeyboardMarkup()
    for i, ch in enumerate(channels):
        markup.add(telebot.types.InlineKeyboardButton(
            "Kanal " + str(i+1),
            url="https://t.me/" + ch.replace("@", "")
        ))
    markup.add(telebot.types.InlineKeyboardButton(
        "Tekshirish", callback_data="check_sub"
    ))
    return markup

@bot.message_handler(commands=['start'])
def start(message):
    uid = message.chat.id
    if uid not in users:
        users[uid] = {"count": 0}
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton(
        "Botni guruhga qo'shish 🚀",
        url="https://t.me/GrabIt_downloader_bot?startgroup=true"
    ))
    bot.send_message(uid,
        "👋🏻 Assalomu aleykum. Men sizga Instagram, Tiktok, Youtube va Pinterestdan video va rasimlani yuklashda yordam beraman.\n\n"
        "• Videoni yuklashim uchun video yoki photoni havolasini menga jo'nating\n\n"
        "Bot guruhlarda ham ishlaydi, guruhda ham ishlatmoqchi bo'lsangiz tugmani bosing👇",
        reply_markup=markup
    )

@bot.message_handler(commands=['admin'])
def admin(message):
    if str(message.chat.id) != str(ADMIN_ID):
        return
    markup = telebot.types.InlineKeyboardMarkup()
    markup.add(telebot.types.InlineKeyboardButton("Statistika", callback_data="stats"))
    markup.add(telebot.types.InlineKeyboardButton("Kanal qoshish", callback_data="add_ch"))
    markup.add(telebot.types.InlineKeyboardButton("Kanallar", callback_data="list_ch"))
    markup.add(telebot.types.InlineKeyboardButton("Xabar yuborish", callback_data="broadcast"))
    markup.add(telebot.types.InlineKeyboardButton("Limit ozgartirish", callback_data="set_limit"))
    bot.send_message(message.chat.id, "Admin Panel", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: True)
def cb(call):
    global LIMIT
    uid = call.message.chat.id

    if call.data == "check_sub":
        if check_sub(uid):
            users[uid]["count"] = 0
            bot.answer_callback_query(call.id, "Tasdiqlandi!")
            bot.send_message(uid, "Obuna tasdiqlandi. Link yuboring.")
        else:
            bot.answer_callback_query(call.id, "Hali obuna bolmadingiz!")

    elif call.data == "stats":
        bot.answer_callback_query(call.id)
        bot.send_message(uid,
            "Foydalanuvchilar: " + str(len(users)) + "\n"
            "Kanallar: " + str(len(channels)) + "\n"
            "Limit: " + str(LIMIT)
        )

    elif call.data == "add_ch":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(uid, "Kanal username yozing:\nMisol: @kanalim")
        bot.register_next_step_handler(msg, save_ch)

    elif call.data == "list_ch":
        bot.answer_callback_query(call.id)
        if not channels:
            bot.send_message(uid, "Kanallar yoq!")
        else:
            markup = telebot.types.InlineKeyboardMarkup()
            for ch in channels:
                markup.add(telebot.types.InlineKeyboardButton(
                    "Ochirish: " + ch, callback_data="del_" + ch
                ))
            bot.send_message(uid, "Kanallar:", reply_markup=markup)

    elif call.data == "broadcast":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(uid, "Xabar yozing:")
        bot.register_next_step_handler(msg, do_broadcast)

    elif call.data == "set_limit":
        bot.answer_callback_query(call.id)
        msg = bot.send_message(uid, "Yangi limitni yozing:")
        bot.register_next_step_handler(msg, update_limit)

    elif call.data.startswith("del_"):
        ch = call.data.replace("del_", "")
        if ch in channels:
            channels.remove(ch)
        bot.answer_callback_query(call.id, "Ochirildi!")
        bot.send_message(uid, ch + " ochirildi!")

def save_ch(message):
    ch = message.text.strip()
    if not ch.startswith("@"):
        ch = "@" + ch
    if ch not in channels:
        channels.append(ch)
        bot.send_message(message.chat.id, ch + " qoshildi!")
    else:
        bot.send_message(message.chat.id, "Allaqachon bor!")

def do_broadcast(message):
    text = message.text
    ok = 0
    for uid in users:
        try:
            bot.send_message(uid, text)
            ok += 1
        except:
            pass
    bot.send_message(message.chat.id, str(ok) + " ta yuborildi!")

def update_limit(message):
    global LIMIT
    try:
        LIMIT = int(message.text)
        bot.send_message(message.chat.id, "Limit " + str(LIMIT) + " ga ozgartirildi!")
    except:
        bot.send_message(message.chat.id, "Raqam yozing!")

@bot.message_handler(func=lambda m: True)
def download(message):
    global LIMIT
    uid = message.chat.id
    url = message.text.strip()

    if not url.startswith("http"):
        bot.send_message(uid, "Link yuboring!")
        return

    if uid not in users:
        users[uid] = {"count": 0}

    if users[uid]["count"] >= LIMIT:
        if not check_sub(uid):
            bot.send_message(uid,
                "Kunlik limitingiz tugadi.\n\n"
                "Davom etish uchun kanallarga obuna bo'ling:",
                reply_markup=sub_markup()
            )
            return
        else:
            users[uid]["count"] = 0

    msg = bot.send_message(uid, "Yuklanmoqda...")

    try:
        ydl_opts = {
            'format': 'best[filesize<45M]/worst',
            'outtmpl': '/tmp/%(title)s.%(ext)s',
            'quiet': True,
            'merge_output_format': 'mp4',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info)

        users[uid]["count"] += 1

        with open(filename, 'rb') as f:
            if filename.endswith(('.mp4', '.webm', '.mkv')):
                bot.send_video(uid, f)
            elif filename.endswith(('.jpg', '.jpeg', '.png', '.webp')):
                bot.send_photo(uid, f)
            elif filename.endswith(('.mp3', '.m4a', '.ogg')):
                bot.send_audio(uid, f)
            else:
                bot.send_document(uid, f)

        os.remove(filename)
        bot.delete_message(uid, msg.message_id)

    except Exception as e:
        bot.edit_message_text("Yuklab bo'lmadi: " + str(e), uid, msg.message_id)

print("GrabIt ishga tushdi!")
bot.polling(none_stop=True)
