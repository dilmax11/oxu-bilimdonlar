"""Telegram Bot API orqali xabar yuborish uchun yordamchi funksiyalar.

Bu modul faqat xabar YUBORISH uchun (oddiy HTTP so'rov). Foydalanuvchi
xabarlarini QABUL qilish (masalan /start buyrug'i) uchun alohida
ishlaydigan telegram_bot.py skripti mas'ul.
"""

import logging

import requests

from config import Config

logger = logging.getLogger(__name__)

API_BASE = "https://api.telegram.org/bot{token}/{method}"


def _api_url(method: str) -> str:
    return API_BASE.format(token=Config.TELEGRAM_BOT_TOKEN, method=method)


def send_telegram_message(chat_id: str, text: str) -> bool:
    """Berilgan chat_id ga xabar yuboradi. Token sozlanmagan bo'lsa, jim o'tkazib yuboradi."""
    if not Config.TELEGRAM_BOT_TOKEN or not chat_id:
        return False
    try:
        resp = requests.post(
            _api_url("sendMessage"),
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
            },
            timeout=5,
        )
        if not resp.ok:
            logger.warning("Telegram xabar yuborilmadi: %s", resp.text)
        return resp.ok
    except requests.RequestException as exc:
        logger.warning("Telegram so'rovida xatolik: %s", exc)
        return False
