import os
from dotenv import load_dotenv
load_dotenv()

class Config:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret")
    DEBUG      = os.environ.get("FLASK_DEBUG", "0") == "1"

    MYSQL_HOST     = os.environ.get("MYSQL_HOST", "mysql-bdca485-bilimdonlar.h.aivencloud.com")
    MYSQL_PORT     = int(os.environ.get("MYSQL_PORT", "25344"))
    MYSQL_USER     = os.environ.get("MYSQL_USER", "avnadmin")
    MYSQL_PASSWORD = os.environ.get("MYSQL_PASSWORD", "AVNS_1q4D1XvJArgJ_fDwIHD")
    MYSQL_DB       = os.environ.get("MYSQL_DB", "defaultdb")
    MYSQL_SSL      = os.environ.get("MYSQL_SSL", "REQUIRED") == "1"

    TELEGRAM_BOT_TOKEN    = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    TELEGRAM_BOT_USERNAME = os.environ.get("TELEGRAM_BOT_USERNAME", "")
