from flask import (
    Blueprint, render_template, request, redirect, url_for, flash, g, send_from_directory, abort
)

from db import get_db
from auth_utils import admin_required
from telegram_utils import send_telegram_message
from config import Config

bp = Blueprint("admin", __name__, url_prefix="/admin")


def _parse_schedule_fields(form):
    """starts_at, ends_at, prize_info maydonlarini formdan o'qiydi."""
    starts_at = form.get("starts_at", "").strip() or None
    ends_at = form.get("ends_at", "").strip() or None
    prize_info = form.get("prize_info", "").strip() or None
    return starts_at, ends_at, prize_info


def _parse_payment_fields(form):
    """is_paid, price maydonlarini formdan o'qiydi."""
    is_paid = 1 if form.get("is_paid") else 0
    price_raw = form.get("price", "0").strip()
    price = int(price_raw) if price_raw.isdigit() else 0
    if not is_paid:
        price = 0
    return is_paid, price

MEDALS = ["🥇", "🥈", "🥉"]


@bp.route("/")
@admin_required
def dashboard():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT COUNT(*) AS c FROM users WHERE role = 'user'")
        total_users = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM tests")
        total_tests = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM tests WHERE is_active = 1")
        active_tests = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM results WHERE status = 'finished'")
        total_attempts = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM payment_requests WHERE status = 'pending'")
        pending_payments = cur.fetchone()["c"]
        cur.execute(
            "SELECT t.title, u.full_name, r.score, r.total_points, r.finished_at "
            "FROM results r JOIN users u ON u.id = r.user_id JOIN tests t ON t.id = r.test_id "
            "WHERE r.status = 'finished' ORDER BY r.finished_at DESC LIMIT 8"
        )
        recent = cur.fetchall()
    return render_template(
        "admin/admin_dashboard.html",
        total_users=total_users,
        total_tests=total_tests,
        active_tests=active_tests,
        total_attempts=total_attempts,
        pending_payments=pending_payments,
        recent=recent,
    )


# ---------- Tests ----------

@bp.route("/tests")
@admin_required
def tests_list():
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT t.*, "
            "(SELECT COUNT(*) FROM questions q WHERE q.test_id = t.id) AS question_count, "
            "(SELECT COUNT(*) FROM results r WHERE r.test_id = t.id AND r.status='finished') AS attempt_count "
            "FROM tests t ORDER BY t.created_at DESC"
        )
        tests = cur.fetchall()
    return render_template("admin/manage_tests.html", tests=tests)


@bp.route("/tests/new", methods=["GET", "POST"])
@admin_required
def test_new():
    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        time_limit = request.form.get("time_limit_minutes", "10").strip()

        error = None
        if not title:
            error = "Test nomini kiriting."
        if not time_limit.isdigit() or int(time_limit) <= 0:
            error = "Vaqt chegarasi musbat son bo'lishi kerak."

        if error:
            flash(error, "error")
        else:
            db = get_db()
            starts_at, ends_at, prize_info = _parse_schedule_fields(request.form)
            is_paid, price = _parse_payment_fields(request.form)
            with db.cursor() as cur:
                cur.execute(
                    "INSERT INTO tests (title, description, time_limit_minutes, "
                    "starts_at, ends_at, prize_info, is_paid, price, created_by) "
                    "VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)",
                    (title, description, int(time_limit),
                     starts_at, ends_at, prize_info, is_paid, price, g.user["id"]),
                )
                db.commit()
                test_id = cur.lastrowid
            flash("Test yaratildi. Endi savollar qo'shing.", "success")
            return redirect(url_for("admin.questions_list", test_id=test_id))

    return render_template("admin/edit_test.html", test=None)


