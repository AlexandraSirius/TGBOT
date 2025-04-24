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

AGE, GENDER, CITY, NICKNAME = range(4)

# Меню
async def show_menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [KeyboardButton("/start"), KeyboardButton("/anketa")],
        [KeyboardButton("/edit"), KeyboardButton("/search")],
        [KeyboardButton("/myprofile"), KeyboardButton("/liked")]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выбери действие 👇", reply_markup=markup)

# Анкета
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
    existing = db.query(Profile).filter(Profile.user_id == user.id).first()

    if context.user_data.get("edit") and existing:
        existing.age = context.user_data["age"]
        existing.gender = context.user_data["gender"]
        existing.city = context.user_data["city"]
        existing.contact = context.user_data["nickname"]
        db.commit()
        msg = "Анкета обновлена! 🔁"
    else:
        profile = Profile(
            user_id=user.id,
            age=context.user_data["age"],
            gender=context.user_data["gender"],
            city=context.user_data["city"],
            contact=context.user_data["nickname"]
        )
        db.add(profile)
        db.commit()
        msg = "Анкета успешно сохранена! 🔥"

    db.close()
    await update.message.reply_text(msg)

    keyboard = [
        [KeyboardButton("/start"), KeyboardButton("/anketa")],
        [KeyboardButton("/edit"), KeyboardButton("/search")],
        [KeyboardButton("/myprofile"), KeyboardButton("/liked")]
    ]
    markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text("Выбери действие 👇", reply_markup=markup)

    return ConversationHandler.END

# Обработка кнопок (лайк/пропуск)
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    action, target_id = query.data.split(":")
    db = SessionLocal()
    from_user = crud.get_user_by_telegram_id(db, update.effective_user.id)
    to_user = db.query(User).filter(User.id == int(target_id)).first()

    existing_like = db.query(Like).filter_by(
        from_user_id=from_user.id,
        to_user_id=int(target_id)
    ).first()

    if not existing_like:
        db.add(Like(
            from_user_id=from_user.id,
            to_user_id=int(target_id),
            is_like=action
        ))
        db.commit()

        mutual = db.query(Like).filter_by(
            from_user_id=int(target_id),
            to_user_id=from_user.id,
            is_like="like"
        ).first()

        if action == "like" and mutual:
            try:
                await context.bot.send_message(
                    chat_id=int(to_user.telegram_id),
                    text=f"💘 У вас совпадение с @{from_user.username or 'пользователем'}!"
                )
                await context.bot.send_message(
                    chat_id=int(from_user.telegram_id),
                    text=f"💘 У вас совпадение с @{to_user.username or 'пользователем'}!"
                )
            except Exception as e:
                print(f"[Ошибка отправки мэтча]: {e}")

    db.close()
    await query.edit_message_text("Выбор сохранён!")

# Команда /search
async def search(update: Update, context: ContextTypes.DEFAULT_TYPE):
    db = SessionLocal()
    current_user = crud.get_user_by_telegram_id(db, update.effective_user.id)

    if not current_user:
        await update.message.reply_text("Вы не зарегистрированы. Напишите /start сначала.")
        db.close()
        return

    my_profile = db.query(Profile).filter(Profile.user_id == current_user.id).first()
    if not my_profile:
        await update.message.reply_text("Сначала заполни анкету с помощью /anketa 😉")
        db.close()
        return

    profile = db.query(Profile).filter(Profile.user_id != current_user.id).first()
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
        f"Имя: {target.first_name or target.username or 'Без имени'}\n"
        f"Ник: {profile.contact}\n"
        f"Возраст: {profile.age}\n"
        f"Пол: {profile.gender}\n"
        f"Город: {profile.city}"
    )
    await update.message.reply_text(text, reply_markup=markup)
    db.close()

# Команда /myprofile
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

# Команда /liked
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
