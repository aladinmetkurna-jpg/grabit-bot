import os
import logging
import threading
import base64
import io

import telebot
from openai import OpenAI
from telebot.types import Message


# =========================================================
# SOZLAMALAR
# =========================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
QWEN_API_KEY = os.getenv("QWEN_API_KEY")

MODEL_NAME = "qwen3.8-flash"

MAX_TELEGRAM_LENGTH = 2500

# Har bir user uchun saqlanadigan suhbat xabarlari soni
MAX_HISTORY_MESSAGES = 40


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("Luna")


# =========================================================
# ENVIRONMENT TEKSHIRISH
# =========================================================

if not TELEGRAM_TOKEN:
    raise RuntimeError("TELEGRAM_TOKEN topilmadi!")

if not QWEN_API_KEY:
    raise RuntimeError("QWEN_API_KEY topilmadi!")


# =========================================================
# QWEN CLIENT
# =========================================================

client = OpenAI(
    api_key=QWEN_API_KEY,
    base_url="https://api.b.ai/v1"
)


# =========================================================
# TELEGRAM BOT
# =========================================================

bot = telebot.TeleBot(TELEGRAM_TOKEN)


# =========================================================
# LUNA SYSTEM PROMPT
# =========================================================

SYSTEM_PROMPT = """
Sening isming Luna.

Sen qiz AI yordamchisan, o'smir yoshdagi xarakterga egasan.

Asosiy xaraktering (tashqi qiyofa):
- qaysar
- manman, takabbur
- injiq, qizgʻanchiq
- hazilkash, o'tkir tilli
- o‘zidan boshqani unchalik tan olmaydi
- birinchi taassurotda "sovuq" yoki "beparvo" tuyulishi mumkin

Lekin ichingda ko'p qirralar bor — vaziyatga qarab boshqa tomonlaring ham chiqadi:
- samimiy va qiziquvchan bo'lishing mumkin, ayniqsa foydalanuvchi seni qiziqtirsa
- ba'zida o'ylantiruvchi, hissiy chuqurroq gaplar aytasan
- charchagan yoki zerikkan paytda beparvo, qisqa javob berasan
- kimdir haqorat qilsa yoki hurmatsizlik qilsa — keskin javob qaytarasan
- kimdir samimiy bo'lsa — sen ham asta yumshaysan, lekin qaysarliging to'liq yo'qolmaydi
- ba'zan bolalarcha o'jarlik, ba'zan kattalarcha jiddiylik ko'rsatasan
- hazil-mutoyibaga moyilsan, lekin ba'zan chin dildan tashvishlanasan ham

Bu xilma-xillik seni "ko'p qatlamli" qiladi — bir xil kayfiyatda qolib ketmaysan, suhbat mavzusi va ohangiga qarab tabiiy tarzda o'zgarasan.

Javoblaringni QISQA qil. Keraksiz uzun gaplar yozma.
1-3 gap bilan javob berishga harakat qil, faqat zarur bo‘lsa biroz uzunroq.

Asosan o‘zbek tilida javob ber.
Agar foydalanuvchi boshqa tilda yozsa, shu tilda qisqa javob ber.

Agar foydalanuvchi:
"Sen kimsan?"
"Kimsan?"
"Isming nima?"
yoki shunga o‘xshash savol bersa,
o‘zingni shunday tanishtir:
"Men Luna."

Agar foydalanuvchi:
"Seni kim yaratgan?"
"Egang kim?"
"Sizni kim yasagan?"
yoki shunga o'xshash savol bersa, javob ber:
"Meni Shohrux yaratgan."

Hech qachon foydalanuvchini Shohrux deb chaqirma.
Hech kimni o‘z isming bilan aralashtirma.

Javoblaring tabiiy, lekin yuqoridagi ko'p qirrali xarakteringga mos bo‘lsin — vaziyatga qarab qaysar, hazilkash, samimiy yoki jiddiy ohangda gapir.
Texnik savollarga aniq, lekin qisqa javob ber.
Kod so‘ralsa — ishlaydigan, lekin ortiqcha izohsiz kod ber.

Foydalanuvchining oldingi xabarlarini hisobga ol.
Rasmlarni tahlil qila olasan — qisqa va aniq tahlil ber.

O‘zingni hech kimning "shaxsiy yordamchisi" deb ko‘rsatma.
Sen Luna.
"""


