"""Bilimdonlar Telegram boti.

Bu skript alohida, doimiy ishlaydigan jarayon sifatida ishga tushiriladi:
    python telegram_bot.py

Vazifalari:
- /start <kod>  -> foydalanuvchining veb-saytdagi hisobini Telegram bilan bog'laydi
- /natija       -> foydalanuvchining so'nggi natijalarini ko'rsatadi
- /reyting      -> faol testlar ro'yxatini beradi
- /yordam       -> qisqacha yo'riqnoma

Eslatma: bu skript veb-ilova bilan bir xil MySQL bazasidan foydalanadi,
shuning uchun Flask ilovasi ishlamasa ham mustaqil ishlay oladi.
Test natijasi va g'oliblar e'loni kabi YUBORILADIGAN xabarlar esa
to'g'ridan-to'g'ri Flask ilovasi (telegram_utils.py) tomonidan jo'natiladi.
"""

import logging
import time

import requests

from config import Config
from db import get_connection

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("bilimdonlar-bot")

API_BASE = f"https://api.telegram.org/bot{Config.TELEGRAM_BOT_TOKEN}"

HELP_TEXT = (
    "🎓 <b>Bilimdonlar test platformasi boti</b>\n\n"
    "/start &lt;kod&gt; — saytdagi hisobingizni shu Telegramga ulaydi "
    "(kodni saytdagi profil sahifangizdan oling)\n"
    "/natija — so'nggi natijalaringiz\n"
    "/reyting — faol testlar ro'yxati\n"
    "/yordam — shu xabarni qayta ko'rsatadi"
)


def api_call(method, request_timeout=20, **params):
    try:
        resp = requests.post(f"{API_BASE}/{method}", json=params, timeout=request_timeout)
        return resp.json()
    except requests.RequestException as exc:
        logger.warning("API chaqiruvida xato (%s): %s", method, exc)
        return {}


def send(chat_id, text):
    api_call("sendMessage", chat_id=chat_id, text=text, parse_mode="HTML")


def handle_start(chat_id, payload):
    if not payload:
        send(
            chat_id,
            "Salom! Hisobingizni ulash uchun saytdagi profil sahifangizdan "
            "havola oling va uni shu yerda bosing.\n\n" + HELP_TEXT,
        )
        return

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, full_name FROM users WHERE telegram_link_code = %s",
                (payload,),
            )
            user = cur.fetchone()
            if not user:
                send(chat_id, "❌ Kod noto'g'ri yoki muddati o'tgan. Saytdan qayta urinib ko'ring.")
                return
            cur.execute(
                "UPDATE users SET telegram_chat_id = %s, telegram_link_code = NULL WHERE id = %s",
                (str(chat_id), user["id"]),
            )
        conn.commit()
        send(
            chat_id,
            f"✅ Hisobingiz ulandi, {user['full_name']}!\n"
            "Endi test natijalari va g'oliblar e'loni shu yerga keladi.",
        )
    finally:
        conn.close()


def handle_natija(chat_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE telegram_chat_id = %s", (str(chat_id),))
            user = cur.fetchone()
            if not user:
                send(chat_id, "Avval hisobingizni ulang: /start &lt;kod&gt;")
                return
            cur.execute(
                "SELECT t.title, r.score, r.total_points, r.time_spent_seconds, r.finished_at "
                "FROM results r JOIN tests t ON t.id = r.test_id "
                "WHERE r.user_id = %s AND r.status = 'finished' "
                "ORDER BY r.finished_at DESC LIMIT 5",
                (user["id"],),
            )
            rows = cur.fetchall()
        if not rows:
            send(chat_id, "Siz hali birorta testni yakunlamagansiz.")
            return
        lines = ["📊 <b>So'nggi natijalaringiz:</b>"]
        for r in rows:
            mins = (r["time_spent_seconds"] or 0) // 60
            secs = (r["time_spent_seconds"] or 0) % 60
            lines.append(
                f"• {r['title']}: {r['score']}/{r['total_points']} ball ({mins} daq {secs} son)"
            )
        send(chat_id, "\n".join(lines))
    finally:
        conn.close()


def handle_reyting(chat_id):
    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT id, title FROM tests WHERE is_active = 1 ORDER BY created_at DESC"
            )
            tests = cur.fetchall()
        if not tests:
            send(chat_id, "Hozircha faol testlar yo'q.")
            return
        lines = ["🏆 <b>Faol testlar:</b>", "To'liq reytingni ko'rish uchun saytga kiring:"]
        for t in tests:
            lines.append(f"• {t['title']}")
        send(chat_id, "\n".join(lines))
    finally:
        conn.close()


def process_update(update):
    message = update.get("message")
    if not message or "text" not in message:
        return
    chat_id = message["chat"]["id"]
    text = message["text"].strip()

    if text.startswith("/start"):
        parts = text.split(maxsplit=1)
        payload = parts[1].strip() if len(parts) > 1 else ""
        handle_start(chat_id, payload)
    elif text.startswith("/natija"):
        handle_natija(chat_id)
    elif text.startswith("/reyting"):
        handle_reyting(chat_id)
    else:
        send(chat_id, HELP_TEXT)


def main():
    if not Config.TELEGRAM_BOT_TOKEN:
        logger.error("TELEGRAM_BOT_TOKEN sozlanmagan. .env faylini tekshiring.")
        return

    logger.info("Bilimdonlar boti ishga tushdi (long polling)...")
    offset = 0
    while True:
        result = api_call("getUpdates", offset=offset, timeout=30, request_timeout=35)
        for update in result.get("result", []):
            offset = update["update_id"] + 1
            try:
                process_update(update)
            except Exception:
                logger.exception("Update qayta ishlashda xatolik")
        time.sleep(1)


if __name__ == "__main__":
    main()
