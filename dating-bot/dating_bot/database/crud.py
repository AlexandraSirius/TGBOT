# dating_bot/database/crud.py

from sqlalchemy.orm import Session
from dating_bot.database.models import User

def get_user_by_telegram_id(db: Session, telegram_id: int):
    return db.query(User).filter(User.telegram_id == telegram_id).first()

def create_user(db: Session, telegram_id: int, username: str, first_name: str):
    db_user = User(
        telegram_id=telegram_id,
        username=username,
        first_name=first_name
    )
    db.add(db_user)
    db.commit()
    db.refresh(db_user)
    return db_user
