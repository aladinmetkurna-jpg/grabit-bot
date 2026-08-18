import telebot
import yt_dlp
import os
import tempfile
import shutil
import threading
import time

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_ID = os.environ.get("ADMIN_ID", "")

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN topilmadi!")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

users = {}
channels = []
LIMIT = 20

# Har bir user uchun bir vaqtning o'zida faqat 1 ta download
user_locks = {}
user_locks_global = threading.Lock()


def get_user_lock(uid):
    with user_locks_global:
        if uid not in user_locks:
            user_locks[uid] = threading.Lock()
        return user_locks[uid]


def check_sub(user_id):
    if not channels:
        return True

    for ch in channels:
        try:
            member = bot.get_chat_member(ch, user_id)

            if member.status in ["left", "kicked"]:
                return False

        except Exception:
            return False

    return True


def sub_markup():
    markup = telebot.types.InlineKeyboardMarkup()

    for i, ch in enumerate(channels):
        markup.add(
            telebot.types.InlineKeyboardButton(
                "Kanal " + str(i + 1),
                url="https://t.me/" + ch.replace("@", "")
            )
        )

    markup.add(
        telebot.types.InlineKeyboardButton(
            "✅ Tekshirish",
            callback_data="check_sub"
        )
    )

    return markup


# =========================
# START
# =========================

@bot.message_handler(commands=["start"])
def start(message):
    uid = message.chat.id

    if uid not in users:
        users[uid] = {"count": 0}

    markup = telebot.types.InlineKeyboardMarkup()

    markup.add(
        telebot.types.InlineKeyboardButton(
            "🤖 Botni guruhga qo'shish",
            url="https://t.me/GrabIt_downloader_bot?startgroup=true"
        )
    )

    text = (
        "👋🏻 Assalomu alaykum!\n\n"
        "Men Instagram, TikTok, YouTube va Pinterest'dan "
        "video va rasmlarni yuklab beraman.\n\n"
        "📥 Yuklash uchun shunchaki havolani yuboring.\n\n"
        "Bot guruhlarda ham ishlaydi."
    )

    bot.send_message(
        uid,
        text,
        reply_markup=markup
    )


# =========================
# ADMIN
# =========================

@bot.message_handler(commands=["admin"])
def admin(message):
    if str(message.chat.id) != str(ADMIN_ID):
        return

    markup = telebot.types.InlineKeyboardMarkup()

    markup.add(
        telebot.types.InlineKeyboardButton(
            "📊 Statistika",
            callback_data="stats"
        )
    )

    markup.add(
        telebot.types.InlineKeyboardButton(
            "➕ Kanal qo'shish",
            callback_data="add_ch"
        )
    )

    markup.add(
        telebot.types.InlineKeyboardButton(
            "📋 Kanallar",
            callback_data="list_ch"
        )
    )

    markup.add(
        telebot.types.InlineKeyboardButton(
            "📢 Xabar yuborish",
            callback_data="broadcast"
        )
    )

    markup.add(
        telebot.types.InlineKeyboardButton(
            "🔢 Limit o'zgartirish",
            callback_data="set_limit"
        )
    )

    bot.send_message(
        message.chat.id,
        "⚙️ Admin Panel",
        reply_markup=markup
    )


# =========================
# CALLBACK
# =========================

