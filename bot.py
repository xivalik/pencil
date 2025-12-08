import logging
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes,
    PicklePersistence
)
from openai import OpenAI
from config import TELEGRAM_BOT_TOKEN, OPENAI_API_KEY

# Validate environment variables
if not TELEGRAM_BOT_TOKEN:
    raise ValueError("BOT_TOKEN environment variable is not set!")
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY environment variable is not set!")

openai_client = OpenAI(api_key=OPENAI_API_KEY)

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

WORD_LIMIT = 100

# ---------------- LANGUAGE DATA ----------------
LANGUAGES = {
    "en": {
        "start": "🎓 <b>English Grammar Checker Bot</b>\n\n📝 Send me any English text and I will check it for grammar errors.\n\n🌍 Change language: /language\n❓ Help: /help\n💡 Feedback: @pencil_fbot",
        "select": "🌍 <b>Select your language:</b>",
        "set": "<b>Language set: 🇬🇧English</b>\n\n📝 Now you can send me any English text to check!",
        "checking": "⏳checking…",
        "word_limit": f"⚠️ <b>Word limit exceeded!</b>\n\nMaximum {WORD_LIMIT} words per message.\nYour message has <b>{{count}}</b> words.\n\n📝 Please send a shorter text.",
        "no_error": "✅ <b>No mistakes found!</b>\n\n📝 You can send another text to check.",
        "no_english": "🚫 <b>I think the text is not in English.</b>\n\n❕ Please send text only in English!"
    },
    "ru": {
        "start": "🎓 <b>Бот для проверки грамматики английского языка</b>\n\n📝 Отправьте любой текст на английском, и я исправлю грамматические ошибки.\n\n🌍 Сменить язык: /language\n❓ Помощь: /help\n💡 Обратная связь: @pencil_fbot",
        "select": "🌍 <b>Выберите язык:</b>",
        "set": "<b>Язык установлен: 🇷🇺Русский</b>\n\n📝 Теперь вы можете отправлять текст на английском для проверки!",
        "checking": "⏳ проверяю…",
        "word_limit": f"⚠️ <b>Превышен лимит слов!</b>\n\nМаксимум {WORD_LIMIT} слов.\nВ вашем сообщении: <b>{{count}}</b> слов.\n\n📝 Отправьте текст покороче.",
        "no_error": "✅ <b>Ошибок не найдено!</b>\n\n📝 Можете отправить следующий текст.",
        "no_english": "🚫 <b>Похоже, текст не на английском.</b>\n\n❕ Пожалуйста, отправляйте текст только на английском!"
    },
    "uz": {
        "start": "🎓 <b>Ingliz tili grammatikasini tekshiruvchi bot</b>\n\n📝 Inglizcha matn yuboring, xatolarni tuzatib beraman.\n\n🌍 Tilni o‘zgartirish: /language\n❓ Yordam: /help\n💡 Fikr bildirish: @pencil_fbot",
        "select": "🌍 <b>Tilni tanlang:</b>",
        "set": "<b>Til tanlandi: 🇺🇿O‘zbekcha</b>\n\n📝 Endi menga inglizcha matn yuborishingiz mumkin!",
        "checking": "⏳ tekshirilmoqda…",
        "word_limit": f"⚠️ <b>Matnda so‘zlar chegarasi oshib ketdi!</b>\n\nMaksimal {WORD_LIMIT} ta so‘z.\nSiz yuborgan matnda: <b>{{count}}</b> ta so‘z bor.\n\n📝 Iltimos, qisqaroq matn yuboring.",
        "no_error": "✅ <b>Xato topilmadi!</b>\n\n📝 Yana matn yuborishingiz mumkin!",
        "no_english": "🚫 <b>Menimcha matn ingliz tilida emas.</b>\n\n❕ Iltimos, faqat inglizcha matn yuboring!"
    }
}

# ---------------- SYSTEM PROMPTS ----------------

