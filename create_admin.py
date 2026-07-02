"""Birinchi administrator hisobini yaratish uchun skript.

Ishlatish:
    python create_admin.py
"""

import getpass

from werkzeug.security import generate_password_hash

from db import get_connection


def main():
    print("== Bilimdonlar: admin hisobini yaratish ==")
    full_name = input("To'liq ism: ").strip()
    username = input("Login: ").strip().lower()
    password = getpass.getpass("Parol: ")
    password2 = getpass.getpass("Parolni takrorlang: ")

    if password != password2:
        print("Xato: parollar mos kelmadi.")
        return
    if len(password) < 6:
        print("Xato: parol kamida 6 ta belgidan iborat bo'lishi kerak.")
        return

    conn = get_connection()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT id FROM users WHERE username = %s", (username,))
            if cur.fetchone():
                print(f"Xato: '{username}' logini allaqachon band.")
                return
            cur.execute(
                "INSERT INTO users (full_name, username, password_hash, role) "
                "VALUES (%s, %s, %s, 'admin')",
                (full_name, username, generate_password_hash(password)),
            )
        conn.commit()
        print(f"Admin '{username}' muvaffaqiyatli yaratildi. Endi tizimga kirishingiz mumkin.")
    finally:
        conn.close()


if __name__ == "__main__":
    main()