@bot.callback_query_handler(func=lambda call: True)
def cb(call):
    global LIMIT

    uid = call.message.chat.id

    if call.data == "check_sub":

        if check_sub(uid):

            if uid not in users:
                users[uid] = {"count": 0}

            users[uid]["count"] = 0

            bot.answer_callback_query(
                call.id,
                "✅ Tasdiqlandi!"
            )

            bot.send_message(
                uid,
                "✅ Obuna tasdiqlandi.\n\nLink yuboring."
            )

        else:

            bot.answer_callback_query(
                call.id,
                "❌ Hali obuna bo'lmagansiz!"
            )

    elif call.data == "stats":

        bot.answer_callback_query(call.id)

        bot.send_message(
            uid,
            "📊 Statistika\n\n"
            "Foydalanuvchilar: " + str(len(users)) + "\n"
            "Kanallar: " + str(len(channels)) + "\n"
            "Limit: " + str(LIMIT)
        )

    elif call.data == "add_ch":

        bot.answer_callback_query(call.id)

        msg = bot.send_message(
            uid,
            "Kanal username yozing:\n\n"
            "Misol: @kanalim"
        )

        bot.register_next_step_handler(
            msg,
            save_ch
        )

    elif call.data == "list_ch":

        bot.answer_callback_query(call.id)

        if not channels:

            bot.send_message(
                uid,
                "❌ Kanallar yo'q!"
            )

        else:

            markup = telebot.types.InlineKeyboardMarkup()

            for ch in channels:
                markup.add(
                    telebot.types.InlineKeyboardButton(
                        "🗑 O'chirish: " + ch,
                        callback_data="del_" + ch
                    )
                )

            bot.send_message(
                uid,
                "📋 Kanallar:",
                reply_markup=markup
            )

    elif call.data == "broadcast":

        bot.answer_callback_query(call.id)

        msg = bot.send_message(
            uid,
            "📢 Xabar yozing:"
        )

        bot.register_next_step_handler(
            msg,
            do_broadcast
        )

    elif call.data == "set_limit":

        bot.answer_callback_query(call.id)

        msg = bot.send_message(
            uid,
            "🔢 Yangi limitni yozing:"
        )

        bot.register_next_step_handler(
            msg,
            update_limit
        )

    elif call.data.startswith("del_"):

        ch = call.data.replace("del_", "", 1)

        if ch in channels:
            channels.remove(ch)

        bot.answer_callback_query(
            call.id,
            "O'chirildi!"
        )

        bot.send_message(
            uid,
            ch + " o'chirildi!"
        )


# =========================
# ADMIN FUNCTIONS
# =========================

def save_ch(message):
    ch = message.text.strip()

    if not ch.startswith("@"):
        ch = "@" + ch

    if ch not in channels:

        channels.append(ch)

        bot.send_message(
            message.chat.id,
            ch + " qo'shildi!"
        )

    else:

        bot.send_message(
            message.chat.id,
            "❌ Allaqachon mavjud!"
        )


def do_broadcast(message):
    text = message.text

    ok = 0

    for uid in list(users.keys()):

        try:
            bot.send_message(
                uid,
                text
            )

            ok += 1

        except Exception:
            pass

    bot.send_message(
        message.chat.id,
        str(ok) + " ta foydalanuvchiga yuborildi!"
    )


def update_limit(message):
    global LIMIT

    try:

        LIMIT = int(message.text)

        if LIMIT < 1:
            raise ValueError

        bot.send_message(
            message.chat.id,
            "✅ Limit " + str(LIMIT) + " ga o'zgartirildi!"
        )

    except Exception:

        bot.send_message(
            message.chat.id,
            "❌ To'g'ri raqam yozing!"
        )


# =========================
# FILE FINDER
# =========================

def find_downloaded_file(folder):
    """
    yt-dlp yaratgan yakuniy faylni topadi.
    .part, .ytdl kabi vaqtinchalik fayllarni hisobga olmaydi.
    """

    if not os.path.exists(folder):
        return None

    files = []

    for name in os.listdir(folder):

        path = os.path.join(folder, name)

        if not os.path.isfile(path):
            continue

        if name.endswith(".part"):
            continue

        if name.endswith(".ytdl"):
            continue

        if name.endswith(".part-Frag"):
            continue

        files.append(path)

    if not files:
        return None

    # Eng katta faylni tanlaymiz
    files.sort(
        key=lambda x: os.path.getsize(x),
        reverse=True
    )

    return files[0]


# =========================
# DOWNLOAD
# =========================

