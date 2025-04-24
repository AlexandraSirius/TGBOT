from telegram import (
    Update,
    ReplyKeyboardMarkup,
    ReplyKeyboardRemove,
    KeyboardButton,
    InlineKeyboardButton,
    InlineKeyboardMarkup,
)
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    CommandHandler,
    CallbackQueryHandler,
    filters,
)
from sqlalchemy.orm import Session
from dating_bot.database.models import Profile, User, Like
from dating_bot.database import crud
from dating_bot.database.session import SessionLocal

AGE, GENDER, CITY, NICKNAME = range(4)

# Главное меню
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("/start"), KeyboardButton("/anketa")],
        [KeyboardButton("/edit"), KeyboardButton("/search")],
        [KeyboardButton("/myprofile"), KeyboardButton("/liked")],
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
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
    markup = ReplyKeyboardMarkup(
        [[KeyboardButton("Мужской"), KeyboardButton("Женский")]],
        resize_keyboard=True, one_time_keyboard=True
    )
    await update.message.reply_text("Укажи пол:", reply_markup=markup)
    return GENDER

async def profile_gender(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["gender"] = update.message.text
    await update.message.reply_text("Из какого ты города?")
    return CITY

async def profile_city(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["city"] = update.message.text
    await update.message.reply_text("Напиши свой Telegram-ник (например, @username):")
    return NICKNAME

async def profile_nickname(update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data["nickname"] = update.message.text
    db = SessionLocal()
    user = crud.get_user_by_telegram_id(db, update.effective_user.id)

    profile = Profile(
        user_id=user.id,
        age=context.user_data["age"],
        gender=context.user_data["gender"],
        city=context.user_data["city"],
        contact=context.user_data["nickname"]
    )

    # Удаление старой анкеты и лайков при редактировании
    if context.user_data.get("edit"):
        db.query(Like).filter((Like.from_user_id == user.id) | (Like.to_user_id == user.id)).delete()
        db.query(Profile).filter(Profile.user_id == user.id).delete()
        db.commit()

    db.add(profile)
    db.commit()
    db.close()

    await update.message.reply_text("Анкета успешно сохранена! 🔥", reply_markup=ReplyKeyboardRemove())
    await show_menu(update, context)
    return ConversationHandler.END

# Команда /search
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    user = crud.get_user_by_telegram_id(db, update.effective_user.id)

    if not user:
        await update.message.reply_text("Вы не зарегистрированы. Напишите /start сначала.")
        db.close()
        return

    my_profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    if not my_profile:
        await update.message.reply_text("Сначала заполни анкету с помощью /anketa 😉")
        db.close()
        return

    profile = db.query(Profile).filter(Profile.user_id != user.id).first()
    if not profile:
        await update.message.reply_text("Нет доступных анкет 😞")
        db.close()
        return

    target = db.query(User).filter(User.id == profile.user_id).first()
    keyboard = [
        [
            InlineKeyboardButton("❤️ Лайк", callback_data=f"like:{profile.user_id}"),
            InlineKeyboardButton("❌ Пропустить", callback_data=f"skip:{profile.user_id}")
        ]
    ]
    markup = InlineKeyboardMarkup(keyboard)
    text = (
        f"Имя: {target.first_name or 'Без имени'}\n"
        f"Ник: {profile.contact}\n"
        f"Возраст: {profile.age}\n"
        f"Пол: {profile.gender}\n"
        f"Город: {profile.city}"
    )
    await update.message.reply_text(text, reply_markup=markup)
    db.close()

# Обработка кнопок лайк / скип
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, target_id = query.data.split(":")
    db = SessionLocal()
    user = crud.get_user_by_telegram_id(db, update.effective_user.id)

    existing = db.query(Like).filter_by(
        from_user_id=user.id, to_user_id=int(target_id)
    ).first()

    if not existing:
        db.add(Like(
            from_user_id=user.id,
            to_user_id=int(target_id),
            is_like=action
        ))
        db.commit()
        msg = "Выбор сохранён!"
    else:
        msg = "Ты уже выбирал эту анкету 😉"

    db.close()
    await query.edit_message_text(msg)

# Моя анкета
async def my_profile(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    user = crud.get_user_by_telegram_id(db, update.effective_user.id)
    profile = db.query(Profile).filter(Profile.user_id == user.id).first()
    db.close()
    if not profile:
        await update.message.reply_text("У тебя пока нет анкеты.")
        return
    text = (
        f"Твоя анкета:\n"
        f"Возраст: {profile.age}\n"
        f"Пол: {profile.gender}\n"
        f"Город: {profile.city}\n"
        f"Ник: {profile.contact}"
    )
    await update.message.reply_text(text)

# Понравившиеся анкеты
async def liked_profiles(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    user = crud.get_user_by_telegram_id(db, update.effective_user.id)
    likes = db.query(Like).filter_by(from_user_id=user.id, is_like="like").all()
    if not likes:
        await update.message.reply_text("У тебя пока нет понравившихся анкет.")
        db.close()
        return
    response = "❤️ Понравившиеся анкеты:\n\n"
    for like in likes:
        profile = db.query(Profile).filter(Profile.user_id == like.to_user_id).first()
        target_user = db.query(User).filter(User.id == like.to_user_id).first()
        if profile and target_user:
            response += (
                f"👤 {target_user.first_name or 'Без имени'}\n"
                f"Ник: {profile.contact}\n"
                f"Возраст: {profile.age}, Пол: {profile.gender}, Город: {profile.city}\n\n"
            )
    db.close()
    await update.message.reply_text(response)
