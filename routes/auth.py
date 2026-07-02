import re

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, g
from werkzeug.security import generate_password_hash, check_password_hash

from db import get_db
from telegram_utils import send_telegram_message

bp = Blueprint("auth", __name__, url_prefix="/auth")

USERNAME_RE = re.compile(r"^[a-zA-Z0-9_]{4,30}$")


@bp.route("/register", methods=("GET", "POST"))
def register():
    if g.user:
        return redirect(url_for("user.dashboard"))

    if request.method == "POST":
        full_name = request.form.get("full_name", "").strip()
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")
        password2 = request.form.get("password2", "")

        error = None
        if not full_name or len(full_name) < 3:
            error = "Ism familiyangizni to'liq kiriting."
        elif not USERNAME_RE.match(username):
            error = "Login 4-30 ta belgidan iborat bo'lib, faqat lotin harflari, raqam va pastki chiziqdan tashkil topishi kerak."
        elif len(password) < 6:
            error = "Parol kamida 6 ta belgidan iborat bo'lishi kerak."
        elif password != password2:
            error = "Parollar bir-biriga mos kelmadi."

        db = get_db()
        if error is None:
            with db.cursor() as cur:
                cur.execute("SELECT id FROM users WHERE username = %s", (username,))
                if cur.fetchone() is not None:
                    error = f"'{username}' logini band. Boshqa login tanlang."

        if error is None:
            with db.cursor() as cur:
                cur.execute(
                    "INSERT INTO users (full_name, username, password_hash, role) "
                    "VALUES (%s, %s, %s, 'user')",
                    (full_name, username, generate_password_hash(password)),
                )
            db.commit()
            flash("Ro'yxatdan muvaffaqiyatli o'tdingiz! Endi tizimga kiring.", "success")
            return redirect(url_for("auth.login"))

        flash(error, "error")

    return render_template("register.html")


@bp.route("/login", methods=("GET", "POST"))
def login():
    if g.user:
        return redirect(url_for("user.dashboard"))

    if request.method == "POST":
        username = request.form.get("username", "").strip().lower()
        password = request.form.get("password", "")

        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE username = %s", (username,))
            user = cur.fetchone()

        error = None
        if user is None or not check_password_hash(user["password_hash"], password):
            error = "Login yoki parol noto'g'ri."
        elif user["is_blocked"]:
            error = "Hisobingiz administrator tomonidan bloklangan."

        if error is None:
            session.clear()
            session["user_id"] = user["id"]
            session.permanent = True
            flash(f"Xush kelibsiz, {user['full_name']}!", "success")
            next_url = request.args.get("next")
            if user["role"] == "admin":
                return redirect(next_url or url_for("admin.dashboard"))
            return redirect(next_url or url_for("user.dashboard"))

        flash(error, "error")

    return render_template("login.html")


@bp.route("/logout")
def logout():
    session.clear()
    flash("Tizimdan chiqdingiz.", "success")
    return redirect(url_for("auth.login"))
