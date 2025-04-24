import os
from dotenv import load_dotenv
from telegram import Update, KeyboardButton, ReplyKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CallbackQueryHandler,
    filters
)

from dating_bot.bot.handlers import (
    show_menu,
    profile_start,
    edit_profile,
    profile_age,
    profile_gender,
    profile_city,
    profile_nickname,
    button_handler,
    search,
    my_profile,
    liked_profiles,
    AGE,
    GENDER,
    CITY,
    NICKNAME
)

from dating_bot.database.session import SessionLocal
from dating_bot.database import crud

# Загрузка переменных среды
load_dotenv()
TOKEN = os.getenv("TELEGRAM_TOKEN")


# Команда /start
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    telegram_id = update.effective_user.id
    username = update.effective_user.username
    first_name = update.effective_user.first_name

    db = SessionLocal()
    user = crud.get_user_by_telegram_id(db, telegram_id)

    if user:
        await update.message.reply_text(f"С возвращением, {first_name}! 💫")
    else:
        crud.create_user(db, telegram_id, username, first_name)
        await update.message.reply_text(f"Привет, {first_name}! 👋\nТы зарегистрирован в Fountains Of Vanya!")

    db.close()

    # Показываем меню
    await show_menu(update, context)


def main():
    app = Application.builder().token(TOKEN).build()

    # Основные команды
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", show_menu))
    app.add_handler(CommandHandler("search", search))
    app.add_handler(CommandHandler("myprofile", my_profile))
    app.add_handler(CommandHandler("liked", liked_profiles))
    app.add_handler(CallbackQueryHandler(button_handler))

    # Обработка анкеты и редактирования
    conv_handler = ConversationHandler(
        entry_points=[
            CommandHandler("anketa", profile_start),
            CommandHandler("edit", edit_profile)
        ],
        states={
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_age)],
            GENDER: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_gender)],
            CITY: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_city)],
            NICKNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, profile_nickname)],
        },
        fallbacks=[]
    )
    app.add_handler(conv_handler)

    app.run_polling()


if __name__ == "__main__":
    main()
