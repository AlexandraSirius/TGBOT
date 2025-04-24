# Настройка Celery
from celery import Celery

app = Celery('dating_bot')
app.config_from_object('celeryconfig')