import os
import tempfile
import shutil
import threading
import urllib.request

import telebot
import yt_dlp


# =========================================================
# SOZLAMALAR
# =========================================================

TELEGRAM_TOKEN = os.environ.get("TELEGRAM_TOKEN", "")
ADMIN_USERNAME = os.environ.get(
    "ADMIN_USERNAME",
    "Meyaxad"
).replace("@", "").lower()

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN topilmadi!")

bot = telebot.TeleBot(TELEGRAM_TOKEN)

users = {}
channels = []
LIMIT = 20

# Rasm kengaytmalari (video bo'lmasa shular tekshiriladi)
IMAGE_EXTENSIONS = (
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
    ".gif"
)

# Faqat videolar ostiga qo'yiladigan yozuv (kursiv)
VIDEO_CAPTION = "<i>Creator: @Meyaxad</i>"

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
            "Botni guruhga qo'shish ⤴",
            url="https://t.me/GrabIt_downloader_bot?startgroup=true"
        )
    )

    bot.send_message(
        user_id,
        "👋 Assalomu aleykum. Men sizga Instagram, Tiktok, "
        "Youtube va Pinterestdan video va rasimlani yuklashda "
        "yordam beraman.\n\n"
        "• Videoni yuklashim uchun video yoki photoni "
        "havolasini menga jo'nating\n\n"
        "<i>Bot guruhlarda ham ishlaydi, guruhda ham "
        "ishlatmoqchi bo'lsangiz tugmani bosing👇</i>",
        parse_mode="HTML",
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
# RASM / VIDEO ANIQLASH
# =========================================================

def is_image_item(item):
    """
    Berilgan post (yoki carousel elementi) faqat rasmmi
    yoki videomi ekanini aniqlaydi.
    """

    formats = item.get("formats")

    if formats:

        # Agar formatlar orasida hech bo'lmasa bittasida
        # video kodek bo'lsa — bu video.
        for f in formats:

            vcodec = f.get("vcodec")

            if vcodec and vcodec != "none":
                return False

        return True

    vcodec = item.get("vcodec")
    ext = (item.get("ext") or "").lower()

    if vcodec in (None, "none") and ("." + ext) in IMAGE_EXTENSIONS:
        return True

    return False


def best_image_url(item):
    """
    Post ichidan eng sifatli (eng katta o'lchamli) rasm
    URL manzilini va uning kengaytmasini qaytaradi.
    """

    formats = item.get("formats")

    if formats:

        candidates = [
            f for f in formats
            if f.get("url") and f.get("vcodec") in (None, "none")
        ]

        if candidates:

            candidates.sort(
                key=lambda f: (f.get("width") or 0) * (f.get("height") or 0),
                reverse=True
            )

            best = candidates[0]

            return best["url"], (best.get("ext") or "jpg")

    if item.get("url"):
        return item["url"], (item.get("ext") or "jpg")

    return None, None


def download_direct(url, dest_path):
    """
    Rasmni ffmpeg/yt-dlp orqali emas, to'g'ridan-to'g'ri
    URL'dan yuklaydi (rasmlar ko'pincha alohida video
    formatga ega bo'lmagani uchun bu ancha ishonchli).
    """

    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
            )
        }
    )

    with urllib.request.urlopen(req, timeout=60) as response:

        with open(dest_path, "wb") as out_file:
            shutil.copyfileobj(response, out_file)


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
        # 1-BOSQICH: LINKNI TEKSHIRISH
        # (yuklab olmasdan turib, video yoki
        # rasm ekanini aniqlaymiz)
        # ---------------------------------

        probe_opts = {
            "quiet": True,
            "no_warnings": True,
            "noplaylist": True,
            "socket_timeout": 60,
            "retries": 5,
        }

        with yt_dlp.YoutubeDL(probe_opts) as ydl:
            info = ydl.extract_info(url, download=False)

        if isinstance(info, dict) and info.get("entries"):
            items = [e for e in info["entries"] if e]
        elif isinstance(info, dict):
            items = [info]
        else:
            items = []

        if not items:
            raise Exception("Hech narsa topilmadi.")

        is_album = len(items) > 1

        media_group = []
        single_path = None
        single_is_image = False

        # ---------------------------------
        # 2-BOSQICH: HAR BIR ELEMENTNI YUKLASH
        # ---------------------------------

        for idx, item in enumerate(items[:10]):

            if is_image_item(item):

                # ----- RASM: to'g'ridan-to'g'ri yuklaymiz -----

                img_url, ext = best_image_url(item)

                if not img_url:
                    continue

                if ("." + ext.lower()) not in IMAGE_EXTENSIONS:
                    ext = "jpg"

                dest = os.path.join(
                    temp_dir,
                    "img_" + str(idx) + "." + ext
                )

                try:
                    download_direct(img_url, dest)
                except Exception:
                    continue

                if not os.path.exists(dest):
                    continue

                if os.path.getsize(dest) > 49 * 1024 * 1024:
                    continue

                if is_album:

                    with open(dest, "rb") as f:
                        media_group.append(
                            telebot.types.InputMediaPhoto(f.read())
                        )

                else:

                    single_path = dest
                    single_is_image = True

            else:

                # ----- VIDEO: yt-dlp orqali yuklaymiz -----

                entry_url = (
                    item.get("webpage_url")
                    or item.get("url")
                    or url
                )

                video_opts = {
                    "format": "bestvideo*+bestaudio/best",
                    "merge_output_format": "mp4",
                    "outtmpl": os.path.join(
                        temp_dir,
                        "vid_" + str(idx) + ".%(ext)s"
                    ),
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
                    "postprocessors": [
                        {
                            "key": "FFmpegVideoConvertor",
                            "preferedformat": "mp4"
                        }
                    ]
                }

                try:

                    with yt_dlp.YoutubeDL(video_opts) as ydl2:
                        ydl2.download([entry_url])

                except Exception:
                    continue

                vid_path = None

                for name in os.listdir(temp_dir):

                    if not name.startswith("vid_" + str(idx) + "."):
                        continue

                    if name.endswith((".part", ".ytdl")):
                        continue

                    vid_path = os.path.join(temp_dir, name)
                    break

                if not vid_path:
                    continue

                if os.path.getsize(vid_path) > 49 * 1024 * 1024:
                    continue

                if is_album:

                    with open(vid_path, "rb") as f:
                        media_group.append(
                            telebot.types.InputMediaVideo(
                                f.read(),
                                caption=VIDEO_CAPTION,
                                parse_mode="HTML"
                            )
                        )

                else:

                    single_path = vid_path
                    single_is_image = False

        # ---------------------------------
        # 3-BOSQICH: YUBORISH
        # ---------------------------------

        if media_group:

            bot.send_media_group(
                user_id,
                media_group
            )

            users[user_id]["count"] += 1

        elif single_path:

            with open(single_path, "rb") as f:

                if single_is_image:

                    bot.send_photo(
                        user_id,
                        f
                    )

                else:

                    bot.send_video(
                        user_id,
                        f,
                        supports_streaming=True,
                        caption=VIDEO_CAPTION,
                        parse_mode="HTML"
                    )

            users[user_id]["count"] += 1

        else:

            raise Exception("Yuklab bo'lmadi.")

        # Statusni o'chirish
        try:

            bot.delete_message(
                user_id,
                status_message.message_id
            )

        except Exception:
            pass

    except Exception:

        # Xato bo'lsa, foydalanuvchiga hech narsa
        # ko'rsatilmaydi — status xabar shunchaki o'chiriladi.

        try:

 
