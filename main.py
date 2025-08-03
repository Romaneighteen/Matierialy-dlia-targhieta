import os
import asyncio
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHANNEL_USERNAME = os.getenv("CHANNEL_USERNAME")
BONUS_FILE_URL = os.getenv("BONUS_FILE_URL")
ADMIN_ID = int(os.getenv("ADMIN_ID"))

user_reviews = {}
waiting_for_review = set()
waiting_for_check = {}
sent_bonus = set()

async def is_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📩 Оставить отзыв", callback_data="leave_review")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "Привет!\n\n"
        "Я очень рад, что ты решил(а) воспользоваться моими материалами. Они помогут тебе прокачать свои навыки.\n\n"
        "Чтобы получить материалы, нужно:\n"
        "1. Оставить честный отзыв (25+ символов)\n"
        "2. Подписаться на канал: {channel}\n"
        "3. Нажать \"Проверить подписку\" после отзыва"
    ).format(channel=CHANNEL_USERNAME)

    await update.message.reply_text(text, reply_markup=reply_markup)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    user_id = query.from_user.id
    await query.answer()

    if query.data == "leave_review":
        waiting_for_review.add(user_id)
        await query.message.reply_text("Пожалуйста, напиши отзыв. Не менее 25 символов.")

    elif query.data == "check_subscription":
        if await is_subscribed(context.bot, user_id):
            if user_id in user_reviews and user_id not in sent_bonus:
                msg = await query.message.reply_text(f"Спасибо! Вот ссылка на материалы: {BONUS_FILE_URL}")
                sent_bonus.add(user_id)
                waiting_for_check[user_id] = msg.message_id
                asyncio.create_task(delayed_subscription_check(context.bot, user_id, msg.chat.id, msg.message_id))
            else:
                await query.message.reply_text("Пожалуйста, сначала оставь отзыв.")
        else:
            await query.message.reply_text("Похоже, ты не подписан на канал. Подпишись и попробуй снова.")

async def delayed_subscription_check(bot, user_id, chat_id, message_id):
    await asyncio.sleep(300)
    if not await is_subscribed(bot, user_id):
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            await bot.send_message(chat_id=chat_id, text="Материалы были удалены, так как вы отписались от канала.")
        except:
            pass

async def handle_review(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()

    if user_id not in waiting_for_review:
        return

    if len(text) < 25:
        await update.message.reply_text("Отзыв слишком короткий. Напиши, пожалуйста, более развернуто (от 25 символов).")
        return

    user_reviews[user_id] = text
    waiting_for_review.remove(user_id)

    keyboard = [[InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Спасибо за отзыв! Теперь подпишись на канал и нажми кнопку ниже, чтобы получить материалы.", reply_markup=reply_markup)

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_review))

    print("Бот запущен...")
    app.run_polling()
