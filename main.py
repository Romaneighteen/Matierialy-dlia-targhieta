import os
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

ASK_REVIEW = 1

# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

# --- Оставить отзыв ---
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "leave_review":
        await query.message.reply_text("Напиши, пожалуйста, отзыв одним сообщением (минимум 30 символов):")
        return ASK_REVIEW

    elif query.data == "get_bonus":
        user_id = query.from_user.id

        if user_id not in user_reviews:
            await query.message.reply_text("❗ Сначала оставь отзыв, затем сможешь получить бонус.")
            return ConversationHandler.END

        chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        if chat_member.status not in ['member', 'administrator', 'creator']:
            await query.message.reply_text("❗ Пожалуйста, подпишись на канал: https://t.me/tg_protarget")
            return ConversationHandler.END

        # Отправляем ссылку
        await query.message.reply_text(f"📎 Вот ваша ссылка на бонусные материалы:\n{BONUS_FILE_URL}")
        users_received_bonus.add(user_id)
        return ConversationHandler.END

# --- Обработка отзыва ---
async def handle_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    review_text = update.message.text.strip()

    if len(review_text) < 30:
        await update.message.reply_text("Пожалуйста, напиши более развёрнутый отзыв (от 30 символов).")
        return ASK_REVIEW

    user_reviews[user_id] = review_text

    # Переслать отзыв админу
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"📝 Новый отзыв от @{update.effective_user.username}:\n\n{review_text}")

    await update.message.reply_text("Спасибо за отзыв! Теперь ты можешь получить бонусные материалы 👇")

    keyboard = [[InlineKeyboardButton("🎁 Получить бонус", callback_data="get_bonus")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Нажми кнопку ниже, чтобы проверить подписку и получить бонус:", reply_markup=reply_markup)

    return ConversationHandler.END

# --- Основной блок ---
def main():
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler)],
        states={ASK_REVIEW: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_review)]},
        fallbacks=[],
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))  # Обработка инлайн-кнопок

    print("Бот запущен...")
    app.run_polling()

if __name__ == "__main__":
    main()