@bp.route("/tests/<int:test_id>/edit", methods=["GET", "POST"])
@admin_required
def test_edit(test_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tests WHERE id = %s", (test_id,))
        test = cur.fetchone()
    if not test:
        flash("Test topilmadi.", "error")
        return redirect(url_for("admin.tests_list"))

    if request.method == "POST":
        title = request.form.get("title", "").strip()
        description = request.form.get("description", "").strip()
        time_limit = request.form.get("time_limit_minutes", "10").strip()

        error = None
        if not title:
            error = "Test nomini kiriting."
        if not time_limit.isdigit() or int(time_limit) <= 0:
            error = "Vaqt chegarasi musbat son bo'lishi kerak."

        if error:
            flash(error, "error")
        else:
            starts_at, ends_at, prize_info = _parse_schedule_fields(request.form)
            is_paid, price = _parse_payment_fields(request.form)
            with db.cursor() as cur:
                cur.execute(
                    "UPDATE tests SET title=%s, description=%s, time_limit_minutes=%s, "
                    "starts_at=%s, ends_at=%s, prize_info=%s, is_paid=%s, price=%s WHERE id=%s",
                    (title, description, int(time_limit),
                     starts_at, ends_at, prize_info, is_paid, price, test_id),
                )
                db.commit()
            flash("Test yangilandi.", "success")
            return redirect(url_for("admin.tests_list"))

    return render_template("admin/edit_test.html", test=test)


@bp.route("/tests/<int:test_id>/toggle", methods=["POST"])
@admin_required
def test_toggle(test_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT is_active, title FROM tests WHERE id = %s", (test_id,))
        test = cur.fetchone()
        if not test:
            flash("Test topilmadi.", "error")
            return redirect(url_for("admin.tests_list"))
        new_state = 0 if test["is_active"] else 1
        cur.execute("UPDATE tests SET is_active = %s WHERE id = %s", (new_state, test_id))
        db.commit()
    flash(
        f"\"{test['title']}\" testi {'faollashtirildi' if new_state else 'to‘xtatildi'}.",
        "success",
    )
    return redirect(url_for("admin.tests_list"))


@bp.route("/tests/<int:test_id>/delete", methods=["POST"])
@admin_required
def test_delete(test_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM tests WHERE id = %s", (test_id,))
        db.commit()
    flash("Test va unga tegishli barcha ma'lumotlar o'chirildi.", "success")
    return redirect(url_for("admin.tests_list"))


# ---------- Questions ----------

@bp.route("/tests/<int:test_id>/questions")
@admin_required
def questions_list(test_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tests WHERE id = %s", (test_id,))
        test = cur.fetchone()
        if not test:
            flash("Test topilmadi.", "error")
            return redirect(url_for("admin.tests_list"))
        cur.execute(
            "SELECT * FROM questions WHERE test_id = %s ORDER BY order_no, id", (test_id,)
        )
        questions = cur.fetchall()
    return render_template("admin/manage_questions.html", test=test, questions=questions)


@bp.route("/tests/<int:test_id>/questions/new", methods=["GET", "POST"])
@admin_required
def question_new(test_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tests WHERE id = %s", (test_id,))
        test = cur.fetchone()
    if not test:
        flash("Test topilmadi.", "error")
        return redirect(url_for("admin.tests_list"))

    if request.method == "POST":
        data, error = _parse_question_form(request.form)
        if error:
            flash(error, "error")
        else:
            with db.cursor() as cur:
                cur.execute(
                    "INSERT INTO questions (test_id, question_text, option_a, option_b, "
                    "option_c, option_d, correct_option, points, order_no) "
                    "VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s)",
                    (
                        test_id, data["question_text"], data["option_a"], data["option_b"],
                        data["option_c"], data["option_d"], data["correct_option"],
                        data["points"], data["order_no"],
                    ),
                )
                db.commit()
            flash("Savol qo'shildi.", "success")
            return redirect(url_for("admin.questions_list", test_id=test_id))

    return render_template("admin/edit_question.html", test=test, question=None)


@bp.route("/questions/<int:question_id>/edit", methods=["GET", "POST"])
@admin_required
def question_edit(question_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM questions WHERE id = %s", (question_id,))
        question = cur.fetchone()
        if not question:
            flash("Savol topilmadi.", "error")
            return redirect(url_for("admin.tests_list"))
        cur.execute("SELECT * FROM tests WHERE id = %s", (question["test_id"],))
        test = cur.fetchone()

    if request.method == "POST":
        data, error = _parse_question_form(request.form)
        if error:
            flash(error, "error")
        else:
            with db.cursor() as cur:
                cur.execute(
                    "UPDATE questions SET question_text=%s, option_a=%s, option_b=%s, "
                    "option_c=%s, option_d=%s, correct_option=%s, points=%s, order_no=%s "
                    "WHERE id=%s",
                    (
                        data["question_text"], data["option_a"], data["option_b"],
                        data["option_c"], data["option_d"], data["correct_option"],
                        data["points"], data["order_no"], question_id,
                    ),
                )
                db.commit()
            flash("Savol yangilandi.", "success")
            return redirect(url_for("admin.questions_list", test_id=test["id"]))

    return render_template("admin/edit_question.html", test=test, question=question)


@bp.route("/questions/<int:question_id>/delete", methods=["POST"])
@admin_required
def question_delete(question_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT test_id FROM questions WHERE id = %s", (question_id,))
        question = cur.fetchone()
        if question:
            cur.execute("DELETE FROM questions WHERE id = %s", (question_id,))
            db.commit()
    flash("Savol o'chirildi.", "success")
    if question:
        return redirect(url_for("admin.questions_list", test_id=question["test_id"]))
    return redirect(url_for("admin.tests_list"))


def _parse_question_form(form):
    question_text = form.get("question_text", "").strip()
    option_a = form.get("option_a", "").strip()
    option_b = form.get("option_b", "").strip()
    option_c = form.get("option_c", "").strip()
    option_d = form.get("option_d", "").strip()
    correct_option = form.get("correct_option", "").strip().upper()
    points = form.get("points", "1").strip()
    order_no = form.get("order_no", "0").strip()

    if not all([question_text, option_a, option_b, option_c, option_d]):
        return None, "Savol matni va barcha 4 ta variant to'ldirilishi shart."
    if correct_option not in ("A", "B", "C", "D"):
        return None, "To'g'ri javobni A, B, C yoki D dan tanlang."
    if not points.isdigit() or int(points) <= 0:
        return None, "Ball musbat son bo'lishi kerak."
    if not order_no.lstrip("-").isdigit():
        order_no = "0"

    return {
        "question_text": question_text,
        "option_a": option_a,
        "option_b": option_b,
        "option_c": option_c,
        "option_d": option_d,
        "correct_option": correct_option,
        "points": int(points),
        "order_no": int(order_no),
    }, None


# ---------- Results / Winners ----------

@bp.route("/tests/<int:test_id>/live")
@admin_required
def test_live(test_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tests WHERE id = %s", (test_id,))
        test = cur.fetchone()
        if not test:
            flash("Test topilmadi.", "error")
            return redirect(url_for("admin.tests_list"))
        cur.execute(
            "SELECT COUNT(*) AS c FROM questions WHERE test_id = %s", (test_id,)
        )
        question_count = cur.fetchone()["c"]
    return render_template(
        "admin/test_live.html", test=test, question_count=question_count
    )


@bp.route("/tests/<int:test_id>/live-data")
@admin_required
def test_live_data(test_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT id, points FROM questions WHERE test_id = %s ORDER BY order_no, id",
            (test_id,),
        )
        questions = cur.fetchall()

        cur.execute(
            "SELECT r.id AS result_id, r.user_id, r.status, "
            "u.full_name, u.username "
            "FROM results r JOIN users u ON u.id = r.user_id "
            "WHERE r.test_id = %s "
            "ORDER BY r.started_at ASC",
            (test_id,),
        )
        results = cur.fetchall()

        cur.execute(
            "SELECT a.result_id, a.question_id, a.is_correct "
            "FROM answers a "
            "JOIN results r ON r.id = a.result_id "
            "WHERE r.test_id = %s",
            (test_id,),
        )
        answer_rows = cur.fetchall()

    question_ids = [q["id"] for q in questions]
    points_by_q = {q["id"]: q["points"] for q in questions}

    answers_by_result = {}
    for a in answer_rows:
        answers_by_result.setdefault(a["result_id"], {})[a["question_id"]] = a["is_correct"]

    participants = []
    for r in results:
        ans = answers_by_result.get(r["result_id"], {})
        score = sum(
            points_by_q.get(qid, 0) for qid, is_correct in ans.items() if is_correct
        )
        cells = []
        for qid in question_ids:
            if qid not in ans:
                cells.append("skipped")
            elif ans[qid]:
                cells.append("correct")
            else:
                cells.append("wrong")
        participants.append(
            {
                "user_id": r["user_id"],
                "full_name": r["full_name"],
                "username": r["username"],
                "status": r["status"],
                "score": score,
                "answers": cells,
            }
        )

    participants.sort(key=lambda p: -p["score"])

    return {"question_count": len(question_ids), "participants": participants}


@bp.route("/tests/<int:test_id>/results")
@admin_required
def test_results(test_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tests WHERE id = %s", (test_id,))
        test = cur.fetchone()
        if not test:
            flash("Test topilmadi.", "error")
            return redirect(url_for("admin.tests_list"))
        cur.execute(
            "SELECT r.id, r.user_id, u.full_name, u.username, r.score, r.total_points, "
            "r.time_spent_seconds, r.finished_at, u.telegram_chat_id "
            "FROM results r JOIN users u ON u.id = r.user_id "
            "WHERE r.test_id = %s AND r.status = 'finished' "
            "ORDER BY r.score DESC, r.time_spent_seconds ASC",
            (test_id,),
        )
        rows = cur.fetchall()
    return render_template("admin/test_results.html", test=test, rows=rows, medals=MEDALS)


@bp.route("/tests/<int:test_id>/announce", methods=["POST"])
@admin_required
def announce_winners(test_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT title FROM tests WHERE id = %s", (test_id,))
        test = cur.fetchone()
        if not test:
            flash("Test topilmadi.", "error")
            return redirect(url_for("admin.tests_list"))
        cur.execute(
            "SELECT u.full_name, u.telegram_chat_id, r.score, r.total_points "
            "FROM results r JOIN users u ON u.id = r.user_id "
            "WHERE r.test_id = %s AND r.status = 'finished' "
            "ORDER BY r.score DESC, r.time_spent_seconds ASC LIMIT 3",
            (test_id,),
        )
        winners = cur.fetchall()

    if not winners:
        flash("Hali natijalar yo'q, e'lon qilib bo'lmaydi.", "error")
        return redirect(url_for("admin.test_results", test_id=test_id))

    sent = 0
    lines = [f"🏆 <b>{test['title']}</b> g'oliblari:"]
    for i, w in enumerate(winners):
        lines.append(f"{MEDALS[i]} {w['full_name']} — {w['score']}/{w['total_points']} ball")
    announcement = "\n".join(lines)

    for w in winners:
        if w["telegram_chat_id"]:
            if send_telegram_message(w["telegram_chat_id"], announcement):
                sent += 1

    flash(f"G'oliblar e'lon qilindi. {sent} ta xabar Telegram orqali yuborildi.", "success")
    return redirect(url_for("admin.test_results", test_id=test_id))


# ---------- Users ----------

@bp.route("/users")
@admin_required
def users_list():
    db = get_db()
    q = request.args.get("q", "").strip()
    db_cursor_sql = "SELECT * FROM users"
    params = ()
    if q:
        db_cursor_sql += " WHERE full_name LIKE %s OR username LIKE %s"
        like = f"%{q}%"
        params = (like, like)
    db_cursor_sql += " ORDER BY created_at DESC"
    with db.cursor() as cur:
        cur.execute(db_cursor_sql, params)
        users = cur.fetchall()
    return render_template("admin/manage_users.html", users=users, q=q)


@bp.route("/users/<int:user_id>/toggle_role", methods=["POST"])
@admin_required
def user_toggle_role(user_id):
    if user_id == g.user["id"]:
        flash("O'zingizning rolingizni o'zgartira olmaysiz.", "error")
        return redirect(url_for("admin.users_list"))
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT role FROM users WHERE id = %s", (user_id,))
        u = cur.fetchone()
        if not u:
            flash("Foydalanuvchi topilmadi.", "error")
            return redirect(url_for("admin.users_list"))
        new_role = "user" if u["role"] == "admin" else "admin"
        cur.execute("UPDATE users SET role = %s WHERE id = %s", (new_role, user_id))
        db.commit()
    flash(f"Foydalanuvchi roli '{new_role}' ga o'zgartirildi.", "success")
    return redirect(url_for("admin.users_list"))


@bp.route("/users/<int:user_id>/toggle_block", methods=["POST"])
@admin_required
def user_toggle_block(user_id):
    if user_id == g.user["id"]:
        flash("O'zingizni bloklay olmaysiz.", "error")
        return redirect(url_for("admin.users_list"))
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT is_blocked FROM users WHERE id = %s", (user_id,))
        u = cur.fetchone()
        if not u:
            flash("Foydalanuvchi topilmadi.", "error")
            return redirect(url_for("admin.users_list"))
        new_state = 0 if u["is_blocked"] else 1
        cur.execute("UPDATE users SET is_blocked = %s WHERE id = %s", (new_state, user_id))
        db.commit()
    flash("Foydalanuvchi holati yangilandi.", "success")
    return redirect(url_for("admin.users_list"))


@bp.route("/users/<int:user_id>/delete", methods=["POST"])
@admin_required
def user_delete(user_id):
    if user_id == g.user["id"]:
        flash("O'zingizni o'chira olmaysiz.", "error")
        return redirect(url_for("admin.users_list"))
    db = get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
        db.commit()
    flash("Foydalanuvchi o'chirildi.", "success")
    return redirect(url_for("admin.users_list"))


# ---------- To'lovlar (pullik testlar uchun ruhsatlar) ----------

@bp.route("/payments")
@admin_required
def payments_list():
    db = get_db()
    status_filter = request.args.get("status", "pending")
    test_filter = request.args.get("test_id", "").strip()

    sql = (
        "SELECT p.*, u.full_name, u.username, u.telegram_chat_id, "
        "t.title AS test_title, t.price AS test_price, t.starts_at AS test_starts_at "
        "FROM payment_requests p "
        "JOIN users u ON u.id = p.user_id "
        "JOIN tests t ON t.id = p.test_id "
        "WHERE 1=1"
    )
    params = []
    if status_filter in ("pending", "approved", "rejected"):
        sql += " AND p.status = %s"
        params.append(status_filter)
    if test_filter.isdigit():
        sql += " AND p.test_id = %s"
        params.append(int(test_filter))
    sql += " ORDER BY p.created_at DESC"

    with db.cursor() as cur:
        cur.execute(sql, params)
        requests_rows = cur.fetchall()
        cur.execute("SELECT id, title FROM tests WHERE is_paid = 1 ORDER BY created_at DESC")
        paid_tests = cur.fetchall()

    return render_template(
        "admin/payments.html",
        requests_rows=requests_rows,
        paid_tests=paid_tests,
        status_filter=status_filter,
        test_filter=test_filter,
    )


@bp.route("/payments/<int:payment_id>/receipt")
@admin_required
def payment_receipt(payment_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT receipt_path FROM payment_requests WHERE id = %s", (payment_id,))
        payment = cur.fetchone()
    if not payment:
        abort(404)
    return send_from_directory(Config.UPLOAD_FOLDER, payment["receipt_path"])


@bp.route("/payments/<int:payment_id>/approve", methods=["POST"])
@admin_required
def payment_approve(payment_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT p.*, u.telegram_chat_id, u.full_name, t.title AS test_title "
            "FROM payment_requests p "
            "JOIN users u ON u.id = p.user_id "
            "JOIN tests t ON t.id = p.test_id "
            "WHERE p.id = %s",
            (payment_id,),
        )
        payment = cur.fetchone()
        if not payment:
            flash("So'rov topilmadi.", "error")
            return redirect(url_for("admin.payments_list"))

        cur.execute(
            "UPDATE payment_requests SET status='approved', admin_comment=NULL, "
            "reviewed_at=NOW(), reviewed_by=%s WHERE id=%s",
            (g.user["id"], payment_id),
        )
        db.commit()

    if payment["telegram_chat_id"]:
        send_telegram_message(
            payment["telegram_chat_id"],
            f"✅ To'lovingiz tasdiqlandi! Endi <b>{payment['test_title']}</b> "
            f"testida qatnashish huquqiga ega bo'ldingiz.",
        )

    flash(f"{payment['full_name']} uchun ruhsat ochildi.", "success")
    return redirect(url_for("admin.payments_list", status=request.form.get("return_status", "pending")))


@bp.route("/payments/<int:payment_id>/reject", methods=["POST"])
@admin_required
def payment_reject(payment_id):
    db = get_db()
    comment = request.form.get("admin_comment", "").strip() or "To'lov tasdiqlanmadi."
    with db.cursor() as cur:
        cur.execute(
            "SELECT p.*, u.telegram_chat_id, u.full_name, t.title AS test_title "
            "FROM payment_requests p "
            "JOIN users u ON u.id = p.user_id "
            "JOIN tests t ON t.id = p.test_id "
            "WHERE p.id = %s",
            (payment_id,),
        )
        payment = cur.fetchone()
        if not payment:
            flash("So'rov topilmadi.", "error")
            return redirect(url_for("admin.payments_list"))

        cur.execute(
            "UPDATE payment_requests SET status='rejected', admin_comment=%s, "
            "reviewed_at=NOW(), reviewed_by=%s WHERE id=%s",
            (comment, g.user["id"], payment_id),
        )
        db.commit()

    if payment["telegram_chat_id"]:
        send_telegram_message(
            payment["telegram_chat_id"],
            f"❌ <b>{payment['test_title']}</b> testi uchun to'lovingiz rad etildi.\n"
            f"Sabab: {comment}\nIltimos, to'lov chekini qaytadan tekshirib yuklang.",
        )

    flash(f"{payment['full_name']} uchun so'rov rad etildi.", "success")
    return redirect(url_for("admin.payments_list", status=request.form.get("return_status", "pending")))


# ---------- Sozlamalar (to'lov kartasi) ----------

@bp.route("/settings", methods=["GET", "POST"])
@admin_required
def settings_page():
    db = get_db()
    if request.method == "POST":
        card_number = request.form.get("payment_card_number", "").strip()
        card_owner = request.form.get("payment_card_owner", "").strip()
        if not card_number or not card_owner:
            flash("Karta raqami va egasining F.I.SH.ni to'liq kiriting.", "error")
        else:
            with db.cursor() as cur:
                cur.execute(
                    "INSERT INTO settings (name, value) VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE value = VALUES(value)",
                    ("payment_card_number", card_number),
                )
                cur.execute(
                    "INSERT INTO settings (name, value) VALUES (%s, %s) "
                    "ON DUPLICATE KEY UPDATE value = VALUES(value)",
                    ("payment_card_owner", card_owner),
                )
                db.commit()
            flash("Sozlamalar saqlandi.", "success")
            return redirect(url_for("admin.settings_page"))

    with db.cursor() as cur:
        cur.execute(
            "SELECT name, value FROM settings WHERE name IN "
            "('payment_card_number', 'payment_card_owner')"
        )
        settings = {row["name"]: row["value"] for row in cur.fetchall()}

    return render_template("admin/settings.html", settings=settings)
