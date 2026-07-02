import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-key-change-me")
    DEBUG = os.environ.get("FLASK_DEBUG", "0") == "1"

    MYSQL_HOST = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT = int(os.environ.get("MYSQL_PORT", "3306"))
    MYSQL_USER = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB = os.environ.get("MYSQL_DB", "bilimdonlar")

    TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "")

    # To'lov cheklari (skrinshot/rasm) shu papkaga saqlanadi. `static` ichida emas,
    # shunda hech kim to'g'ridan-to'g'ri havola orqali boshqalarning chekini ko'ra olmaydi —
    # fayllar faqat admin panel orqali (autentifikatsiyadan o'tib) ochiladi.
    UPLOAD_FOLDER = os.environ.get(
        "UPLOAD_FOLDER", os.path.join(BASE_DIR, "uploads", "receipts")
    )
    MAX_CONTENT_LENGTH = 8 * 1024 * 1024  # 8 MB