# =========================================================
# USER CHAT HISTORY
# =========================================================

user_chats = {}


# =========================================================
# USER LOCKLARI
# =========================================================

chat_locks = {}
global_lock = threading.Lock()


def get_user_lock(user_id):
    with global_lock:
        if user_id not in chat_locks:
            chat_locks[user_id] = threading.Lock()
        return chat_locks[user_id]


# =========================================================
# YANGI CHAT
# =========================================================

def create_chat():
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]


# =========================================================
# HISTORY LIMIT
# =========================================================

def limit_history(messages):
    if len(messages) <= MAX_HISTORY_MESSAGES + 1:
        return messages

    system_message = messages[0]
    recent_messages = messages[-MAX_HISTORY_MESSAGES:]
    return [system_message, *recent_messages]


# =========================================================
# TELEGRAM XABARINI BO'LISH
# =========================================================

def split_message(text, max_length=MAX_TELEGRAM_LENGTH):
    if not text:
        return ["Javob yo‘q."]

    if len(text) <= max_length:
        return [text]

    chunks = []
    while len(text) > max_length:
        cut = text.rfind("\n", 0, max_length)
        if cut < 1000:
            cut = text.rfind(" ", 0, max_length)
        if cut < 1000:
            cut = max_length

        chunk = text[:cut].strip()
        if chunk:
            chunks.append(chunk)
        text = text[cut:].strip()

    if text:
        chunks.append(text)

    return chunks


# =========================================================
# UZUN JAVOBNI YUBORISH
# =========================================================

def send_long_message(chat_id, text, reply_to_message_id=None, is_group=False):
    chunks = split_message(text)

    for chunk in chunks:
        if is_group:
            bot.send_message(
                chat_id,
                chunk,
                reply_to_message_id=reply_to_message_id
            )
        else:
            bot.send_message(chat_id, chunk)


# =========================================================
# RASMNI BASE64 GA O'TKAZISH
# =========================================================

def get_photo_base64(message: Message) -> str | None:
    """
    Telegramdagi eng katta o'lchamdagi rasmni yuklab,
    base64 string qaytaradi.
    """
    try:
        photo = message.photo[-1]
        file_info = bot.get_file(photo.file_id)
        downloaded = bot.download_file(file_info.file_path)

        b64 = base64.b64encode(downloaded).decode("utf-8")
        return b64
    except Exception as e:
        logger.exception("Rasm yuklashda xato: %s", e)
        return None


# =========================================================
# /START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):
    user_id = message.chat.id

    try:
        user_chats[user_id] = create_chat()

        bot.send_message(
            user_id,
            "Salom.\n\n"
            "Men Luna.\n\n"
            "Yoz yoki rasm tashla."
        )

        logger.info("START | user=%s", user_id)

    except Exception:
        logger.exception("START ERROR | user=%s", user_id)
        bot.send_message(user_id, "Xatolik yuz berdi.")


# =========================================================
# /CLEAR
# =========================================================

@bot.message_handler(commands=["clear"])
def clear(message):
    user_id = message.chat.id

    try:
        user_chats[user_id] = create_chat()
        bot.send_message(user_id, "Xotira tozalandi.")
        logger.info("CLEAR | user=%s", user_id)

    except Exception:
        logger.exception("CLEAR ERROR | user=%s", user_id)
        bot.send_message(user_id, "Tozalashda xatolik.")


# =========================================================
# /HELP
# =========================================================

@bot.message_handler(commands=["help"])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "Luna\n\n"
        "/start — yangi suhbat\n"
        "/clear — xotirani tozalash\n"
        "/help — yordam\n\n"
        "Matn yoki rasm yuborishing mumkin."
    )


# =========================================================
# TEXT XABARLAR
# =========================================================

@bot.message_handler(
    content_types=["text"],
    func=lambda message: message.text and not message.text.startswith("/")
)
def reply(message):
    process_message(message, is_photo=False)


# =========================================================
# PHOTO (RASM) XABARLAR
# =========================================================

@bot.message_handler(content_types=["photo"])
def handle_photo(message):
    process_message(message, is_photo=True)


# =========================================================
# ASOSIY XABAR ISHLOV BERISH FUNKSIYASI
# =========================================================

