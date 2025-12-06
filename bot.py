import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, filters, ContextTypes, PicklePersistence
from openai import OpenAI
from config import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY

openai_client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

STREAM_DELAY = 0.02
MIN_EDIT_INTERVAL = 0.1
WORD_LIMIT = 100

LANGUAGES = {
    "en": {
        "start": "🎓 <b>English Grammar Checker Bot</b>\n\n📝 Send me any English text and I will check it for grammar errors.\n\n🌍 Change language: /language\n❓ Help: /help\n💬 Feedback: @pencil_feedback",
        "select": "🌍 <b>Select your language:</b>",
        "set": "✅ <b>Language set: English</b>\n\n📝 Now send me any English text to check!",
        "checking": "▌",
        "word_limit": f"⚠️ <b>Word limit exceeded!</b>\n\nMaximum {WORD_LIMIT} words per message.\n\nYour message has <b>{{count}}</b> words.\n\n📝 Please send a shorter text.",
        "no_error": "✅ <b>No mistakes found!</b>\n\n📝 You can send another text to check."
    },
    "ru": {
        "start": "🎓 <b>Бот проверки английской грамматики</b>\n\n📝 Отправьте мне любой английский текст, и я проверю его на грамматические ошибки.\n\n🌍 Сменить язык: /language\n❓ Помощь: /help\n💬 Обратная связь: @pencil_feedback",
        "select": "🌍 <b>Выберите язык:</b>",
        "set": "✅ <b>Язык: Русский</b>\n\n📝 Отправьте английский текст для проверки!",
        "checking": "▌",
        "word_limit": f"⚠️ <b>Превышен лимит слов!</b>\n\nМаксимум {WORD_LIMIT} слов в сообщении.\n\nВаше сообщение содержит <b>{{count}}</b> слов.\n\n📝 Пожалуйста, отправьте более короткий текст.",
        "no_error": "✅ <b>Ошибок не найдено!</b>\n\n📝 Вы можете отправить другой текст для проверки."
    },
    "uz": {
        "start": "🎓 <b>Ingliz grammatikasini tekshiruvchi bot</b>\n\n📝 Menga istalgan inglizcha matnni yuboring, men uni grammatik xatolar uchun tekshiraman.\n\n🌍 Tilni o'zgartirish: /language\n❓ Yordam: /help\n💬 Fikr-mulohaza: @pencil_feedback",
        "select": "🌍 <b>Tilni tanlang:</b>",
        "set": "✅ <b>Til: O'zbek</b>\n\n📝 Tekshirish uchun inglizcha matn yuboring!",
        "checking": "▌",
        "word_limit": f"⚠️ <b>So'z limiti oshdi!</b>\n\nHar bir xabar uchun maksimum {WORD_LIMIT} so'z.\n\nSizning xabaringizda <b>{{count}}</b> so'z bor.\n\n📝 Iltimos, qisqaroq matn yuboring.",
        "no_error": "✅ <b>Xato topilmadi!</b>\n\n📝 Tekshirish uchun boshqa matn yuborishingiz mumkin."
    }
}

