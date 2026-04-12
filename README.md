# ✏️ English Grammar Checker Bot

A Telegram bot that checks English grammar using Claude AI.

## What it does
- Checks grammar mistakes in English text
- Shows corrected text with explanation of each mistake
- Ignores punctuation, focuses on grammar only

## How to run

1. **Install dependencies**
   ```
   pip install -r requirements.txt
   ```

2. **Add your keys in `config.py`**
   ```python
   ANTHROPIC_API_KEY = "your-key"
   TELEGRAM_BOT_TOKEN = "your-token"
   ```

3. **Run**
   ```
   python bot.py
   ```

## Commands
| Command | Description |
|--------|-------------|
| `/start` | Start the bot |

## Limits
- Max **100 words** per message
- English text only

## Stack
- Python 3
- [python-telegram-bot](https://github.com/python-telegram-bot/python-telegram-bot)
- [Anthropic Claude API](https://www.anthropic.com)