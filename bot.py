import json
import asyncio
from datetime import datetime, timedelta

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
)

from apscheduler.schedulers.background import BackgroundScheduler
import pytz

# 🔑 ВСТАВЬ СЮДА ТОКЕН ОТ BotFather
BOT_TOKEN = "8440232593:AAFR3Lq2Ox2oPlSnMFqZ_6hm0vQpiFBWW90"

# 🔢 ВСТАВЬ СЮДА СВОЙ chat_id, который получишь через /id
YOUR_CHAT_ID = 123456789

WORDS_FILE = "words.json"

# -------------------------------
# ХРАНЕНИЕ И ЗАГРУЗКА СЛОВ
# -------------------------------

def load_words():
    try:
        with open(WORDS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return []

def save_words(words):
    with open(WORDS_FILE, "w") as f:
        json.dump(words, f, ensure_ascii=False, indent=2)

# -------------------------------
# КОМАНДЫ
# -------------------------------

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Привет! Отправь слово в формате: слово - перевод")

async def show_id(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(f"Твой chat_id: {update.message.chat_id}")

async def add_word(update: Update, context: ContextTypes.DEFAULT_TYPE):
    text = update.message.text
    if " - " not in text:
        await update.message.reply_text("Используй формат: слово - перевод")
        return

    word, translation = text.split(" - ", 1)
    words = load_words()
    words.append({
        "word": word.strip(),
        "translation": translation.strip(),
        "next_review": datetime.now().isoformat()
    })
    save_words(words)
    await update.message.reply_text(f"Слово '{word.strip()}' добавлено!")

# -------------------------------
# ПОВТОРЕНИЕ
# -------------------------------

user_progress = {}

async def send_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id
    words = load_words()

    if chat_id not in user_progress:
        user_progress[chat_id] = {
            "current_index": 0
        }

    index = user_progress[chat_id]["current_index"]

    if index >= len(words):
        await update.message.reply_text("Все слова пройдены!")
        return

    word = words[index]
    user_progress[chat_id]["awaiting_answer"] = word
    await update.message.reply_text(f"Переведи: {word['word']}")

async def handle_answer(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chat_id = update.message.chat_id

    if chat_id not in user_progress or "awaiting_answer" not in user_progress[chat_id]:
        await add_word(update, context)
        return

    expected = user_progress[chat_id]["awaiting_answer"]["translation"].lower()
    user_answer = update.message.text.strip().lower()

    if user_answer == expected:
        await update.message.reply_text("✅ Верно!")
        user_progress[chat_id]["current_index"] += 1
    else:
        await update.message.reply_text(f"❌ Неверно. Правильный ответ: {expected}")

    del user_progress[chat_id]["awaiting_answer"]
    await send_review(update, context)

# -------------------------------
# ЗАДАЧА НА 7 УТРА
# -------------------------------

async def send_review_job(app):
    try:
        dummy_update = type("obj", (object,), {
            "message": type("obj", (object,), {"chat_id": YOUR_CHAT_ID})
        })
        dummy_context = type("obj", (object,), {
            "bot": app.bot,
            "user_data": {}
        })
        await send_review(dummy_update, dummy_context)
    except Exception as e:
        print("Ошибка в автозадаче:", e)

# -------------------------------
# ЗАПУСК
# -------------------------------

def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("id", show_id))
    app.add_handler(CommandHandler("review", send_review))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_answer))

    # Планировщик (7:00 Asia/Almaty)
    scheduler = BackgroundScheduler(timezone=pytz.timezone("Asia/Almaty"))
    scheduler.add_job(send_review_job, "cron", hour=7, minute=0, args=[app])
    scheduler.start()

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