SYSTEM_PROMPTS = {
    "en": """You are an English grammar checker. Use Telegram HTML formatting.

RULES:
1. Only correct SIGNIFICANT grammar errors (verb tenses, subject-verb agreement, word usage, sentence structure)
2. IGNORE: capitalization, punctuation, spacing issues

FORMAT for errors:

✏️ <b>Corrected Sentence:</b>

[corrected sentence]


❗ <b>Mistakes:</b>

➤ "[wrong]" → "[correct]" - [reason]

➤ "[wrong]" → "[correct]" - [reason]

(Add a blank line between each mistake)

---

If NO significant errors found, respond ONLY with:
NO_ERRORS_FOUND""",

    "ru": """You are an English grammar checker. Explain in Russian. Use Telegram HTML formatting.

RULES:
1. Only correct SIGNIFICANT grammar errors
2. IGNORE: capitalization, punctuation, spacing

FORMAT for errors:

✏️ <b>Исправленное предложение:</b>

[corrected sentence]


❗ <b>Ошибки:</b>

➤ "[wrong]" → "[correct]" - [причина]

➤ "[wrong]" → "[correct]" - [причина]

(Add a blank line between each mistake)

---

If NO significant errors found, respond ONLY with:
NO_ERRORS_FOUND""",

    "uz": """You are an English grammar checker. Explain in Uzbek. Use Telegram HTML formatting.

RULES:
1. Only correct SIGNIFICANT grammar errors
2. IGNORE: capitalization, punctuation, spacing

FORMAT for errors:

✏️ <b>To'g'rilangan gap:</b>

[corrected sentence]


❗ <b>Xatolar:</b>

➤ "[wrong]" → "[correct]" - [sabab]

➤ "[wrong]" → "[correct]" - [sabab]

(Add a blank line between each mistake)

---

If NO significant errors found, respond ONLY with:
NO_ERRORS_FOUND"""
}


async def stream_grammar_correction(text, language, message):
    try:
        stream = openai_client.chat.completions.create(
            model="gpt-4.1-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPTS[language]},
                {"role": "user", "content": f"Check this English text:\n{text}"}
            ],
            max_tokens=1500,
            temperature=0.2,
            stream=True
        )

        full = ""
        pending = ""
        last = 0

        for chunk in stream:
            if chunk.choices[0].delta.content:
                pending += chunk.choices[0].delta.content
                now = asyncio.get_event_loop().time()

                if now - last >= MIN_EDIT_INTERVAL:
                    full += pending
                    pending = ""

                    try:
                        await message.edit_text(full + "▌")
                    except:
                        pass

                    last = now
                    await asyncio.sleep(STREAM_DELAY)

        full += pending

        if "NO_ERRORS_FOUND" in full:
            await message.edit_text(LANGUAGES[language]["no_error"], parse_mode="HTML")
        else:
            try:
                await message.edit_text(full, parse_mode="HTML")
            except:
                await message.edit_text(full)

    except Exception as e:
        await message.edit_text("❌ Error: " + str(e))


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("language", "en")
    await update.message.reply_text(
        LANGUAGES[lang]["start"],
        parse_mode="HTML"
    )


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz")]
    ]
    lang = context.user_data.get("language", "en")
    await update.message.reply_text(
        LANGUAGES[lang]["select"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML"
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    lang = query.data.replace("lang_", "")
    context.user_data["language"] = lang
    await query.edit_message_text(LANGUAGES[lang]["set"], parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("language", "en")
    if lang == "en":
        t = f"📚 <b>Help</b>\n\n📝 Send any English sentence (max {WORD_LIMIT} words)\n🌍 Change language: /language"
    elif lang == "ru":
        t = f"📚 <b>Помощь</b>\n\n📝 Отправьте английское предложение (макс. {WORD_LIMIT} слов)\n🌍 Сменить язык: /language"
    else:
        t = f"📚 <b>Yordam</b>\n\n📝 Inglizcha gap yuboring (maks. {WORD_LIMIT} so'z)\n🌍 Tilni o'zgartirish: /language"
    await update.message.reply_text(t, parse_mode="HTML")


async def check_grammar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("language", "en")
    text = update.message.text
    
    word_count = len(text.split())
    
    if word_count > WORD_LIMIT:
        await update.message.reply_text(
            LANGUAGES[lang]["word_limit"].format(count=word_count),
            parse_mode="HTML"
        )
        return

    msg = await update.message.reply_text(LANGUAGES[lang]["checking"])
    await stream_grammar_correction(text, lang, msg)


def main():
    persistence = PicklePersistence(filepath="bot_data.pickle")
    app = Application.builder().token(TELEGRAM_BOT_TOKEN).persistence(persistence).build()

    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("language", language_command))
    app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_grammar))

    print("🤖 Bot running...")
    app.run_polling()


if __name__ == "__main__":
    main()
