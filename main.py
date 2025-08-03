import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, MessageHandler, filters, ContextTypes, CallbackQueryHandler

# Переменные окружения
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
BONUS_FILE_URL = os.getenv("BONUS_FILE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

# Словарь для хранения отзывов
user_reviews = {}

# Сохраняем пользователя в файл
def save_user(user_id, username):
    user_data = {
        "user_id": user_id,
        "username": username,
        "timestamp": datetime.now().isoformat()
    }
    with open("users.json", "a") as f:
        f.write(json.dumps(user_data) + "\n")

# Проверка подписки на канал
async def is_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# Обработка команды /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("\ud83d\udcdd Оставить отзыв", callback_data="review")],
        [InlineKeyboardButton("\ud83c\udf81 Получить бонус", callback_data="bonus")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Что ты хочешь сделать?", reply_markup=reply_markup)

# Обработка нажатий кнопок
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id
    username = query.from_user.username or "без username"

    if query.data == "review":
        await query.message.reply_text("Пожалуйста, отправь отзыв. Не менее 30 символов.")
    elif query.data == "bonus":
        if not await is_subscribed(context.bot, user_id):
            await query.message.reply_text("Пожалуйста, подпишись на канал @tg_protarget, чтобы получить бонус.")
            return
        if user_id in user_reviews:
            await query.message.reply_text("Ты уже получил бонус. Спасибо!")
            return
        await query.message.reply_text(f"Вот твой бонус: {BONUS_FILE_URL}")
        save_user(user_id, username)

# Обработка текстовых сообщений
async def handle_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "без username"
    text = update.message.text.strip()

    if len(text) < 30:
        await update.message.reply_text("Пожалуйста, напиши отзыв длиной не менее 30 символов.")
        return

    if user_id in user_reviews:
        await update.message.reply_text("Ты уже отправлял отзыв. Спасибо!")
        return

    user_reviews[user_id] = text
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"\ud83d\udc64 Новый отзыв от {user_id} (@{username}):\n{text}")
    await update.message.reply_text("Спасибо за отзыв! Теперь ты можешь получить бонус.\nНажми \"Получить бонус\" снова.")
    save_user(user_id, username)

# Команда /users — список последних пользователей
async def list_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    try:
        with open("users.json", "r") as f:
            lines = f.readlines()

        if not lines:
            await update.message.reply_text("Пока нет пользователей.")
            return

        msg = f"\ud83d\udc65 Всего пользователей: {len(lines)}\n\n"
        for i, line in enumerate(lines[-10:], 1):
            user = json.loads(line)
            msg += f"{i}. @{user['username']} | ID: {user['user_id']}\n"

        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text("Ошибка чтения списка пользователей.")

# Команда /reviews — последние отзывы
async def list_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return

    if not user_reviews:
        await update.message.reply_text("Пока нет отзывов.")
        return

    msg = "\ud83d\udccb Последние отзывы:\n\n"
    for user_id, review in list(user_reviews.items())[-5:]:
        msg += f"\ud83d\udcdd {user_id}:\n{review}\n\n"

    await update.message.reply_text(msg)

# Запуск бота
if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_review))
    app.add_handler(CommandHandler("users", list_users))
    app.add_handler(CommandHandler("reviews", list_reviews))

    print("Бот запущен...")
    app.run_polling()
