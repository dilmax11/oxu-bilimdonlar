"""MySQL ulanish yordamchisi.

Flask ilovasi ichida `get_db()` har bir so'rov (request) uchun bitta
ulanishni qaytaradi va so'rov tugagach avtomatik yopadi.
Telegram bot kabi Flask kontekstidan tashqarida ishlaydigan skriptlar
uchun `get_connection()` funksiyasidan to'g'ridan-to'g'ri foydalaning.
"""

import pymysql
import pymysql.cursors
from flask import g

from config import Config


def get_connection():
    """Flask kontekstidan tashqarida (masalan, telegram_bot.py da) ishlatish uchun."""
    return pymysql.connect(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )


def get_db():
    """Flask so'rov konteksti ichida qayta ishlatiladigan ulanish."""
    if "db" not in g:
        g.db = get_connection()
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_app(app):
    app.teardown_appcontext(close_db)
