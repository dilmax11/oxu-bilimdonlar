import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
    DEBUG      = os.environ.get("FLASK_DEBUG", "0") == "1"

    MYSQL_HOST     = os.environ.get("MYSQL_HOST", "localhost")
    MYSQL_PORT     = int(os.environ.get("MYSQL_PORT", "3306"))
    MYSQL_USER     = os.environ.get("MYSQL_USER", "root")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "")
    MYSQL_DB       = os.environ.get("MYSQL_DB", "bilimdonlar")
    MYSQL_SSL      = os.environ.get("MYSQL_SSL", "0") == "1"

    TELEGRAM_BOT_TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "")
