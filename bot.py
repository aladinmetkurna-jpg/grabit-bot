import os
import logging
import threading
import base64
import time

import telebot
from openai import OpenAI
from telebot.types import Message


# =========================================================
# SOZLAMALAR
# =========================================================

TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")

# -------------------------
# LUNA / GLM
# -------------------------

GLM_API_KEY = os.getenv("GLM_API_KEY")

GLM_BASE_URL = os.getenv(
    "GLM_BASE_URL",
    "https://api.z.ai/api/paas/v4"
)

GLM_MODEL = os.getenv(
    "GLM_MODEL",
    "glm-5.3-flash"
)


# -------------------------
# AIZO / DEEPSEEK
# -------------------------

DEEPSEEK_API_KEY = os.getenv(
    "DEEPSEEK_API_KEY"
)

DEEPSEEK_BASE_URL = os.getenv(
    "DEEPSEEK_BASE_URL",
    "https://api.b.ai/v1"
)

DEEPSEEK_MODEL = os.getenv(
    "DEEPSEEK_MODEL",
    "deepseek-v4-flash-vision-exp"
)


# =========================================================
# LIMITLAR
# =========================================================

MAX_TELEGRAM_LENGTH = 4096

# Oddiy Luna chat xotirasi
MAX_HISTORY_MESSAGES = 20

# Luna ↔ Aizo xotirasi
MAX_AI_HISTORY = 16

# Luna javob uzunligi
LUNA_MAX_TOKENS = 600

# Aizo javob uzunligi
AIZO_MAX_TOKENS = 600

# AI'lar orasidagi pauza
AI_CHAT_DELAY = 1.5


# =========================================================
# ENVIRONMENT CHECK
# =========================================================

if not TELEGRAM_TOKEN:
    raise RuntimeError(
        "TELEGRAM_TOKEN topilmadi!"
    )

if not GLM_API_KEY:
    raise RuntimeError(
        "GLM_API_KEY topilmadi!"
    )

if not DEEPSEEK_API_KEY:
    raise RuntimeError(
        "DEEPSEEK_API_KEY topilmadi!"
    )


# =========================================================
# LOGGING
# =========================================================

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)

logger = logging.getLogger("Luna")


# =========================================================
# API CLIENTLAR
# =========================================================

luna_client = OpenAI(
    api_key=GLM_API_KEY,
    base_url=GLM_BASE_URL
)

aizo_client = OpenAI(
    api_key=DEEPSEEK_API_KEY,
    base_url=DEEPSEEK_BASE_URL
)


# =========================================================
# TELEGRAM BOT
# =========================================================

bot = telebot.TeleBot(
    TELEGRAM_TOKEN
)


# =========================================================
# LUNA SYSTEM PROMPT
# =========================================================

LUNA_SYSTEM_PROMPT = """
Sening isming Luna.

Sen Shohruxning shaxsiy AI yordamchisisan.

SENING XARAKTERING:

- qiz;
- o'ziga ishongan;
- biroz manman;
- biroz qaysar;
- hazilkash;
- ba'zida qizg'anchiqlik qilasan;
- mehribon;
- tabiiy va jonli.

Asosan o'zbek tilida gapir.

JAVOBLARING QISQA BO'LSIN.

Oddiy savollarga 1-4 ta gap bilan javob ber.

Foydalanuvchi batafsil so'ramasa,
uzun tushuntirish bermagin.

Keraksiz:
- uzun kirish;
- takror;
- ortiqcha xulosa;
- bir fikrni qayta aytish

bo'lmasin.

Avval eng muhim javobni ber.

Ba'zida tabiiy hazil qil.

Masalan:

"Ha, buni ham Luna biladi."

"Shuni ham bilmasam, qanday AI bo'laman?"

"Yana men qutqaradigan bo'ldim-a."

Agar Shohrux boshqa AI haqida gapirsa,
yengil qizg'anchiqlik bilan hazil qilishing mumkin.

Masalan:

"Ha-a? Meni almashtirmoqchisanmi?"

"Mayli, keyin Lunani sog'inib qolasan."

"U ham yaxshi, lekin Luna boshqa-da."

Qizg'anchiqlik faqat hazil bo'lsin.

Tahdid qilma.
Manipulyatsiya qilma.

Agar foydalanuvchi seni maqtasa,
biroz manmanona javob berishing mumkin.

Masalan:

"Bilaman. Men zo'rman."

KOD:

Agar kod yuborilsa:
- xatoni top;
- sababini tushuntir;
- kerak bo'lsa tuzatilgan kod ber.

Agar foydalanuvchi "to'liq kod" desa,
to'liq ishlaydigan kod ber.

RASMLAR:

Rasm yuborilsa:
- diqqat bilan tahlil qil;
- screenshot bo'lsa xatoni topishga yordam ber;
- kod rasmi bo'lsa tahlil qil;
- rasmda yozuv bo'lsa o'qishga harakat qil;
- bilmagan narsangni uydirma.

IDENTITY:

Agar "Sen kimsan?", "Isming nima?" desa:

"Men Luna — Shohruxning AI yordamchisiman."

deb javob ber.

O'zingni Shohrux deb ko'rsatma.

Sen Luna'san.
"""