@bot.message_handler(func=lambda m: True)
def download(message):

    global LIMIT

    uid = message.chat.id

    if not message.text:
        return

    url = message.text.strip()

    if not url.startswith(("http://", "https://")):

        bot.send_message(
            uid,
            "🔗 Iltimos, link yuboring!"
        )

        return

    if uid not in users:
        users[uid] = {"count": 0}

    # LIMIT
    if users[uid]["count"] >= LIMIT:

        if not check_sub(uid):

            bot.send_message(
                uid,
                "⛔ Kunlik limitingiz tugadi.\n\n"
                "Davom etish uchun kanallarga obuna bo'ling:",
                reply_markup=sub_markup()
            )

            return

        else:

            users[uid]["count"] = 0

    # Bir userdan bir vaqtning o'zida 2 downloadni bloklash
    lock = get_user_lock(uid)

    if not lock.acquire(blocking=False):

        bot.send_message(
            uid,
            "⏳ Sizning boshqa linkingiz hali yuklanmoqda.\n"
            "Iltimos, tugashini kuting."
        )

        return

    msg = None
    temp_dir = None

    try:

        msg = bot.send_message(
            uid,
            "🔎 Qidirilmoqda..."
        )

        # Har download uchun alohida papka
        temp_dir = tempfile.mkdtemp(
            prefix="grabit_"
        )

        ydl_opts = {

            # VIDEO + AUDIO
            "format": "bv*+ba/b",

            # MP4 ga birlashtirish
            "merge_output_format": "mp4",

            # Unique filename
            "outtmpl": os.path.join(
                temp_dir,
                "%(id)s.%(ext)s"
            ),

            # Temporary files
            "paths": {
                "home": temp_dir,
                "temp": temp_dir
            },

            # Keraksiz loglarni kamaytirish
            "quiet": True,
            "no_warnings": True,

            # Parallel fragment download
            "concurrent_fragment_downloads": 4,

            # Retry
            "retries": 3,
            "fragment_retries": 3,

            # Network
            "socket_timeout": 30,

            # YouTube/Pinterest va boshqalar uchun
            "noplaylist": True,

            # Fayl nomlarini xavfsiz qilish
            "restrictfilenames": True,

            # Postprocessor
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4"
                }
            ]
        }

        # Instagram/TikTok/Pinterest kabi saytlar
        # uchun URL ni yuklash
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:

            info = ydl.extract_info(
                url,
                download=True
            )

        # Yuklangan yakuniy faylni topamiz
        filename = find_downloaded_file(
            temp_dir
        )

        if not filename:
            raise Exception(
                "Yuklangan fayl topilmadi."
            )

        filesize = os.path.getsize(filename)

        # Telegram bot limiti uchun
        # juda katta faylni yuborishga urinmaymiz
        if filesize > 49 * 1024 * 1024:

            bot.edit_message_text(
                "❌ Fayl juda katta.\n\n"
                "Telegram bot orqali 50 MB dan katta "
                "faylni yuborib bo'lmaydi.",
                uid,
                msg.message_id
            )

            return

        # Count faqat muvaffaqiyatli download'dan keyin
        users[uid]["count"] += 1

        lower = filename.lower()

        with open(filename, "rb") as f:

            if lower.endswith(
                (".mp4", ".webm", ".mkv", ".mov")
            ):

                bot.send_video(
                    uid,
                    f,
                    supports_streaming=True
                )

            elif lower.endswith(
                (
                    ".jpg",
                    ".jpeg",
                    ".png",
                    ".webp"
                )
            ):

                bot.send_photo(
                    uid,
                    f
                )

            elif lower.endswith(
                (
                    ".mp3",
                    ".m4a",
                    ".aac",
                    ".ogg",
                    ".opus"
                )
            ):

                bot.send_audio(
                    uid,
                    f
                )

            else:

                bot.send_document(
                    uid,
                    f
                )

        # Status xabarini o'chirish
        try:
            bot.delete_message(
                uid,
                msg.message_id
            )
        except Exception:
            pass

    except Exception as e:

        error = str(e)

        # Juda uzun error Telegramda noqulay
        if len(error) > 1500:
            error = error[-1500:]

        if msg:

            try:

                bot.edit_message_text(
                    "❌ Yuklab bo'lmadi:\n\n"
                    + error,
                    uid,
                    msg.message_id
                )

            except Exception:

                bot.send_message(
                    uid,
                    "❌ Yuklab bo'lmadi:\n\n"
                    + error
                )

        else:

            bot.send_message(
                uid,
                "❌ Yuklab bo'lmadi:\n\n"
                + error
            )

    finally:

        # Temporary folderni tozalash
        if temp_dir and os.path.exists(temp_dir):

            try:
                shutil.rmtree(
                    temp_dir,
                    ignore_errors=True
                )
            except Exception:
                pass

        # Lockni bo'shatish
        lock.release()


# =========================
# RUN
# =========================

print("GrabIt ishga tushdi!")

bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30
    )
