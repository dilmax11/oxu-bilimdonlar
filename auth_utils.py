import functools

from flask import g, session, redirect, url_for, flash, request

from db import get_db


def load_logged_in_user():
    """Har bir so'rovdan oldin chaqiriladi (app.before_request)."""
    user_id = session.get("user_id")
    if user_id is None:
        g.user = None
        return
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, full_name, username, role, telegram_chat_id, is_blocked "
            "FROM users WHERE id = %s",
            (user_id,),
        )
        g.user = cur.fetchone()
    if g.user and g.user["is_blocked"]:
        session.clear()
        g.user = None


def login_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Davom etish uchun avval tizimga kiring.", "error")
            return redirect(url_for("auth.login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


def admin_required(view):
    @functools.wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            flash("Davom etish uchun avval tizimga kiring.", "error")
            return redirect(url_for("auth.login", next=request.path))
        if g.user["role"] != "admin":
            flash("Bu bo'limga faqat administratorlar kira oladi.", "error")
            return redirect(url_for("user.dashboard"))
        return view(*args, **kwargs)
    return wrapped
