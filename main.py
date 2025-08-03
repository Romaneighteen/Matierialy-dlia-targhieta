import os
import json
import asyncio
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, InputFile
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler,
    filters, ContextTypes, CallbackQueryHandler
)

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

# Сохраняем пользователя
def save_user(user_id, username):
    record = {
        "user_id": user_id,
        "username": username,
        "timestamp": datetime.now().isoformat()
    }
    try:
        with open(USER_DATA_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[Ошибка] Не удалось сохранить пользователя: {e}")

# Сохраняем отзыв
def save_review(user_id, username, text):
    record = {
        "user_id": user_id,
        "username": username,
        "text": text,
        "timestamp": datetime.now().isoformat()
    }
    try:
        with open(REVIEW_DATA_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"[Ошибка] Не удалось сохранить отзыв: {e}")

# Проверка подписки
async def is_subscribed(bot, user_id):
    try:
        member = await bot.get_chat_member(chat_id=CHANNEL_USERNAME, user_id=user_id)
        return member.status in ["member", "administrator", "creator"]
    except:
        return False

# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [[InlineKeyboardButton("📩 Оставить отзыв", callback_data="leave_review")]]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = (
        "Привет!\n\n"
        "Я очень рад, что ты решил(а) воспользоваться моими материалами. Они помогут тебе прокачать таргет.\n\n"
        "Чтобы получить материалы, нужно:\n"
        "1. Оставить честный отзыв (25+ символов)\n"
        "2. Подписаться на канал: {channel}\n"
        "3. Нажать \"Проверить подписку\" после отзыва"
    ).format(channel=CHANNEL_USERNAME)

    await update.message.reply_text(text, reply_markup=reply_markup)

# Кнопки отзыва и подписки
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
                waiting_for_check[user_id] = msg.message_id
                asyncio.create_task(delayed_subscription_check(context.bot, user_id, msg.chat.id, msg.message_id))
            else:
                await query.message.reply_text("Пожалуйста, сначала оставь отзыв.")
        else:
            await query.message.reply_text("Похоже, ты не подписан на канал. Подпишись и попробуй снова.")

# Проверка отписки через 5 минут
async def delayed_subscription_check(bot, user_id, chat_id, message_id):
    await asyncio.sleep(300)
    if not await is_subscribed(bot, user_id):
        try:
            await bot.delete_message(chat_id=chat_id, message_id=message_id)
            await bot.send_message(chat_id=chat_id, text="Материалы были удалены, так как вы отписались от канала.")
        except:
            pass

# Обработка текстов — отзывы
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
    await context.bot.send_message(chat_id=ADMIN_ID, text=f"👤 Отзыв от @{username} (ID: {user_id}):\n{text}")

    keyboard = [[InlineKeyboardButton("✅ Проверить подписку", callback_data="check_subscription")]]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Спасибо за отзыв! Теперь подпишись на канал и нажми кнопку ниже, чтобы получить материалы.", reply_markup=reply_markup)

# ================== АДМИН-КОМАНДЫ ==================

async def users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()[-10:]
            users = [json.loads(line) for line in lines]
        msg = "👥 Последние пользователи:\n" + "\n".join([f"@{u['username']} ({u['user_id']})" for u in users])
        await update.message.reply_text(msg)
    except Exception as e:
        await update.message.reply_text(f"Ошибка чтения users.json: {e}")

async def reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        with open(REVIEW_DATA_FILE, "r", encoding="utf-8") as f:
            lines = f.readlines()[-10:]
            reviews = [json.loads(line) for line in lines]
        msg = "📝 Последние отзывы:\n\n" + "\n\n".join([f"@{r['username']} ({r['user_id']}):\n{r['text']}" for r in reviews])
        await update.message.reply_text(msg[:4096])
    except Exception as e:
        await update.message.reply_text(f"Ошибка чтения reviews.json: {e}")

async def export_reviews(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        await update.message.reply_document(InputFile(REVIEW_DATA_FILE))
    except Exception as e:
        await update.message.reply_text(f"Не удалось отправить файл: {e}")

async def export_users(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        await update.message.reply_document(InputFile(USER_DATA_FILE))
    except Exception as e:
        await update.message.reply_text(f"Не удалось отправить файл: {e}")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    if not context.args:
        await update.message.reply_text("Укажи текст: /broadcast Твой бонус!")
        return
    text = " ".join(context.args)
    count = 0
    try:
        with open(USER_DATA_FILE, "r", encoding="utf-8") as f:
            for line in f:
                user = json.loads(line)
                try:
                    await context.bot.send_message(chat_id=user["user_id"], text=text)
                    count += 1
                    await asyncio.sleep(0.1)
                except:
                    continue
        await update.message.reply_text(f"✅ Рассылка завершена. Отправлено: {count}")
    except Exception as e:
        await update.message.reply_text(f"Ошибка рассылки: {e}")

# Тестовая запись в файл
async def test_write(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_user.id != ADMIN_ID:
        return
    try:
        test_data = {"test": True, "timestamp": datetime.now().isoformat()}
        with open("test_write.json", "w", encoding="utf-8") as f:
            json.dump(test_data, f, ensure_ascii=False)
        await update.message.reply_text("✅ Тестовая запись в файл прошла успешно.")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка записи: {e}")

# ========== Запуск ==========

if __name__ == "__main__":
    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("users", users))
    app.add_handler(CommandHandler("reviews", reviews))
    app.add_handler(CommandHandler("export_reviews", export_reviews))
    app.add_handler(CommandHandler("export_users", export_users))
    app.add_handler(CommandHandler("broadcast", broadcast))
    app.add_handler(CommandHandler("test_write", test_write))
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_review))

    print("Бот запущен...")
    app.run_polling()
