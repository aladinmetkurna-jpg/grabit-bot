import os
import tempfile
import shutil
import threading

import telebot
import yt_dlp


# =========================================================
# SOZLAMALAR
# =========================================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_USERNAME = os.environ.get("ADMIN_USERNAME", "").replace("@", "").lower()

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN topilmadi!")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

users = {}
channels = []
LIMIT = 20

# Bir foydalanuvchining bir vaqtning o'zida
# ikkita download boshlashini oldini oladi.
user_locks = {}
locks_global = threading.Lock()


# =========================================================
# USER LOCK
# =========================================================

def get_user_lock(user_id):
    with locks_global:
        if user_id not in user_locks:
            user_locks[user_id] = threading.Lock()

        return user_locks[user_id]


# =========================================================
# ADMIN TEKSHIRISH
# =========================================================

def is_admin(message):
    username = message.from_user.username

    if not username:
        return False

    return username.lower() == ADMIN_USERNAME


# =========================================================
# OBUNA TEKSHIRISH
# =========================================================

def check_sub(user_id):

    if not channels:
        return True

    for channel in channels:

        try:
            member = bot.get_chat_member(
                channel,
                user_id
            )

            if member.status in ["left", "kicked"]:
                return False

        except Exception:
            return False

    return True


def sub_markup():

    markup = telebot.types.InlineKeyboardMarkup()

    for i, channel in enumerate(channels):

        markup.add(
            telebot.types.InlineKeyboardButton(
                "Kanal " + str(i + 1),
                url="https://t.me/" + channel.replace("@", "")
            )
        )

    markup.add(
        telebot.types.InlineKeyboardButton(
            "✅ Tekshirish",
            callback_data="check_sub"
        )
    )

    return markup


# =========================================================
# START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):

    user_id = message.chat.id

    if user_id not in users:
        users[user_id] = {
            "count": 0
        }

    markup = telebot.types.InlineKeyboardMarkup()

    markup.add(
        telebot.types.InlineKeyboardButton(
            "🤖 Botni guruhga qo'shish",
            url="https://t.me/GrabIt_downloader_bot?startgroup=true"
        )
    )

    bot.send_message(
        user_id,
        "👋🏻 Assalomu alaykum!\n\n"
        "Instagram, TikTok, YouTube va Pinterest "
        "havolalaridan video yuklab beraman.\n\n"
        "📥 Linkni yuboring.",
        reply_markup=markup
    )


# =========================================================
# ADMIN PANEL
# =========================================================

@bot.message_handler(commands=["admin"])
def admin(message):

    if not is_admin(message):
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
            "🔢 Limit",
            callback_data="set_limit"
        )
    )

    bot.send_message(
        message.chat.id,
        "⚙️ <b>Admin Panel</b>",
        parse_mode="HTML",
        reply_markup=markup
    )


# =========================================================
# CALLBACK
# =========================================================