SYSTEM_PROMPTS = {
    "en": """You are an English grammar checker. Use Telegram HTML formatting.

TASK:
• Fix important grammar mistakes   
• Ignore commas, capitalization, spacing  
• Keep meaning the same  
• If text is nonsense or not English → reply: NOT_IN_ENGLISH  

FORMAT:
✏️ <b>Corrected Text:</b>

[corrected]


❗<b>Mistakes:</b>

➤ "[wrong]" → "[correct]" — [reason]

If no important mistakes → reply: NO_ERRORS_FOUND
""",

    "ru": """You are an English grammar checker. Explain in Russian. Use Telegram HTML formatting.

TASK:
• Исправлять только серьёзные грамматические ошибки  
• Игнорировать мелкие детали  
• Смысл не менять  
• Если текст не английский → ответ: NOT_IN_ENGLISH  

ФОРМАТ:
✏️ <b>Исправленный Текст:</b>

[corrected]


❗<b>Ошибки:</b>

➤ "[wrong]" → "[correct]" — [причина]

Если ошибок нет → ответ: NO_ERRORS_FOUND
""",

    "uz": """You are an English grammar checker. Explain in Uzbek. Use Telegram HTML formatting.

TASK:
• Faqat muhim grammatik xatolarni tuzating  
• Kichik xatolarni e'tiborga olmang  
• Ma'noni o'zgartirmang  
• Inglizcha bo'lmasa → NOT_IN_ENGLISH  

FORMAT:
✏️ <b>To‘g‘irlangan Matn:</b>

[corrected]


❗<b>Xatolar:</b>

➤ "[wrong]" → "[correct]" — [sabab]

Agar xato bo‘lmasa → NO_ERRORS_FOUND
"""
}

# ---------------- COMMANDS ----------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("language", "en")
    await update.message.reply_text(LANGUAGES[lang]["start"], parse_mode="HTML")


async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇺🇿 O'zbek", callback_data="lang_uz")],
    ]
    lang = context.user_data.get("language", "en")
    await update.message.reply_text(
        LANGUAGES[lang]["select"],
        reply_markup=InlineKeyboardMarkup(keyboard),
        parse_mode="HTML",
    )


async def language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    lang = query.data.replace("lang_", "")
    context.user_data["language"] = lang
    await query.edit_message_text(LANGUAGES[lang]["set"], parse_mode="HTML")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("language", "en")
    text = {
        "en": f"📚 <b>Help</b>\n\n📝 Send an English text (max {WORD_LIMIT} words)\n🌍 Change language: /language",
        "ru": f"📚 <b>Помощь</b>\n\n📝 Отправьте текст на английском (макс {WORD_LIMIT} слов)\n🌍 Сменить язык: /language",
        "uz": f"📚 <b>Yordam</b>\n\n📝 Shunchaki inglizcha matn yuboring (maks {WORD_LIMIT} so'z)\n🌍 Tilni o‘zgartirish: /language",
    }[lang]
    await update.message.reply_text(text, parse_mode="HTML")


# ---------------- MAIN CHECKER ----------------

async def check_grammar(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lang = context.user_data.get("language", "en")
    text = update.message.text

    # 1️⃣ If already processing → block
    if context.user_data.get("is_processing", False):
        await update.message.reply_text(LANGUAGES[lang]["wait"])
        return

    context.user_data["is_processing"] = True

    # 2️⃣ Word limit
    word_count = len(text.split())
    if word_count > WORD_LIMIT:
        context.user_data["is_processing"] = False
        await update.message.reply_text(
            LANGUAGES[lang]["word_limit"].format(count=word_count),
            parse_mode="HTML",
        )
        return

    # 3️⃣ Send checking message
    msg = await update.message.reply_text(LANGUAGES[lang]["checking"])

    try:
        # 4️⃣ Timeout for OpenAI
        try:
            full_text = await asyncio.wait_for(
                run_grammar_correction(text, lang),
                timeout=5,
            )
        except asyncio.TimeoutError:
            await msg.edit_text(LANGUAGES[lang]["no_english"], parse_mode="HTML")
            return

        # 5️⃣ Model responses
        if "NO_ERRORS_FOUND" in full_text:
            await msg.edit_text(LANGUAGES[lang]["no_error"], parse_mode="HTML")
        elif "NOT_IN_ENGLISH" in full_text:
            await msg.edit_text(LANGUAGES[lang]["no_english"], parse_mode="HTML")
        else:
            await msg.edit_text(full_text, parse_mode="HTML")

    except Exception as e:
        logger.error(f"Grammar error: {e}")
        await msg.edit_text("❌ Error: " + str(e))
    finally:
        context.user_data["is_processing"] = False


# ---------------- RUN BOT ----------------

def main():
    try:
        persistence = PicklePersistence("bot_data.pickle")

        app = Application.builder().token(TELEGRAM_BOT_TOKEN).persistence(persistence).build()

        app.add_handler(CommandHandler("start", start_command))
        app.add_handler(CommandHandler("help", help_command))
        app.add_handler(CommandHandler("language", language_command))
        app.add_handler(CallbackQueryHandler(language_callback, pattern="^lang_"))
        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, check_grammar))

        logger.info("🤖 Bot starting...")
        app.run_polling()
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
        raise


if __name__ == "__main__":
    main()