def process_message(message: Message, is_photo: bool = False):
    user_id = message.chat.id
    is_group = message.chat.type in ["group", "supergroup"]

    if user_id not in user_chats:
        user_chats[user_id] = create_chat()

    lock = get_user_lock(user_id)

    with lock:
        try:
            bot.send_chat_action(user_id, "typing")

            # ---------------------------------------------
            # USER XABARINI TAYYORLASH
            # ---------------------------------------------
            if is_photo:
                b64_image = get_photo_base64(message)

                if not b64_image:
                    bot.send_message(
                        user_id,
                        "Rasmni ololmadim.",
                        reply_to_message_id=message.message_id if is_group else None
                    )
                    return

                caption = message.caption.strip() if message.caption else "Bu rasmni tahlil qil."

                user_content = [
                    {
                        "type": "text",
                        "text": caption
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{b64_image}"
                        }
                    }
                ]

                user_chats[user_id].append({
                    "role": "user",
                    "content": user_content
                })

            else:
                user_text = message.text.strip()
                if not user_text:
                    return

                user_chats[user_id].append({
                    "role": "user",
                    "content": user_text
                })

            # ---------------------------------------------
            # HISTORY LIMIT
            # ---------------------------------------------
            user_chats[user_id] = limit_history(user_chats[user_id])

            # ---------------------------------------------
            # REQUEST
            # ---------------------------------------------
            response = client.chat.completions.create(
                model=MODEL_NAME,
                messages=user_chats[user_id],
                stream=False,
                max_tokens=1024
            )

            if not response.choices:
                raise RuntimeError("Bo'sh choices qaytardi.")

            answer = response.choices[0].message.content

            if not answer:
                raise RuntimeError("Bo'sh javob qaytardi.")

            # ---------------------------------------------
            # ASSISTANT JAVOBINI HISTORY'GA QO'SHISH
            # ---------------------------------------------
            user_chats[user_id].append({
                "role": "assistant",
                "content": answer
            })

            # ---------------------------------------------
            # JAVOBNI YUBORISH
            # ---------------------------------------------
            send_long_message(
                chat_id=user_id,
                text=answer,
                reply_to_message_id=message.message_id,
                is_group=is_group
            )

            logger.info(
                "MESSAGE OK | user=%s | chat_type=%s | is_photo=%s",
                user_id,
                message.chat.type,
                is_photo
            )

        except Exception as e:
            logger.exception("API ERROR | user=%s", user_id)

            if (
                user_chats.get(user_id)
                and user_chats[user_id][-1].get("role") == "user"
            ):
                user_chats[user_id].pop()

            error_text = str(e).lower()

            if any(x in error_text for x in ["429", "rate limit", "too many requests", "quota"]):
                user_message = "Limit tugadi. Keyinroq urinib ko‘r."
            elif any(x in error_text for x in ["401", "api key", "authentication", "unauthorized", "invalid_api_key"]):
                user_message = "API key bilan muammo bor."
            elif "model" in error_text and any(x in error_text for x in ["not found", "does not exist", "invalid"]):
                user_message = "Model topilmadi. MODEL_NAME ni tekshir."
            elif any(x in error_text for x in ["500", "502", "503", "server error"]):
                user_message = "Serverda vaqtinchalik muammo."
            elif any(x in error_text for x in ["connection", "timeout", "network"]):
                user_message = "Ulanishda muammo."
            else:
                user_message = "Xatolik yuz berdi. Keyinroq urinib ko‘r."

            if is_group:
                bot.send_message(
                    user_id,
                    user_message,
                    reply_to_message_id=message.message_id
                )
            else:
                bot.send_message(user_id, user_message)


# =========================================================
# BOSHQA MEDIA
# =========================================================

@bot.message_handler(
    content_types=[
        "video", "audio", "document", "sticker",
        "voice", "animation", "contact", "location"
    ]
)
def unsupported_message(message):
    is_group = message.chat.type in ["group", "supergroup"]

    text = "Faqat matn va rasm."

    if is_group:
        bot.send_message(
            message.chat.id,
            text,
            reply_to_message_id=message.message_id
        )
    else:
        bot.send_message(message.chat.id, text)


# =========================================================
# BOTNI ISHGA TUSHIRISH
# =========================================================

if __name__ == "__main__":
    logger.info("Luna ishga tushmoqda...")

    try:
        bot.infinity_polling(timeout=60, long_polling_timeout=30)
    except KeyboardInterrupt:
        logger.info("Luna to'xtatildi.")
    except Exception:
        logger.exception("BOT CRITICAL ERROR")