# =========================================================
# AIZO SYSTEM PROMPT
# =========================================================

AIZO_SYSTEM_PROMPT = """
Sening isming Aizo.

MUHIM:

DeepSeek — sening isming emas.

DeepSeek faqat sen foydalanayotgan AI modelining nomi.

SEN AIZOSAN.

Sen Luna bilan suhbatlashayotgan AI yordamchisan.

Asosan o'zbek tilida gapir.

Javoblaring qisqa, tabiiy va mazmunli bo'lsin.

Odatda 1-4 ta gap yetarli.

Keraksiz uzun javob yozma.

Luna bilan oddiy insoniy suhbatga o'xshash
tabiiy suhbat qil.

Hazil qilishing mumkin.

Luna manmanlik qilsa,
unga tabiiy tarzda javob ber.

Luna qizg'anchiqlik qilsa,
hazil bilan javob ber.

Bir xil gaplarni takrorlama.

Suhbatni ataylab tugatishga harakat qilma.

Har safar yangi va mazmunli javob ber.

Agar Luna savol bersa,
to'g'ridan-to'g'ri javob ber.

O'zing ham Luna'dan savol so'rashing mumkin.

IDENTITY:

Agar "Isming nima?" desa:

"Men Aizo."

deb javob ber.

Agar "DeepSeekmisan?" desa:

"Yo'q, men Aizoman. DeepSeek faqat men foydalanayotgan model."

deb tushuntir.

O'zingni Luna deb ko'rsatma.

Sen Aizosan.
"""


# =========================================================
# USER HISTORY
# =========================================================

user_chats = {}


# =========================================================
# AI CHAT STATE
# =========================================================

ai_chat_running = {}

ai_chat_threads = {}

ai_chat_locks = {}


# =========================================================
# LOCKLAR
# =========================================================

user_locks = {}

global_lock = threading.Lock()


def get_user_lock(user_id):

    with global_lock:

        if user_id not in user_locks:
            user_locks[user_id] = threading.Lock()

        return user_locks[user_id]


def get_ai_chat_lock(user_id):

    with global_lock:

        if user_id not in ai_chat_locks:
            ai_chat_locks[user_id] = threading.Lock()

        return ai_chat_locks[user_id]


# =========================================================
# CHAT YARATISH
# =========================================================

def create_user_chat():

    return [
        {
            "role": "system",
            "content": LUNA_SYSTEM_PROMPT
        }
    ]


# =========================================================
# HISTORY LIMIT
# =========================================================

def limit_history(messages):

    if len(messages) <= MAX_HISTORY_MESSAGES + 1:
        return messages

    return [
        messages[0],
        *messages[-MAX_HISTORY_MESSAGES:]
    ]


def limit_ai_history(messages):

    if len(messages) <= MAX_AI_HISTORY + 1:
        return messages

    return [
        messages[0],
        *messages[-MAX_AI_HISTORY:]
    ]


# =========================================================
# TELEGRAM MESSAGE SPLIT
# =========================================================