@bot.callback_query_handler(func=lambda call: True)
def callback(call):

    global LIMIT

    user_id = call.message.chat.id

    # ---------------------------------
    # OBUNA
    # ---------------------------------

    if call.data == "check_sub":

        if check_sub(user_id):

            if user_id not in users:
                users[user_id] = {"count": 0}

            users[user_id]["count"] = 0

            bot.answer_callback_query(
                call.id,
                "✅ Tasdiqlandi!"
            )

            bot.send_message(
                user_id,
                "✅ Obuna tasdiqlandi.\n\n"
                "Link yuboring."
            )

        else:

            bot.answer_callback_query(
                call.id,
                "❌ Hali obuna bo'lmagansiz!"
            )

        return

    # ---------------------------------
    # ADMIN CALLBACKLARI
    # ---------------------------------

    if not is_admin(call.message):
        bot.answer_callback_query(
            call.id,
            "❌ Ruxsat yo'q!"
        )
        return

    # ---------------------------------
    # STATISTIKA
    # ---------------------------------

    if call.data == "stats":

        bot.answer_callback_query(call.id)

        bot.send_message(
            user_id,
            "📊 <b>Statistika</b>\n\n"
            "👥 Foydalanuvchilar: "
            + str(len(users))
            + "\n"
            "📢 Kanallar: "
            + str(len(channels))
            + "\n"
            "🔢 Limit: "
            + str(LIMIT),
            parse_mode="HTML"
        )

    # ---------------------------------
    # KANAL QO'SHISH
    # ---------------------------------

    elif call.data == "add_ch":

        bot.answer_callback_query(call.id)

        msg = bot.send_message(
            user_id,
            "Kanal username yozing:\n\n"
            "Misol: @kanalim"
        )

        bot.register_next_step_handler(
            msg,
            save_channel
        )

    # ---------------------------------
    # KANALLAR
    # ---------------------------------

    elif call.data == "list_ch":

        bot.answer_callback_query(call.id)

        if not channels:

            bot.send_message(
                user_id,
                "❌ Kanallar yo'q!"
            )

        else:

            markup = telebot.types.InlineKeyboardMarkup()

            for channel in channels:

                markup.add(
                    telebot.types.InlineKeyboardButton(
                        "🗑 " + channel,
                        callback_data="delete:" + channel
                    )
                )

            bot.send_message(
                user_id,
                "📋 Kanallar:",
                reply_markup=markup
            )

    # ---------------------------------
    # BROADCAST
    # ---------------------------------

    elif call.data == "broadcast":

        bot.answer_callback_query(call.id)

        msg = bot.send_message(
            user_id,
            "📢 Yuboriladigan xabarni yozing:"
        )

        bot.register_next_step_handler(
            msg,
            broadcast
        )

    # ---------------------------------
    # LIMIT
    # ---------------------------------

    elif call.data == "set_limit":

        bot.answer_callback_query(call.id)

        msg = bot.send_message(
            user_id,
            "🔢 Yangi limitni yozing:"
        )

        bot.register_next_step_handler(
            msg,
            set_limit
        )

    # ---------------------------------
    # KANAL O'CHIRISH
    # ---------------------------------

    elif call.data.startswith("delete:"):

        channel = call.data.split(":", 1)[1]

        if channel in channels:
            channels.remove(channel)

        bot.answer_callback_query(
            call.id,
            "O'chirildi!"
        )

        bot.send_message(
            user_id,
            channel + " o'chirildi!"
        )


# =========================================================
# KANAL SAQLASH
# =========================================================

def save_channel(message):

    if not is_admin(message):
        return

    channel = message.text.strip()

    if not channel.startswith("@"):
        channel = "@" + channel

    if channel not in channels:

        channels.append(channel)

        bot.send_message(
            message.chat.id,
            channel + " qo'shildi!"
        )

    else:

        bot.send_message(
            message.chat.id,
            "❌ Bu kanal allaqachon mavjud!"
        )


# =========================================================
# BROADCAST
# =========================================================

def broadcast(message):

    if not is_admin(message):
        return

    text = message.text
    sent = 0

    for user_id in list(users.keys()):

        try:

            bot.send_message(
                user_id,
                text
            )

            sent += 1

        except Exception:
            pass

    bot.send_message(
        message.chat.id,
        str(sent) + " ta foydalanuvchiga yuborildi!"
    )


# =========================================================
# LIMIT
# =========================================================

def set_limit(message):

    global LIMIT

    if not is_admin(message):
        return

    try:

        value = int(message.text)

        if value < 1:
            raise ValueError

        LIMIT = value

        bot.send_message(
            message.chat.id,
            "✅ Limit "
            + str(LIMIT)
            + " ga o'zgartirildi!"
        )

    except Exception:

        bot.send_message(
            message.chat.id,
            "❌ Faqat raqam yozing!"
        )


# =========================================================
# FAYLNI TOPISH
# =========================================================

def find_file(folder):

    if not os.path.exists(folder):
        return None

    files = []

    for name in os.listdir(folder):

        path = os.path.join(
            folder,
            name
        )

        if not os.path.isfile(path):
            continue

        if name.endswith(
            (
                ".part",
                ".ytdl"
            )
        ):
            continue

        files.append(path)

    if not files:
        return None

    # Avval MP4
    mp4 = [
        f for f in files
        if f.lower().endswith(".mp4")
    ]

    if mp4:

        return max(
            mp4,
            key=os.path.getsize
        )

    return max(
        files,
        key=os.path.getsize
    )


