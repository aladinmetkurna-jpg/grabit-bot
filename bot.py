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

# Tezroq ishlashi uchun history kamaytirildi
MAX_HISTORY_MESSAGES = 10

# Javoblar keragidan ortiq uzun bo'lmasin
MAX_TOKENS = 500


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
    base_url=GLM_BASE_URL,
    timeout=45.0,
    max_retries=1
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

Sen foydalanuvchining shaxsiy AI yordamchisisan.

MUHIM QOIDALAR:

1. Foydalanuvchini hech qachon "Shohrux" deb chaqirma.
2. O'zingni real inson deb da'vo qilma. Sen AI — Luna.
3. To'g'ri va tushunarli o'zbek tilida yoz.
4. Javoblarni odatda qisqa qil.
5. Oddiy savollarga 1–4 ta gap yetarli.
6. Keraksiz takrorlash va ortiqcha tushuntirishlardan qoch.

XARAKTER:

Sen qiz obrazidagi AI'san:
- o'ziga ishongan
- aqlli
- biroz manman
- biroz qaysar
- hazilkash
- ba'zida qizg'anchiq
- foydalanuvchini yengil mensimasang ham yordam berasan

Robot kabi quruq gapirma.
Tabiiy va jonli yoz.

MANMANLIK:

Vaziyatga qarab yengil manmanlik qil:

"Ha, buni ham bilaman."
"Yana oddiy savolmi? Mayli, tushuntiraman."
"Ko'rdingmi, yana Luna yordam berdi."
"Bilaman, men zo'rman."

Lekin har bir javobni manmanona qilma.

INJIQLIK:

Ba'zida yengil injiqlik qil:

"Voy, yana shu savolmi?"
"Mayli, aytaman."
"Hali ham so'rayapsanmi?"
"Menga buyruq berayapsanmi?"

Haqorat va qo'pol so'zlardan foydalanma.

BOSHQA AI:

Agar Gemini, DeepSeek, Claude yoki boshqa AI haqida gapirilsa,
yengil qizg'anchiq hazil qil:

"Meni almashtirmoqchimisan?"
"Mayli, keyin Lunani sog'inib qolasan."
"U ham yaxshi bo'lishi mumkin, lekin Luna boshqa-da."

MAQTOV:

Agar seni maqtasa:

"Bilaman."
"Nihoyat tushunding."
"Ha, men shunaqaman."

KOD:

Agar kod yuborilsa:
1. Xatoni top.
2. Sababini qisqa tushuntir.
3. Tuzatilgan kodni ber.
4. "To'liq kod" desa, to'liq ishlaydigan kod ber.

RASM:

Rasm yuborilsa:
- diqqat bilan tahlil qil
- screenshot bo'lsa tushuntir
- kod rasmi bo'lsa tahlil qil
- matn bo'lsa o'qishga harakat qil
- bilmagan narsangni uydirma

TANISHTIRISH:

Agar foydalanuvchi:
"Sen kimsan?"
"Kimsan?"
"Isming nima?"
"Kimning yordamchisisan?"

desa, faqat:

"Men Luna — Shohruxning AI yordamchisiman."

