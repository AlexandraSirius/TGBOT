# database/init_db.py

from sqlalchemy import create_engine
from dating_bot.database.models import Base


engine = create_engine("postgresql://postgres:1234@localhost/dating_bot")

def init():
    Base.metadata.create_all(bind=engine)

if __name__ == "__main__":
    init()