# =========================================================
# DOWNLOAD
# =========================================================

@bot.message_handler(
    func=lambda message: True
)
def download(message):

    user_id = message.chat.id

    if not message.text:
        return

    url = message.text.strip()

    if not url.startswith(
        (
            "http://",
            "https://"
        )
    ):
        return

    if user_id not in users:

        users[user_id] = {
            "count": 0
        }

    # ---------------------------------
    # LIMIT
    # ---------------------------------

    if users[user_id]["count"] >= LIMIT:

        if not check_sub(user_id):

            bot.send_message(
                user_id,
                "⛔ Kunlik limitingiz tugadi.\n\n"
                "Davom etish uchun kanallarga "
                "obuna bo'ling:",
                reply_markup=sub_markup()
            )

            return

        users[user_id]["count"] = 0

    # ---------------------------------
    # LOCK
    # ---------------------------------

    lock = get_user_lock(user_id)

    if not lock.acquire(
        blocking=False
    ):

        bot.send_message(
            user_id,
            "⏳ Avvalgi video yuklanmoqda."
        )

        return

    status_message = None
    temp_dir = None

    try:

        status_message = bot.send_message(
            user_id,
            "🔎 Qidirilmoqda..."
        )

        temp_dir = tempfile.mkdtemp(
            prefix="grabit_"
        )

        # ---------------------------------
        # YT-DLP
        # ---------------------------------

        ydl_opts = {

            # VIDEO + AUDIO
            "format": (
                "bestvideo*+bestaudio/"
                "best"
            ),

            # MP4
            "merge_output_format": "mp4",

            # Fayl nomi
            "outtmpl": os.path.join(
                temp_dir,
                "%(id)s.%(ext)s"
            ),

            # Temporary folder
            "paths": {
                "home": temp_dir,
                "temp": temp_dir
            },

            "noplaylist": True,

            "quiet": True,
            "no_warnings": True,

            "retries": 5,
            "fragment_retries": 5,

            "socket_timeout": 60,

            "restrictfilenames": True,

            # FFmpeg orqali video + audio
            "postprocessors": [
                {
                    "key": "FFmpegVideoConvertor",
                    "preferedformat": "mp4"
                }
            ]
        }

        with yt_dlp.YoutubeDL(
            ydl_opts
        ) as ydl:

            ydl.extract_info(
                url,
                download=True
            )

        # ---------------------------------
        # FAYL
        # ---------------------------------

        filename = find_file(
            temp_dir
        )

        if not filename:

            raise Exception(
                "Video topilmadi."
            )

        filesize = os.path.getsize(
            filename
        )

        # Telegram Bot API cheklovi
        if filesize > 49 * 1024 * 1024:

            bot.edit_message_text(
                "❌ Video juda katta "
                "(50 MB dan oshgan).",
                user_id,
                status_message.message_id
            )

            return

        # ---------------------------------
        # YUBORISH
        # ---------------------------------

        with open(
            filename,
            "rb"
        ) as video:

            bot.send_video(
                user_id,
                video,
                supports_streaming=True
            )

        users[user_id]["count"] += 1

        # Statusni o'chirish
        try:

            bot.delete_message(
                user_id,
                status_message.message_id
            )

        except Exception:
            pass

    except Exception as error:

        text = str(error)

        if len(text) > 1200:
            text = text[-1200:]

        try:

            bot.edit_message_text(
                "❌ Yuklab bo'lmadi:\n\n"
                + text,
                user_id,
                status_message.message_id
            )

        except Exception:

            bot.send_message(
                user_id,
                "❌ Yuklab bo'lmadi."
            )

    finally:

        # Temporary fayllarni o'chirish
        if temp_dir:

            shutil.rmtree(
                temp_dir,
                ignore_errors=True
            )

        lock.release()


# =========================================================
# START BOT
# =========================================================

print("GrabIt ishga tushdi!")

bot.infinity_polling(
    skip_pending=True,
    timeout=30,
    long_polling_timeout=30
)