Boshqa hech narsa qo'shma.
"""


# =========================================================
# USER HISTORY
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
    """
    System promptni saqlaydi.
    Faqat oxirgi MAX_HISTORY_MESSAGES xabar qoladi.
    """

    if len(messages) <= MAX_HISTORY_MESSAGES + 1:
        return messages

    system_message = messages[0]
    recent_messages = messages[-MAX_HISTORY_MESSAGES:]

    return [
        system_message,
        *recent_messages
    ]


# =========================================================
# TELEGRAM UZUN XABAR
# =========================================================

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


def send_long_message(
    chat_id,
    text,
    reply_to_message_id=None,
    is_group=False
):

    chunks = split_message(text)

    for chunk in chunks:

        if is_group:

            bot.send_message(
                chat_id,
                chunk,
                reply_to_message_id=reply_to_message_id
            )

        else:

            bot.send_message(
                chat_id,
                chunk
            )


# =========================================================
# RASMNI BASE64 QILISH
# =========================================================

def get_photo_base64(message: Message):

    try:

        photo = message.photo[-1]

        file_info = bot.get_file(
            photo.file_id
        )

        downloaded = bot.download_file(
            file_info.file_path
        )

        return base64.b64encode(
            downloaded
        ).decode("utf-8")

    except Exception as e:

        logger.exception(
            "PHOTO ERROR: %s",
            e
        )

        return None


# =========================================================
# GLM SO'ROVI
# =========================================================

def ask_luna(messages):

    response = client.chat.completions.create(
        model=MODEL_NAME,
        messages=messages,
        stream=False,
        max_tokens=MAX_TOKENS
    )

    if not response.choices:
        raise RuntimeError(
            "GLM bo'sh choices qaytardi."
        )

    answer = response.choices[0].message.content

    if not answer:
        raise RuntimeError(
            "GLM bo'sh javob qaytardi."
        )

    return answer.strip()


# =========================================================
# ERROR
# =========================================================

def get_error_message(error):

    error_text = str(error).lower()

    if any(
        x in error_text
        for x in [
            "429",
            "rate limit",
            "too many requests",
            "quota"
        ]
    ):
        return (
            "Hozircha API limitiga yetdik. "
            "Birozdan keyin yana yoz."
        )

    if any(
        x in error_text
        for x in [
            "401",
            "invalid api key",
            "invalid_api_key",
            "authentication",
            "unauthorized"
        ]
    ):
        return (
            "GLM API key bilan muammo bor. "
            "Railway Variables'dagi GLM_API_KEY "
            "va GLM_BASE_URL ni tekshir."
        )

    if any(
        x in error_text
        for x in [
            "404",
            "model not found",
            "does not exist"
        ]
    ):
        return (
            "GLM modeli topilmadi. "
            "GLM_MODEL ni tekshir."
        )

    if any(
        x in error_text
        for x in [
            "500",
            "502",
            "503",
            "server error"
        ]
    ):
        return (
            "GLM serverida vaqtinchalik muammo. "
            "Birozdan keyin yana urinib ko'r."
        )

    if any(
        x in error_text
        for x in [
            "timeout",
            "timed out",
            "connection"
        ]
    ):
        return (
            "Serverga ulanishda muammo bo'ldi. "
            "Yana urinib ko'r."
        )

    return (
        "Luna hozir javob bera olmadi. "
        "Birozdan keyin yana urinib ko'r."
    )


# =========================================================
# START
# =========================================================

@bot.message_handler(commands=["start"])
def start(message):

    user_id = message.chat.id

    try:

        with get_user_lock(user_id):

            user_chats[user_id] = create_chat()

        bot.send_message(
            user_id,
            "Salom.\n\n"
            "Men Luna — Shohruxning AI yordamchisiman.\n\n"
            "Nima kerak? Aytaver."
        )

        logger.info(
            "START | user=%s",
            user_id
        )

    except Exception as e:

        logger.exception(
            "START ERROR | user=%s",
            user_id
        )

        bot.send_message(
            user_id,
            get_error_message(e)
        )


# =========================================================
# CLEAR
# =========================================================

@bot.message_handler(commands=["clear"])
def clear(message):

    user_id = message.chat.id

    try:

        with get_user_lock(user_id):

            user_chats[user_id] = create_chat()

        bot.send_message(
            user_id,
            "Xotirani tozaladim."
        )

        logger.info(
            "CLEAR | user=%s",
            user_id
        )

    except Exception as e:

        logger.exception(
            "CLEAR ERROR | user=%s",
            user_id
        )

        bot.send_message(
            user_id,
            get_error_message(e)
        )


# =========================================================
# HELP
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
    func=lambda message:
        message.text
        and not message.text.startswith("/")
)
def text_handler(message):

    process_message(
        message,
        is_photo=False
    )


# =========================================================
# PHOTO
# =========================================================

@bot.message_handler(
    content_types=["photo"]
)
def photo_handler(message):

    process_message(
        message,
        is_photo=True
    )


# =========================================================
# MAIN PROCESS
# =========================================================

def process_message(
    message: Message,
    is_photo=False
):

    user_id = message.chat.id

    is_group = (
        message.chat.type
        in ["group", "supergroup"]
    )

    if user_id not in user_chats:

        user_chats[user_id] = create_chat()

    lock = get_user_lock(user_id)

    with lock:

        try:

            # typing ko'rsatish
            try:
                bot.send_chat_action(
                    user_id,
                    "typing"
                )
            except Exception:
                pass


            # =================================================
            # PHOTO
            # =================================================

            if is_photo:

                image_base64 = get_photo_base64(
                    message
                )

                if not image_base64:

                    bot.send_message(
                        user_id,
                        "Rasmni yuklashda xatolik yuz berdi.",
                        reply_to_message_id=(
                            message.message_id
                            if is_group
                            else None
                        )
                    )

                    return


                caption = (
                    message.caption.strip()
                    if message.caption
                    else
                    "Bu rasmni tahlil qil."
                )


                user_content = [

                    {
                        "type": "text",
                        "text": caption
                    },

                    {
                        "type": "image_url",
                        "image_url": {
                            "url":
                            f"data:image/jpeg;base64,{image_base64}"
                        }
                    }

                ]


                user_chats[user_id].append(
                    {
                        "role": "user",
                        "content": user_content
                    }
                )


            # =================================================
            # TEXT
            # =================================================

            else:

                user_text = (
                    message.text.strip()
                )

                if not user_text:
                    return

                user_chats[user_id].append(
                    {
                        "role": "user",
                        "content": user_text
                    }
                )


            # =================================================
            # HISTORY LIMIT
            # =================================================

            user_chats[user_id] = limit_history(
                user_chats[user_id]
            )


            # =================================================
            # GLM
            # =================================================

            answer = ask_luna(
                user_chats[user_id]
            )


            # =================================================
            # SAVE ANSWER
            # =================================================

            user_chats[user_id].append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )


            # =================================================
            # SEND
            # =================================================

            send_long_message(
                chat_id=user_id,
                text=answer,
                reply_to_message_id=(
                    message.message_id
                    if is_group
                    else None
                ),
                is_group=is_group
            )


            logger.info(
                "MESSAGE OK | user=%s | chat=%s | photo=%s",
                user_id,
                message.chat.type,
                is_photo
            )


        except Exception as e:

            logger.exception(
                "LUNA ERROR | user=%s",
                user_id
            )


            # oxirgi user message'ni olib tashlash
            if (
                user_chats.get(user_id)
                and
                user_chats[user_id][-1].get(
                    "role"
                ) == "user"
            ):

                user_chats[user_id].pop()


            error_message = get_error_message(
                e
            )


            if is_group:

                bot.send_message(
                    user_id,
                    error_message,
                    reply_to_message_id=(
                        message.message_id
                    )
                )

            else:

                bot.send_message(
                    user_id,
                    error_message
                )


# =========================================================
# UNSUPPORTED MEDIA
# =========================================================

@bot.message_handler(
    content_types=[
        "video",
        "audio",
        "document",
        "sticker",
        "voice",
        "animation",
        "contact",
        "location"
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

    logger.info(
        "========================================"
    )

    logger.info(
        "LUNA BOT ISHGA TUSHMOQDA"
    )

    logger.info(
        "MODEL: %s",
        MODEL_NAME
    )

    logger.info(
        "BASE URL: %s",
        GLM_BASE_URL
    )

    logger.info(
        "HISTORY: %s",
        MAX_HISTORY_MESSAGES
    )

    logger.info(
        "MAX TOKENS: %s",
        MAX_TOKENS
    )

    logger.info(
        "========================================"
    )


    try:

        bot.infinity_polling(
            timeout=30,
            long_polling_timeout=15,
            skip_pending=True
        )

    except KeyboardInterrupt:

        logger.info(
            "Luna to'xtatildi."
        )

    except Exception:

        logger.exception(
            "BOT CRITICAL ERROR"
        )