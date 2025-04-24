from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters
)

from sqlalchemy.orm import Session
from dating_bot.database.models import Profile, User, Like
from dating_bot.database import crud
from dating_bot.database.session import SessionLocal

AGE, GENDER, CITY, CONTACT = range(4)

# Меню
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("/start"), KeyboardButton("/anketa")],
        [KeyboardButton("/edit"), KeyboardButton("/search")],
        [KeyboardButton("/myprofile"), KeyboardButton("/liked")]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text("Выбери действие 👇", reply_markup=markup)

# Создание анкеты
async def profile_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    user = crud.get_user_by_telegram_id(db, update.effective_user.id)
    existing = db.query(Profile).filter(Profile.user_id == user.id).first()
    db.close()

    if existing:
        await update.message.reply_text("У тебя уже есть анкета. Хочешь изменить — напиши /edit 😉")
        return ConversationHandler.END

    await update.message.reply_text("Сколько тебе лет?")
    return AGE

# Редактирование анкеты
async def edit_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    user = crud.get_user_by_telegram_id(db, update.effective_user.id)
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    db.close()

    if not profile:
        await update.message.reply_text("У тебя ещё нет анкеты. Напиши /anketa, чтобы создать её.")
        return ConversationHandler.END

    context.user_data["edit"] = True
    await update.message.reply_text("Обновим анкету!\nСколько тебе лет?")
    return AGE

async def profile_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["age"] = int(update.message.text)
    reply_markup = ReplyKeyboardMarkup(
        [[KeyboardButton("Мужской"), KeyboardButton("Женский")]],
        resize_keyboard=True,
        one_time_keyboard=True
    )
    await update.message.reply_text("Укажи пол:", reply_markup=reply_markup)
    return GENDER

async def profile_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["gender"] = update.message.text
    await update.message.reply_text("Из какого ты города?")
    return CITY

async def profile_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["city"] = update.message.text
    await update.message.reply_text("Как с тобой связаться? Напиши свой Telegram @username")
    return CONTACT

async def profile_contact(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["contact"] = update.message.text
    user_id = update.effective_user.id

    db = SessionLocal()
    user = crud.get_user_by_telegram_id(db, user_id)

    if context.user_data.get("edit"):
        db.query(Like).filter(
            (Like.from_user_id == user.id) | (Like.to_user_id == user.id)
        ).delete()
        db.query(Profile).filter(Profile.user_id == user.id).delete()
        db.commit()

    profile = Profile(
        user_id=user.id,
        age=context.user_data["age"],
        gender=context.user_data["gender"],
        city=context.user_data["city"],
        contact=context.user_data["contact"]
    )
    db.add(profile)
    db.commit()

    message = "Анкета обновлена! 🔁" if context.user_data.get("edit") else "Анкета успешно сохранена! 🔥"
    await update.message.reply_text(message, reply_markup=ReplyKeyboardRemove())

    keyboard = [
        [KeyboardButton("/start"), KeyboardButton("/anketa")],
        [KeyboardButton("/edit"), KeyboardButton("/search")],
        [KeyboardButton("/myprofile"), KeyboardButton("/liked")]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=False)
    await update.message.reply_text("Выбери действие 👇", reply_markup=markup)

    db.close()
    return ConversationHandler.END

# Обработка кнопок (лайк/пропуск)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    await query.edit_message_text("Выбор сохранён!")

# Просмотр своей анкеты
async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    user = crud.get_user_by_telegram_id(db, update.effective_user.id)
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    db.close()

    if not profile:
        await update.message.reply_text("У тебя пока нет анкеты. Напиши /anketa, чтобы создать её.")
        return

    text = (
        f"Твоя анкета:\n"
        f"Возраст: {profile.age}\n"
        f"Пол: {profile.gender}\n"
        f"Город: {profile.city}\n"
        f"Контакт: {profile.contact}"
    )
    await update.message.reply_text(text)

# Просмотр понравившихся анкет
async def liked_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    user = crud.get_user_by_telegram_id(db, update.effective_user.id)

    likes = db.query(Like).filter(
        Like.from_user_id == user.id,
        Like.is_like == "like"
    ).all()

    if not likes:
        await update.message.reply_text("У тебя пока нет понравившихся анкет.")
        db.close()
        return

    response = "❤️ Понравившиеся анкеты:\n\n"
    shown_ids = set()
    for like in likes:
        if like.to_user_id in shown_ids:
            continue
        shown_ids.add(like.to_user_id)

        profile = db.query(Profile).filter(Profile.user_id == like.to_user_id).first()
        target_user = db.query(User).filter(User.id == like.to_user_id).first()
        if profile and target_user:
            response += (
                f"👤 {target_user.first_name or target_user.username or 'Без имени'}\n"
                f"Возраст: {profile.age}, Пол: {profile.gender}, Город: {profile.city}\n"
                f"Контакт: {profile.contact}\n\n"
            )

    db.close()
    await update.message.reply_text(response)

# Поиск анкет
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    current_user = crud.get_user_by_telegram_id(db, update.effective_user.id)

    profile = (
        db.query(Profile)
        .filter(Profile.user_id != current_user.id)
        .first()
    )

    if not profile:
        await update.message.reply_text("Нет доступных анкет 😞 Попробуй позже!")
        db.close()
        return

    user = db.query(User).filter(User.id == profile.user_id).first()
    text = (
        f"👤 {user.first_name or user.username or 'Без имени'}\n"
        f"Возраст: {profile.age}\n"
        f"Пол: {profile.gender}\n"
        f"Город: {profile.city}\n"
        f"Контакт: {profile.contact}"
    )
    keyboard = [
        [
            InlineKeyboardButton("❤️ Лайк", callback_data=f"like:{profile.user_id}"),
            InlineKeyboardButton("❌ Пропустить", callback_data=f"skip:{profile.user_id}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text(text, reply_markup=reply_markup)
    db.close()