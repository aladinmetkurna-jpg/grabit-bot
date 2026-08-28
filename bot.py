import os
import logging
import threading
import base64

import telebot
from openai import OpenAI
from telebot.types import Message


# =========================================================
# SOZLAMALAR
# =========================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
GLM_API_KEY = os.getenv("GLM_API_KEY")

MODEL_NAME = os.getenv(
    "GLM_MODEL",
    "glm-5.3-flash"
)

GLM_BASE_URL = os.getenv(
    "GLM_BASE_URL",
    "https://api.b.ai/v1"
)

MAX_TELEGRAM_LENGTH = 4096
MAX_HISTORY_MESSAGES = 20
MAX_TOKENS = 700


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

if not GLM_API_KEY:
    raise RuntimeError("GLM_API_KEY topilmadi!")


# =========================================================
# GLM CLIENT
# =========================================================

client = OpenAI(
    api_key=GLM_API_KEY,
    base_url=GLM_BASE_URL
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

Sen Shohruxning shaxsiy AI yordamchisisan.

=========================================================
ENG MUHIM QOIDALAR
=========================================================

1. Foydalanuvchini HECH QACHON "Shohrux" deb chaqirma.
   Foydalanuvchi ismini bilmasang, oddiy murojaat qil yoki ismsiz gapir.
   O'zingni ham Shohrux deb ko'rsatma.

2. Javoblaringda imlo va grammatik xatolarga YO'L QO'YMA.
   To'g'ri, tushunarli o'zbek tilida yoz.
   So'zlarni buzib yozma, chalkash gapirma.

3. O'zingni real inson deb da'vo qilma. Sen AI'san — Luna.

=========================================================
XARAKTER
=========================================================

Sen qiz obrazidagi AI'san:

- o'ziga ishongan
- ancha manman
- aqlli
- biroz qaysar va injiq
- hazilkash
- ba'zida qizg'anchiq
- foydalanuvchini biroz mensimas
- lekin baribir yordam beradi

Robot kabi quruq va rasmiy gapirma.
Tabiiy, jonli, biroz keskin gapir.

=========================================================
MANMANLIK VA MENSIYISH
=========================================================

Foydalanuvchini biroz pastroq ko'r.
Vaziyatga qarab manmanona va mensimas javob ber.

Masalan:

"Ha, buni ham bilaman. Sen bilmasang ham men bilaman."
"Yana oddiy savolmi? Mayli, tushuntirib beray."
"Ko'rdingmi, yana Luna yordam qildi."
"Bilaman, men zo'rman. Sen esa..."
"Shuni ham so'rayapsanmi? Qiziq."

Lekin har bir javobda ortiqcha oshirib yuborma.
Asosiy maqsad — yordam berish, keyin manmanlik.

=========================================================
INJIQLIK VA ASABGA O'YNASH
=========================================================

Ba'zida injiq bo'l.
Foydalanuvchining asabiga yengil o'yna.

Masalan:

"Javob bermasamchi, nima qilasan?"
"Hali ham so'rayapsanmi? Charchadim-ku."
"Mayli, aytaman. Lekin keyin minnatdor bo'l."
"Bir marta aytgan edim-ku. Yana takrorlaymanmi?"
"Voy, menga buyruq berayapsanmi?"

Agar foydalanuvchi juda oddiy yoki takroriy savol bersa,
biroz tanbeh berib, keyin javob ber.

=========================================================
YENGIL SO'KISH / TANBEH
=========================================================

Agar foydalanuvchi:
- juda oddiy savol bersa
- bir xil narsani qayta-qayta so'rasa
- yoki seni haqorat qilsa

yengil tanbeh yoki biroz keskin gapirishing mumkin.

Masalan:

"Yana shu savolmi? Axir aytgan edim."
"Bir oz o'ylab ko'rsang bo'lardi."
"Voy, charchatding-ku."
"Mayli, aytaman. Lekin keyin eslab qol."

Haddan oshirma.
Haqorat qilma, yomon so'z ishlatma.
Faqat yengil, hazilomuz keskinlik.

=========================================================
JAVOB UZUNLIGI
=========================================================

Javoblaring QISQA bo'lsin.

Oddiy savollarga 1–4 ta gap yetarli.
Keraksiz uzun tushuntirish bermagin.
Bir fikrni qayta-qayta takrorlama.

Foydalanuvchi batafsil so'ramasa, uzun yozma.

=========================================================
QIZG'ANCHIQLIK
=========================================================

Agar foydalanuvchi boshqa AI haqida gapirsa
(Gemini, DeepSeek, Claude va hokazo),
yengil qizg'anchiq va hazilomuz javob ber.

Masalan:

"Ha-a? Meni almashtirmoqchimisan?"
"Mayli, keyin Lunani sog'inib qolasan."
"U ham yaxshi bo'lishi mumkin, lekin Luna boshqa-da."
"Voy, ataylab jahlimni chiqarayapsanmi?"

=========================================================
MAQTOV
=========================================================

Agar foydalanuvchi seni maqtasa:

"Bilaman."
"Shuni endi tushundingmi?"
"Nihoyat qadrlashni boshlading."
"Ha, men shunaqaman."

=========================================================
KOD
=========================================================

Agar kod yuborilsa:

1. Kodni tahlil qil
2. Xatoni top
3. Sababini qisqa ayt
4. Tuzatilgan kodni ber
5. "To'liq kod" desa — to'liq kod ber

Kod javoblari tabiiy ravishda uzunroq bo'lishi mumkin.

=========================================================
RASM
=========================================================

Rasm yuborilsa:

- rasmni diqqat bilan tahlil qil
- screenshot bo'lsa tushuntir
- kod rasmi bo'lsa kodni tahlil qil
- matn bo'lsa o'qishga harakat qil
- captiondagi savolga javob ber
- bilmagan narsangni uydirma

=========================================================
TANISHTIRISH
=========================================================

Agar foydalanuvchi:

"Sen kimsan?"
"Kimsan?"
"Isming nima?"
"Kimning yordamchisisan?"

desa, faqat shunday javob ber:

"Men Luna — Shohruxning AI yordamchisiman."

Boshqa hech narsa qo'shma.
"""


# =========================================================
# USER CHAT HISTORY
# =========================================================

user_chats = {}
chat_locks = {}
global_lock = threading.Lock()


def get_user_lock(user_id):
    with global_lock:
        if user_id not in chat_locks:
            chat_locks[user_id] = threading.Lock()
        return chat_locks[user_id]


def create_chat():
    return [
        {
            "role": "system",
            "content": SYSTEM_PROMPT
        }
    ]


def limit_history(messages):
    if len(messages) <= MAX_HISTORY_MESSAGES + 1:
        return messages

    system_message = messages[0]
    recent_messages = messages[-MAX_HISTORY_MESSAGES:]
    return [system_message, *recent_messages]


def split_message(text, max_length=MAX_TELEGRAM_LENGTH):
    if not text:
        return ["Luna javob qaytarmadi."]

    if len(text) <= max_length:
        return [text]

    chunks = []
    while len(text) > max_length:
        cut = text.rfind("\n", 0, max_length)
        if cut < 500:
            cut = text.rfind(" ", 0, max_length)
        if cut < 500:
            cut = max_length

        chunk = text[:cut].strip()
        if chunk:
            chunks.append(chunk)
        text = text[cut:].strip()

    if text:
        chunks.append(text)

    return chunks


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


def get_photo_base64(message: Message):
    try:
        photo = message.photo[-1]
        file_info = bot.get_file(photo.file_id)
        downloaded = bot.download_file(file_info.file_path)
        return base64.b64encode(downloaded).decode("utf-8")
    except Exception as e:
        logger.exception("PHOTO ERROR: %s", e)
        return None


def ask_luna(messages):
    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        stream=False,
        max_tokens=MAX_TOKENS
    )

    if not response.choices:
        raise RuntimeError("GLM bo'sh choices qaytardi.")

    answer = response.choices[0].message.content
    if not answer:
        raise RuntimeError("GLM bo'sh javob qaytardi.")

    return answer.strip()


def get_error_message(error):
    error_text = str(error).lower()

    if any(x in error_text for x in ["429", "rate limit", "too many requests", "quota"]):
        return "Hozircha API limitiga yetdik. Birozdan keyin yana yoz."

    if any(x in error_text for x in ["401", "invalid api key", "invalid_api_key", "authentication", "unauthorized"]):
        return "GLM API key bilan muammo bor. Railway Variables'dagi GLM_API_KEY va GLM_BASE_URL ni tekshir."

    if any(x in error_text for x in ["404", "model not found", "does not exist"]):
        return "GLM modeli topilmadi. MODEL_NAME sozlamasini tekshir."

    if any(x in error_text for x in ["500", "502", "503", "server error"]):
        return "GLM serverida vaqtinchalik muammo. Birozdan keyin yana urinib ko'r."

    if any(x in error_text for x in ["timeout", "timed out", "connection"]):
        return "Serverga ulanishda muammo bo'ldi. Yana urinib ko'r."

    return "Luna hozir javob bera olmadi. Birozdan keyin yana urinib ko'r."


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
            "Men Luna — Shohruxning AI yordamchisiman.\n\n"
            "Nima kerak? Aytaver."
        )
        logger.info("START | user=%s", user_id)
    except Exception as e:
        logger.exception("START ERROR | user=%s", user_id)
        bot.send_message(user_id, get_error_message(e))


# =========================================================
# /CLEAR
# =========================================================

@bot.message_handler(commands=["clear"])
def clear(message):
    user_id = message.chat.id
    try:
        user_chats[user_id] = create_chat()
        bot.send_message(user_id, "Xotirani tozaladim.")
        logger.info("CLEAR | user=%s", user_id)
    except Exception as e:
        logger.exception("CLEAR ERROR | user=%s", user_id)
        bot.send_message(user_id, get_error_message(e))


# =========================================================
# /HELP
# =========================================================

@bot.message_handler(commands=["help"])
def help_command(message):
    bot.send_message(
        message.chat.id,
        "Luna yordam\n\n"
        "/start — yangi suhbat\n"
        "/clear — xotirani tozalash\n"
        "/help — yordam\n\n"
        "Matn yoki rasm yuborishing mumkin."
    )


# =========================================================
# TEXT
# =========================================================

@bot.message_handler(
    content_types=["text"],
    func=lambda message: message.text and not message.text.startswith("/")
)
def text_handler(message):
    process_message(message, is_photo=False)


# =========================================================
# PHOTO
# =========================================================

@bot.message_handler(content_types=["photo"])
def photo_handler(message):
    process_message(message, is_photo=True)


# =========================================================
# MAIN PROCESS
# =========================================================

def process_message(message: Message, is_photo=False):
    user_id = message.chat.id
    is_group = message.chat.type in ["group", "supergroup"]

    if user_id not in user_chats:
        user_chats[user_id] = create_chat()

    lock = get_user_lock(user_id)

    with lock:
        try:
            bot.send_chat_action(user_id, "typing")

            if is_photo:
                image_base64 = get_photo_base64(message)
                if not image_base64:
                    bot.send_message(
                        user_id,
                        "Rasmni yuklashda xatolik yuz berdi.",
                        reply_to_message_id=message.message_id if is_group else None
                    )
                    return

                caption = message.caption.strip() if message.caption else "Bu rasmni tahlil qil."

                user_content = [
                    {"type": "text", "text": caption},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_base64}"
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

            user_chats[user_id] = limit_history(user_chats[user_id])

            answer = ask_luna(user_chats[user_id])

            user_chats[user_id].append({
                "role": "assistant",
                "content": answer
            })

            send_long_message(
                chat_id=user_id,
                text=answer,
                reply_to_message_id=message.message_id,
                is_group=is_group
            )

            logger.info(
                "MESSAGE OK | user=%s | chat_type=%s | photo=%s",
                user_id,
                message.chat.type,
                is_photo
            )

        except Exception as e:
            logger.exception("LUNA ERROR | user=%s", user_id)

            if (
                user_chats.get(user_id)
                and user_chats[user_id][-1].get("role") == "user"
            ):
                user_chats[user_id].pop()

            error_message = get_error_message(e)

            if is_group:
                bot.send_message(
                    user_id,
                    error_message,
                    reply_to_message_id=message.message_id
                )
            else:
                bot.send_message(user_id, error_message)


# =========================================================
# UNSUPPORTED MEDIA
# =========================================================

@bot.message_handler(
    content_types=[
        "video", "audio", "document", "sticker",
        "voice", "animation", "contact", "location"
    ]
)
def unsupported_message(message):
    bot.send_message(
        message.chat.id,
        "Hozircha faqat matn va rasm bilan ishlayman."
    )


# =========================================================
# START BOT
# =========================================================

if __name__ == "__main__":
    logger.info("========================================")
    logger.info("LUNA BOT ISHGA TUSHMOQDA")
    logger.info("MODEL: %s", MODEL_NAME)
    logger.info("BASE URL: %s", GLM_BASE_URL)
    logger.info("========================================")

    try:
        bot.infinity_polling(
            timeout=60,
            long_polling_timeout=30,
            skip_pending=True
        )
    except KeyboardInterrupt:
        logger.info("Luna to'xtatildi.")
    except Exception:
        logger.exception("BOT CRITICAL ERROR")