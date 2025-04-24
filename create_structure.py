import os
from pathlib import Path

# Определяем структуру проекта
structure = {
    "dating-bot": {
        "bot": {
            "main.py": "# Основной входной файл Telegram-бота\nfrom telegram.ext import ApplicationBuilder\n\n# Инициализация бота\napp = ApplicationBuilder().token('YOUR_TOKEN').build()\n\nif __name__ == '__main__':\n    app.run_polling()",
            "handlers.py": "# Обработчики команд и действий бота\nfrom telegram import Update\nfrom telegram.ext import ContextTypes\n\nasync def start(update: Update, context: ContextTypes.DEFAULT_TYPE):\n    await update.message.reply_text('Привет! Я бот для знакомств!')"
        },
        "services": {
            "producer": {
                "__init__.py": "",
                "main.py": "# Сервер, получающий команды от клиента"
            },
            "consumer": {
                "__init__.py": "",
                "main.py": "# Обработчик задач из очереди"
            },
            "celery_worker.py": "# Настройка Celery\nfrom celery import Celery\n\napp = Celery('dating_bot')\napp.config_from_object('celeryconfig')"
        },
        "database": {
            "models.py": "# Описание таблиц (пользователи, анкеты)\nfrom sqlalchemy import Column, Integer, String\nfrom sqlalchemy.ext.declarative import declarative_base\n\nBase = declarative_base()\n\nclass User(Base):\n    __tablename__ = 'users'\n    id = Column(Integer, primary_key=True)\n    username = Column(String)",
            "crud.py": "# Операции с БД (create, read, update, delete)\nfrom sqlalchemy.orm import Session\n\n# Пример CRUD-операций\ndef create_user(db: Session, username: str):\n    ...",
            "init_db.py": "# Инициализация базы данных\nfrom sqlalchemy import create_engine\nfrom .models import Base\n\nengine = create_engine('sqlite:///dating.db')\nBase.metadata.create_all(engine)"
        },
        "media": {},  # Пустая папка для фотографий
        "redis": {
            "__init__.py": "",
            "client.py": "# Настройка Redis-клиента\nimport redis\n\nr = redis.Redis(host='localhost', port=6379, db=0)"
        },
        "minio": {
            "__init__.py": "",
            "client.py": "# (будет позже) Настройка MinIO клиента"
        },
        "monitoring": {
            "__init__.py": "",
            "prometheus.py": "# Настройка Prometheus для мониторинга"
        },
        "requirements.txt": "# Основные зависимости\npython-telegram-bot\ncelery\nredis\nsqlalchemy\nprometheus-client",
        "README.md": "# Dating Bot\n\nTelegram-бот для знакомств\n\n## Установка\n\n1. Установите зависимости: `pip install -r requirements.txt`\n2. Настройте базу данных\n3. Запустите бота: `python bot/main.py`"
    }
}

def create_project_structure(base_path: Path, structure: dict):
    for name, content in structure.items():
        path = base_path / name
        
        if isinstance(content, dict):
            # Создаем директорию
            path.mkdir(parents=True, exist_ok=True)
            
            # Если это не пустая папка (как media/)
            if content:
                # Добавляем __init__.py если это python пакет
                if name not in ["media", "redis", "minio", "monitoring"]:
                    (path / "__init__.py").touch()
                
                # Рекурсивно создаем вложенную структуру
                create_project_structure(path, content)
        else:
            # Создаем файл с содержимым
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)

if __name__ == "__main__":
    project_path = Path.cwd() / "dating-bot"
    create_project_structure(project_path, structure)
    print(f"Структура проекта создана в {project_path}")