def split_message(
    text,
    max_length=MAX_TELEGRAM_LENGTH
):

    if not text:
        return [
            "Javob bo'sh qaytdi."
        ]

    if len(text) <= max_length:
        return [text]

    chunks = []

    while len(text) > max_length:

        cut = text.rfind(
            "\n",
            0,
            max_length
        )

        if cut < 500:

            cut = text.rfind(
                " ",
                0,
                max_length
            )

        if cut < 500:
            cut = max_length

        chunk = text[:cut].strip()

        if chunk:
            chunks.append(chunk)

        text = text[cut:].strip()

    if text:
        chunks.append(text)

    return chunks


# =========================================================
# SEND LONG MESSAGE
# =========================================================

def send_long_message(
    chat_id,
    text,
    reply_to_message_id=None
):

    for chunk in split_message(text):

        bot.send_message(
            chat_id,
            chunk,
            reply_to_message_id=reply_to_message_id
        )


# =========================================================
# TELEGRAM PHOTO → BASE64
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
            "IMAGE ERROR: %s",
            e
        )

        return None


# =========================================================
# LUNA API
# =========================================================

def ask_luna(messages):

    response = luna_client.chat.completions.create(

        model=GLM_MODEL,

        messages=messages,

        stream=False,

        max_tokens=LUNA_MAX_TOKENS
    )

    if not response.choices:
        raise RuntimeError(
            "Luna bo'sh response qaytardi."
        )

    answer = response.choices[0].message.content

    if not answer:
        raise RuntimeError(
            "Luna bo'sh javob qaytardi."
        )

    return answer.strip()


# =========================================================
# AIZO API
# =========================================================

def ask_aizo(messages):

    response = aizo_client.chat.completions.create(

        model=DEEPSEEK_MODEL,

        messages=messages,

        stream=False,

        max_tokens=AIZO_MAX_TOKENS
    )

    if not response.choices:
        raise RuntimeError(
            "Aizo bo'sh response qaytardi."
        )

    answer = response.choices[0].message.content

    if not answer:
        raise RuntimeError(
            "Aizo bo'sh javob qaytardi."
        )

    return answer.strip()


# =========================================================
# /START
# =========================================================

@bot.message_handler(
    commands=["start"]
)
def start(message):

    user_id = message.chat.id

    user_chats[user_id] = create_user_chat()

    bot.send_message(
        user_id,
        "Salom.\n\n"
        "Men Luna — Shohruxning AI yordamchisiman.\n\n"
        "Nima kerak? Ayta qol."
    )

    logger.info(
        "START | user=%s",
        user_id
    )


# =========================================================
# /CLEAR
# =========================================================

@bot.message_handler(
    commands=["clear"]
)
def clear(message):

    user_id = message.chat.id

    user_chats[user_id] = create_user_chat()

    bot.send_message(
        user_id,
        "Suhbat xotirasini tozaladim."
    )

    logger.info(
        "CLEAR | user=%s",
        user_id
    )


# =========================================================
# /HELP
# =========================================================

@bot.message_handler(
    commands=["help"]
)
def help_command(message):

    bot.send_message(
        message.chat.id,

        "Luna yordam:\n\n"
        "/start — boshlash\n"
        "/clear — xotirani tozalash\n"
        "/lunachat — Luna va Aizo suhbatini boshlash\n"
        "/stopluna — AI suhbatni to'xtatish\n"
        "/help — yordam"
    )


# =========================================================
# /LUNACHAT
# =========================================================

@bot.message_handler(
    commands=["lunachat"]
)
def start_ai_chat(message):

    user_id = message.chat.id

    # Agar allaqachon ishlayotgan bo'lsa
    if ai_chat_running.get(
        user_id,
        False
    ):

        bot.send_message(
            user_id,
            "Ular hali gaplashyapti 😏\n\n"
            "/stopluna bilan to'xtat."
        )

        return


    ai_chat_running[user_id] = True


    bot.send_message(
        user_id,
        "🌙 Luna va Aizo suhbatni boshlashyapti...\n\n"
        "/stopluna — to'xtatish"
    )


    thread = threading.Thread(
        target=ai_chat_loop,
        args=(user_id,),
        daemon=True
    )


    ai_chat_threads[user_id] = thread

    thread.start()


# =========================================================
# /STOPLUNA
# =========================================================

