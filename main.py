import os
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    ConversationHandler,
    filters,
)
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = "@tg_protarget"
YANDEX_DISK_LINK = os.getenv("YANDEX_DISK_LINK")  # Ссылка на материалы
ADMIN_ID = int(os.getenv("ADMIN_ID"))  # Твой Telegram ID

user_reviews = {}
users_received_link = set()


# --- /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "👋 Привет!\n\nЧтобы получить дополнительные материалы по рекламе, нужно:\n\n"
        "1️⃣ Оставить отзыв о курсе\n"
        "2️⃣ Подписаться на канал https://t.me/tg_protarget\n"
        "3️⃣ Нажать кнопку 🔁 Проверить подписку\n\n"
        "📝 Пожалуйста, напиши свой отзыв в одном сообщении:")
    return 1


# --- Отзыв ---
async def handle_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    username = update.effective_user.username or "без username"
    review_text = update.message.text

    user_reviews[user_id] = review_text

    # Отправить админу
    await context.bot.send_message(
        chat_id=ADMIN_ID,
        text=f"✉️ Новый отзыв от @{username} (ID: {user_id}):\n\n{review_text}"
    )

    # Попросить подписаться и нажать кнопку
    keyboard = [["🔁 Проверить подписку"]]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

    await update.message.reply_text(
        f"❤️ Спасибо за отзыв!\n\nТеперь подпишись на канал {CHANNEL_USERNAME}, если ещё не подписан.\n"
        f"Когда подпишешься — нажми '🔁 Проверить подписку'.",
        reply_markup=reply_markup)

    return ConversationHandler.END


# --- Проверка подписки и выдача ссылки ---
async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id

    chat_member = await context.bot.get_chat_member(chat_id=CHANNEL_USERNAME,
                                                    user_id=user_id)
    if chat_member.status in ['member', 'administrator', 'creator']:
        if user_id in users_received_link:
            await update.message.reply_text(
                "✅ Вы уже получали ссылку на материалы.")
        else:
            await update.message.reply_text(
                f"📎 Вот ваша ссылка на бонусные материалы:\n{YANDEX_DISK_LINK}"
            )
            users_received_link.add(user_id)
    else:
        await update.message.reply_text(
            f"❌ Вы не подписаны на канал.\nПодпишитесь на {CHANNEL_USERNAME} и нажмите ещё раз '🔁 Проверить подписку'."
        )


# --- Обработка кнопки "🔁 Проверить подписку" ---
async def handle_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.text == "🔁 Проверить подписку":
        await check(update, context)


if __name__ == '__main__':
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start)],
        states={
            1:
            [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_review)]
        },
        fallbacks=[],
    )

    app.add_handler(conv_handler)
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, handle_buttons))

    print("Бот запущен...")
    app.run_polling()
