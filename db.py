import pymysql
import pymysql.cursors
from flask import g
from config import Config

def get_connection():
    kwargs = dict(
        host=Config.MYSQL_HOST,
        port=Config.MYSQL_PORT,
        user=Config.MYSQL_USER,
        password=Config.MYSQL_PASSWORD,
        database=Config.MYSQL_DB,
        charset="utf8mb4",
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=False,
    )
    if Config.MYSQL_SSL:
        kwargs["ssl"] = {"ssl": {}}
    return pymysql.connect(**kwargs)

def get_db():
    if "db" not in g:
        g.db = get_connection()
    return g.db

def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()

def init_app(app):
    app.teardown_appcontext(close_db)