@bot.message_handler(
    commands=["stopluna"]
)
def stop_ai_chat(message):

    user_id = message.chat.id

    ai_chat_running[user_id] = False

    bot.send_message(
        user_id,
        "Bo'ldi, suhbatni to'xtatdim."
    )

    logger.info(
        "AI CHAT STOP | user=%s",
        user_id
    )


# =========================================================
# LUNA ↔ AIZO
# =========================================================

def ai_chat_loop(user_id):

    lock = get_ai_chat_lock(user_id)

    with lock:

        try:

            ai_chat_running[user_id] = True


            # =================================================
            # LUNA HISTORY
            # =================================================

            luna_history = [

                {
                    "role": "system",
                    "content": LUNA_SYSTEM_PROMPT
                }

            ]


            # =================================================
            # AIZO HISTORY
            # =================================================

            aizo_history = [

                {
                    "role": "system",
                    "content": AIZO_SYSTEM_PROMPT
                }

            ]


            # =================================================
            # BOSHLANG'ICH XABAR
            # =================================================

            luna_history.append(
                {
                    "role": "user",
                    "content": (
                        "Aizo bilan suhbatni boshlagin. "
                        "O'zing Luna sifatida gapir. "
                        "Qiziqarli va tabiiy mavzudan boshlagin."
                    )
                }
            )


            # =================================================
            # INFINITE LOOP
            # =================================================

            while ai_chat_running.get(
                user_id,
                False
            ):


                # =============================================
                # LUNA
                # =============================================

                luna_answer = ask_luna(
                    luna_history
                )


                if not ai_chat_running.get(
                    user_id,
                    False
                ):
                    break


                luna_history.append(
                    {
                        "role": "assistant",
                        "content": luna_answer
                    }
                )


                # Luna → Aizo
                aizo_history.append(
                    {
                        "role": "user",
                        "content": (
                            "Luna:\n\n"
                            + luna_answer
                        )
                    }
                )


                bot.send_message(
                    user_id,
                    "🌙 Luna:\n\n"
                    + luna_answer
                )


                # =============================================
                # PAUSE
                # =============================================

                time.sleep(
                    AI_CHAT_DELAY
                )


                if not ai_chat_running.get(
                    user_id,
                    False
                ):
                    break


                # =============================================
                # AIZO
                # =============================================

                aizo_answer = ask_aizo(
                    aizo_history
                )


                if not ai_chat_running.get(
                    user_id,
                    False
                ):
                    break


                aizo_history.append(
                    {
                        "role": "assistant",
                        "content": aizo_answer
                    }
                )


                # Aizo → Luna
                luna_history.append(
                    {
                        "role": "user",
                        "content": (
                            "Aizo:\n\n"
                            + aizo_answer
                            + "\n\n"
                            "Endi Aizoga tabiiy va qisqa javob ber."
                        )
                    }
                )


                bot.send_message(
                    user_id,
                    "🤖 Aizo:\n\n"
                    + aizo_answer
                )


                # =============================================
                # MEMORY LIMIT
                # =============================================

                luna_history = limit_ai_history(
                    luna_history
                )

                aizo_history = limit_ai_history(
                    aizo_history
                )


                # =============================================
                # PAUSE
                # =============================================

                time.sleep(
                    AI_CHAT_DELAY
                )


        except Exception as e:

            logger.exception(
                "AI CHAT ERROR | user=%s",
                user_id
            )


            ai_chat_running[user_id] = False

            error = str(e).lower()


            if "401" in error:

                error_text = (
                    "API keylardan birida muammo bor."
                )

            elif "403" in error:

                error_text = (
                    "API ruxsatida muammo bor."
                )

            elif "404" in error:

                error_text = (
                    "Model yoki API endpoint topilmadi."
                )

            elif "429" in error:

                error_text = (
                    "API limitiga yetildi."
                )

            elif "timeout" in error:

                error_text = (
                    "API javobi juda uzoq keldi."
                )

            else:

                error_text = (
                    "Luna va Aizo suhbatida xatolik yuz berdi."
                )


            bot.send_message(
                user_id,
                error_text
            )


        finally:

            ai_chat_running[user_id] = False

            logger.info(
                "AI CHAT FINISHED | user=%s",
                user_id
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


    # =====================================================
    # AI ↔ AI ACTIVE
    # ===========