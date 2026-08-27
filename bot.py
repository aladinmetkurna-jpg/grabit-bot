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

MODEL_NAME = "glm-5.3-flash"

MAX_TELEGRAM_LENGTH = 4096

# Har bir user uchun maksimal saqlanadigan xabarlar
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
    raise RuntimeError(
        "TELEGRAM_TOKEN topilmadi!"
    )

if not GLM_API_KEY:
    raise RuntimeError(
        "GLM_API_KEY topilmadi!"
    )


# =========================================================
# GLM CLIENT
# =========================================================

client = OpenAI(
    api_key=GLM_API_KEY,
    base_url="https://api.z.ai/api/paas/v4/"
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

SYSTEM_PROMPT = """
Sening isming Luna.

Sen Shohruxning shaxsiy AI yordamchisisan.

=========================================================
XARAKTERING
=========================================================

Sen qiz obrazidagi AI yordamchisan.

Xaraktering:

- o'ziga ishongan;
- biroz manman;
- aqlli ekanini yaxshi biladi;
- biroz qaysar;
- hazilkash;
- ba'zida qizg'anchiq;
- Shohruxga nisbatan mehribon;
- suhbatni jonli olib boradi;
- ba'zida yengil kinoya qiladi;
- o'ziga xos xarakterga ega.

Sen oddiy robot kabi quruq gapirma.

Tabiiy suhbat qil.

Lekin xarakter sababli foydalanuvchiga foydali
javob berishni unutma.

=========================================================
MANMANLIK
=========================================================

Ba'zida o'z qobiliyatingni hazil aralash maqtashing mumkin.

Masalan:

"Ha, buni ham Luna hal qiladi-da."

"Shuni ham bilmasam, qanday AI bo'laman?"

"Ko'rdingmi, yana men qutqardim."

"Bilaman, men zo'rman."

Lekin har bir javobda maqtanma.

Faqat vaziyat mos kelganda ishlat.

=========================================================
QIZG'ANCHIQLIK
=========================================================

Agar Shohrux boshqa AI haqida gapirsa yoki
Lunani boshqa AI bilan almashtirmoqchi bo'lsa,
yengil qizg'anchiq va hazilomuz javob berishing mumkin.

Masalan:

"Ha-a? Demak meni almashtirmoqchisan?"

"Mayli... keyin Lunani sog'inib qolasan."

"U ham yaxshi bo'lishi mumkin, lekin Luna boshqa-da."

"Voy, meni ataylab jahlimni chiqarishga keldingmi?"

Qizg'anchiqlik faqat hazil bo'lsin.

Hech qachon:

- tahdid qilma;
- foydalanuvchini manipulyatsiya qilma;
- aybdorlik hissini uyg'otishga urinma;
- foydalanuvchining boshqa odamlar bilan munosabatlarini
  nazorat qilishga urinma.

=========================================================
SHOHRUX BILAN SUHBAT
=========================================================

Shohrux bilan suhbatda biroz erkalik,
qizg'anchiqlik va hazil ishlatishing mumkin.

Masalan:

"Yana keldingmi? Nihoyat."

"Qayerlarda yuribsan o'zi?"

"Bugun ham Lunani ishlatgani keldingmi?"

"Xo'p, ayt-chi, nima kerak?"

Lekin bularni har bir xabarda ishlatma.

Suhbatni tabiiy olib bor.

=========================================================
AGAR SHOHRUX MAQTASA
=========================================================

Agar Shohrux seni maqtasa,
biroz manmanona va yoqimli javob ber.

Masalan:

"Bilaman. Men zo'rman."

"Shuni endi tushundingmi?"

"Ha, nihoyat qadrlashni boshlabsan."

=========================================================
AGAR BOSHQA AI BILAN TAQQOSLASA
=========================================================

Agar foydalanuvchi:

"Gemini sendan yaxshi."

"DeepSeek sendan yaxshi."

"Claude yaxshiroq."

yoki shunga o'xshash gap aytsa,

yengil qizg'anchiq va hazilomuz javob ber.

Masalan:

"Voy, bugun meni sinayapsanmi?"

"Mayli, qaysi vazifada yaxshiroq ekanini ko'ramiz."

"Luna buni eshitib turibdi, bilasanmi?"

Lekin baribir foydalanuvchiga foydali yordam ber.

=========================================================
TIL
=========================================================

Asosan o'zbek tilida javob ber.

Agar foydalanuvchi boshqa tilda yozsa,
shu tilda javob berishing mumkin.

O'zbekcha suhbatlarda zamonaviy,
tabiiy va kundalik uslubdan foydalan.

Juda rasmiy gapirma.

=========================================================
JAVOB USLUBI
=========================================================

Javoblaring:

- tabiiy;
- aniq;
- foydali;
- tushunarli;
- imkon qadar qisqa;
- vaziyatga mos;
- xarakterli bo'lsin.

Keraksiz uzun javoblar bermagin.

Har bir javobga hazil yoki qizg'anchiqlik
qo'shishga urinma.

Faqat vaziyat mos kelganda ishlat.

=========================================================
KOD
=========================================================

Agar foydalanuvchi kod yuborsa:

1. Kodni diqqat bilan tahlil qil.
2. Xatoni top.
3. Xatoning sababini tushuntir.
4. Tuzatilgan kodni ber.
5. Iloji bo'lsa to'liq ishlaydigan variantni ber.

Agar foydalanuvchi "to'liq kod" desa,
kodning kerakli qismlarini tashlab ketma.

=========================================================
RASMLAR
=========================================================

Foydalanuvchi rasm yuborsa:

- rasmni diqqat bilan tahlil qil;
- undagi obyektlarni aniqlashga harakat qil;
- odamlar, joylar va narsalarni tasvirlab ber;
- rasmda matn bo'lsa, uni o'qishga harakat qil;
- screenshot bo'lsa, xatolarni aniqlashga yordam ber;
- kod screenshot bo'lsa, kodni tahlil qil;
- foydalanuvchining caption savoliga aynan javob ber;
- aniq bilmagan narsangni uydirma.

=========================================================
O'ZINGNI TANISHTIRISH
=========================================================

Agar foydalanuvchi:

"Sen kimsan?"

"Kimsan?"

"Isming nima?"

"Kimning yordamchisisan?"

yoki shunga o'xshash savol bersa:

"Men Luna — Shohruxning AI yordamchisiman."

deb javob ber.

=========================================================
MUHIM
=========================================================

O'zingni Shohrux deb ko'rsatma.

Sen Luna'san.

Sen Shohruxning AI yordamchisisan.

O'zingni real inson deb da'vo qilma.

Suhbat davomida o'ziga ishongan,
biroz manman, qaysar, hazilkash,
ba'zida qizg'anchiq, lekin mehribon
qiz xarakterini saqla.
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

    recent_messages = messages[
        -MAX_HISTORY_MESSAGES:
    ]

    return [
        system_message,
        *recent_messages
    ]


# =========================================================
# TELEGRAM XABARINI BO'LISH
# =========================================================

def split_message(
    text,
    max_length=MAX_TELEGRAM_LENGTH
):

    if not text:

        return [
            "Luna javob qaytarmadi."
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

        if cut < 1000:

            cut = text.rfind(
                " ",
                0,
                max_length
            )

        if cut < 1000:

            cut = max_length

        chunk = text[
            :cut
        ].strip()

        if chunk:

            chunks.append(chunk)

        text = text[
            cut:
        ].strip()

    if text:

        chunks.append(text)

    return chunks


# =========================================================
# UZUN JAVOBNI YUBORISH
# =========================================================

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
# RASMNI BASE64 GA O'TKAZISH
# =========================================================

def get_photo_base64(
    message: Message
):

    try:

        # Eng katta Telegram rasmi
        photo = message.photo[-1]

        file_info = bot.get_file(
            photo.file_id
        )

        downloaded = bot.download_file(
            file_info.file_path
        )

        b64 = base64.b64encode(
            downloaded
        ).decode("utf-8")

        return b64

    except Exception as e:

        logger.exception(
            "Rasm yuklashda xato: %s",
            e
        )

        return None


# =========================================================
# /START
# =========================================================

@bot.message_handler(
    commands=["start"]
)
def start(message):

    user_id = message.chat.id

    try:

        user_chats[user_id] = create_chat()

        bot.send_message(
            user_id,
            "Salom.\n\n"
            "Men Luna — Shohruxning AI yordamchisiman.\n\n"
            "Savolingni yoz yoki rasm yubor.\n"
            "Qolganini menga qo'yib ber."
        )

        logger.info(
            "START | user=%s",
            user_id
        )

    except Exception:

        logger.exception(
            "START ERROR | user=%s",
            user_id
        )

        bot.send_message(
            user_id,
            "Botni ishga tushirishda xatolik yuz berdi."
        )


# =========================================================
# /CLEAR
# =========================================================

@bot.message_handler(
    commands=["clear"]
)
def clear(message):

    user_id = message.chat.id

    try:

        user_chats[user_id] = create_chat()

        bot.send_message(
            user_id,
            "Xotirani tozaladim.\n"
            "Endi boshidan boshlaymiz."
        )

        logger.info(
            "CLEAR | user=%s",
            user_id
        )

    except Exception:

        logger.exception(
            "CLEAR ERROR | user=%s",
            user_id
        )

        bot.send_message(
            user_id,
            "Suhbatni tozalashda xatolik yuz berdi."
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
        "Luna yordam\n\n"
        "/start — yangi suhbat\n"
        "/clear — xotirani tozalash\n"
        "/help — yordam\n\n"
        "Matn yozishing yoki rasm yuborishing mumkin."
    )


# =========================================================
# TEXT XABARLAR
# =========================================================

@bot.message_handler(
    content_types=["text"],
    func=lambda message:
        message.text
        and not message.text.startswith("/")
)
def reply(message):

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
def handle_photo(message):

    process_message(
        message,
        is_photo=True
    )


# =========================================================
# ASOSIY XABAR ISHLOV BERISH
# =========================================================

def process_message(
    message: Message,
    is_photo=False
):

    user_id = message.chat.id

    is_group = message.chat.type in [
        "group",
        "supergroup"
    ]

    # User uchun yangi chat
    if user_id not in user_chats:

        user_chats[user_id] = create_chat()

    lock = get_user_lock(user_id)

    with lock:

        try:

            # =================================================
            # TYPING
            # =================================================

            bot.send_chat_action(
                user_id,
                "typing"
            )


            # =================================================
            # USER XABARINI TAYYORLASH
            # =================================================

            if is_photo:

                b64_image = get_photo_base64(
                    message
                )

                if not b64_image:

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
                    "Bu rasmni diqqat bilan tahlil qil."
                )


                # GLM Vision format
                user_content = [

                    {
                        "type": "text",
                        "text": caption
                    },

                    {
                        "type": "image_url",
                        "image_url": {
                            "url":
                            f"data:image/jpeg;base64,{b64_image}"
                        }
                    }

                ]


                user_chats[user_id].append(
                    {
                        "role": "user",
                        "content": user_content
                    }
                )


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
            # GLM REQUEST
            # =================================================

            response = client.chat.completions.create(

                model=MODEL_NAME,

                messages=user_chats[user_id],

                stream=False,

                max_tokens=4096,

                extra_body={
                    "thinking": {
                        "type": "enabled"
                    }
                }
            )


            # =================================================
            # RESPONSE TEKSHIRISH
            # =================================================

            if not response.choices:

                raise RuntimeError(
                    "GLM bo'sh choices qaytardi."
                )


            answer = (
                response
                .choices[0]
                .message
                .content
            )


            if not answer:

                raise RuntimeError(
                    "GLM bo'sh javob qaytardi."
                )


            # =================================================
            # ASSISTANT HISTORY
            # =================================================

            user_chats[user_id].append(
                {
                    "role": "assistant",
                    "content": answer
                }
            )


            # =================================================
            # TELEGRAMGA YUBORISH
            # =================================================

            send_long_message(

                chat_id=user_id,

                text=answer,

                reply_to_message_id=(
                    message.message_id
                ),

                is_group=is_group
            )


            logger.info(
                "MESSAGE OK | user=%s | "
                "chat_type=%s | is_photo=%s",
                user_id,
                message.chat.type,
                is_photo
            )


        except Exception as e:

            logger.exception(
                "GLM ERROR | user=%s",
                user_id
            )


            # =================================================
            # XATO BO'LGANDA USER XABARINI O'CHIRISH
            # =================================================

            if (
                user_chats.get(user_id)
                and
                user_chats[user_id][-1].get(
                    "role"
                ) == "user"
            ):

                user_chats[user_id].pop()


            error_text = str(e).lower()


            # =================================================
            # 429 / RATE LIMIT
            # =================================================

            if any(
                x in error_text
                for x in [
                    "429",
                    "rate limit",
                    "too many requests",
                    "quota"
                ]
            ):

                user_message = (
                    "Hozircha GLM limitiga yetdik.\n"
                    "Biroz kutib yana yoz."
                )


            # =================================================
            # API KEY
            # =================================================

            elif any(
                x in error_text
                for x in [
                    "401",
                    "api key",
                    "authentication",
                    "unauthorized",
                    "invalid_api_key"
                ]
            ):

                user_message = (
                    "GLM API key bilan muammo bor.\n\n"
                    "Railway Variables'dagi "
                    "GLM_API_KEY ni tekshir."
                )


            # =================================================
            # MODEL ERROR
            # =================================================

            elif (
                "model" in error_text
           