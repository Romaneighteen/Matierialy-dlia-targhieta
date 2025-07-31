import os
import json
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
BONUS_FILE_URL = os.getenv("BONUS_FILE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

user_reviews = {}
users_received_bonus = set()
USERS_FILE = "users.json"

ASK_REVIEW = 1

# --- Работа с базой пользователей ---
def load_users():
    if os.path.exists(USERS_FILE):
        with open(USERS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return []

def save_users(users):
    with open(USERS_FILE, "w", encoding="utf-8") as f:
        json.dump(users, f, ensure_ascii=False, indent=2)

def add_user(user):
    users = load_users()
    if not any(u["id"] == user.id for u in users):
        users.append({
            "id": user.id,
            "username": user.username,
            "name": user.first_name,
            "status": "new",
            "joined": datetime.now().strftime("%Y-%m-%d")
        })
        save_users(users)

def update_user_status(user_id, new_status):
    users = load_users()
    for u in users:
        if u["id"] == user_id:
            u["status"] = new_status
            break
    save_users(users)

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    add_user(user)

    keyboard = [
        [InlineKeyboardButton("📝 Оставить отзыв", callback_data="leave_review")],
        [InlineKeyboardButton("🎁 Получить бонус", callback_data="get_bonus")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(
        "Привет! Чтобы получить бонусные материалы, оставь отзыв о курсе и подпишись на канал:\n\n"
        "📢 https://t.me/tg_protarget",
        reply_markup=reply_markup
    )

# --- Инлайн-кнопки ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    user_id = query.from_user.id

    if query.data == "leave_review":
        await query.message.reply_text("Напиши, пожалуйста, отзыв одним сообщением (минимум 30 символов):")
        return ASK_REVIEW

    elif query.data == "get_bonus":
        if user_id not in user_reviews:
            await query.message.reply_text("❗ Сначала оставь отзыв, затем сможешь получить бонус.")
            return ConversationHandler.END

        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if chat_member.status not in ['member', 'administrator', 'creator']:
            await query.message.reply_text("❗ Пожалуйста, подпишись на канал: https://t.me/tg_protarget")
            return ConversationHandler.END

        # Отправляем бонус
        await query.message.reply_text(f"📎 Вот ваша ссылка на бонусные материалы:\n{BONUS_FILE_URL}")
        users_received_bonus.add(user_id)
        update_user_status(user_id, "получил_материалы")
        return ConversationHandler.END

# --- Обработка отзыва ---
async def handle_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    user_id = user.id
    review_text = update.message.text.strip()

    if len(review_text) < 30:
        await update.message.reply_text("Пожалуйста, напиши более развёрнутый отзыв (от 30 символов).")
        return ASK_REVIEW

    user_reviews[user_id] = review_text

    await context.bot.send_message(chat_id=ADMIN_ID,
                                   text=f"📝 Новый отзыв от @{user.username}:\n\n{review_text}")

    await update.message.reply_text("Спасибо за отзыв! Теперь ты можешь получить бонусные материалы 👇")

    keyboard = [[InlineKeyboardButton("🎁 Получить бонус", callback_data="get_bonus")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Нажми кнопку ниже, чтобы проверить подписку и получить бонус:",
                                    reply_markup=reply_markup)
    return ConversationHandler.END

# --- Рассылка (только для администратора) ---
async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    msg = " ".join(context.args)
    if not msg:
        await update.message.reply_text("Напиши текст после команды: /broadcast ваш текст")
        return

    users = load_users()
    count = 0
    for user in users:
        try:
            await context.bot.send_message(chat_id=user["id"], text=msg)
            count += 1
        except Exception as e:
            print(f"❌ Ошибка при отправке {user['id']}: {e}")
    await update.message.reply_text(f"✅ Рассылка отправлена {count} пользователям.")

# --- Основной блок ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={ASK_REVIEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_review)]},
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))  # обработка инлайн-кнопок

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
