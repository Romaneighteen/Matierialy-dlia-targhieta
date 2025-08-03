import os
import json
from datetime import datetime, timedelta
import asyncio
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
BONUS_FILE_URL = os.getenv("BONUS_FILE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Файлы хранения
USER_DATA_FILE = "users.json"
REVIEW_DATA_FILE = "reviews.json"

user_reviews = {}
waiting_for_review = set()
waiting_for_check = {}
sent_bonus = set()

# Сохранение пользователя
def save_user(user_id, username):
    record = {
        "user_id": user_id,
        "username": username,
        "timestamp": datetime.now().isoformat()
    }
    with open(USER_DATA_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")

# Сохранение отзыва в файл
def save_review(user_id, username, text):
    record = {
        "user_id": user_id,
        "username": username,
        "text": text,
        "timestamp": datetime.now().isoformat()
    }
    with open(REVIEW_DATA_FILE, "a") as f:
        f.write(json.dumps(record) + "\n")

# Проверка подписки
async def is_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# Приветственное сообщение
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("\ud83d\udcdd Оставить отзыв", callback_data="leave_review")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "Привет! \n\n"
        "Я очень рад, что ты решил(а) воспользоваться моими материалами. "
        "Они помогут тебе прокачать таргет. \n\n"
        "Чтобы получить материалы, нужно:\n"
        "1. Оставить честный отзыв (25+ символов)\n"
        "2. Подписаться на мой канал: {channel}\n"
        "3. Нажать кнопку \"Проверить подписку\" после отзыва"
    ).format(channel=CHANNEL_USERNAME)

    await update.message.reply_text(text, reply_markup=reply_markup)

# Обработка кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    username = query.from_user.username or "без username"
    await query.answer()

    if query.data == "leave_review":
        waiting_for_review.add(user_id)
        await query.message.reply_text("Пожалуйста, напиши отзыв. Не менее 25 символов.")

    elif query.data == "check_subscription":
        if await is_subscribed(context.bot, user_id):
            if user_id in user_reviews and user_id not in sent_bonus:
                msg = await query.message.reply_text(f"Спасибо! Вот ссылка на материалы: {BONUS_FILE_URL}")
                save_user(user_id, username)
                sent_bonus.add(user_id)

                # Планируем автопроверку через 5 минут
                waiting_for_check[user_id] = msg.message_id
                asyncio.create_task(delayed_subscription_check(context.bot, user_id, msg.chat.id, msg.message_id))
            else:
                await query.message.reply_text("Пожалуйста, сначала оставь отзыв.")
        else:
            await query.message.reply_text("Похоже, ты не подписан на канал. Подпишись и попробуй снова.")

# Проверка подписки спустя время
async def delayed_subscription_check(bot, user_id, chat_id, message_id):
    await asyncio.sleep(300)  # 5 минут
    if not await is_subscribed(bot, user_id):
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            await bot.send_message(chat_id=chat_id, text="Материалы были удалены, так как вы отписались от канала.")
        except:
            pass

# Обработка текстовых сообщений (отзывы)
async def handle_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "без username"
    text = update.message.text.strip()

    if user_id not in waiting_for_review:
        return

    if len(text) < 25:
        await update.message.reply_text("Отзыв слишком короткий. Напиши, пожалуйста, более развернуто (от 25 символов).")
        return

    user_reviews[user_id] = text
    waiting_for_review.remove(user_id)
    save_review(user_id, username, text)
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"\ud83d\udc64 Отзыв от @{username} (ID: {user_id}):\n{text}")

    keyboard = [[InlineKeyboardButton("\u2705 Проверить подписку", callback_data="check_subscription")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Спасибо за отзыв! Теперь подпишись на канал и нажми кнопку ниже, чтобы получить материалы.",
        reply_markup=reply_markup
    )

# Запуск бота
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_review))

    print("Бот запущен...")
    app.run_polling()
