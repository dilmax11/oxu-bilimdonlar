import os
import random
import secrets
import uuid
from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash, g
from werkzeug.utils import secure_filename

from db import get_db
from auth_utils import login_required
from telegram_utils import send_telegram_message
from config import Config

bp = Blueprint("user", __name__, url_prefix="/u")

ALLOWED_RECEIPT_EXT = {"jpg", "jpeg", "png", "pdf", "webp"}


def _allowed_receipt(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in ALLOWED_RECEIPT_EXT


def get_payment_status(db, user_id, test_id):
    """Berilgan test uchun foydalanuvchining to'lov so'rovi holatini qaytaradi (yoki None)."""
    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM payment_requests WHERE user_id = %s AND test_id = %s",
            (user_id, test_id),
        )
        return cur.fetchone()


def has_test_access(db, user_id, test):
    """Foydalanuvchi shu testga kirish huquqiga ega-yo'qligini tekshiradi.
    Bepul testlarga hamma ro'yxatdan o'tgan foydalanuvchi kira oladi,
    pullik testlarga esa faqat to'lovi tasdiqlangan (approved) foydalanuvchi kira oladi."""
    if not test["is_paid"]:
        return True
    payment = get_payment_status(db, user_id, test["id"])
    return bool(payment and payment["status"] == "approved")


def _finish_attempt(db, result, answers):
    """Testni yakunlaydi: ballarni hisoblaydi, javoblarni saqlaydi, natijani yopadi."""
    test_id = result["test_id"]
    user_id = result["user_id"]

    with db.cursor() as cur:
        cur.execute(
            "SELECT id, correct_option, points FROM questions WHERE test_id = %s",
            (test_id,),
        )
        questions = cur.fetchall()
        cur.execute("SELECT time_limit_minutes FROM tests WHERE id = %s", (test_id,))
        test = cur.fetchone()

    score = 0
    total_points = 0
    answer_rows = []
    for q in questions:
        total_points += q["points"]
        selected = answers.get(q["id"])
        is_correct = 1 if selected == q["correct_option"] else 0
        if is_correct:
            score += q["points"]
        answer_rows.append((result["id"], q["id"], selected, is_correct))

    elapsed_seconds = int((datetime.now() - result["started_at"]).total_seconds())
    max_seconds = test["time_limit_minutes"] * 60
    time_spent = max(0, min(elapsed_seconds, max_seconds))

    with db.cursor() as cur:
        cur.execute("DELETE FROM answers WHERE result_id = %s", (result["id"],))
        if answer_rows:
            cur.executemany(
                "INSERT INTO answers (result_id, question_id, selected_option, is_correct) "
                "VALUES (%s, %s, %s, %s)",
                answer_rows,
            )
        cur.execute(
            "UPDATE results SET status='finished', score=%s, total_points=%s, "
            "time_spent_seconds=%s, finished_at=NOW() WHERE id=%s",
            (score, total_points, time_spent, result["id"]),
        )
    db.commit()

    with db.cursor() as cur:
        cur.execute(
            "SELECT telegram_chat_id FROM users WHERE id = %s", (user_id,)
        )
        user = cur.fetchone()
        cur.execute("SELECT title FROM tests WHERE id = %s", (test_id,))
        test_row = cur.fetchone()

    if user and user["telegram_chat_id"]:
        text = (
            f"✅ <b>{test_row['title']}</b> testini yakunladingiz!\n"
            f"Natija: <b>{score}/{total_points}</b> ball\n"
            f"Sarflangan vaqt: {time_spent // 60} daqiqa {time_spent % 60} soniya"
        )
        send_telegram_message(user["telegram_chat_id"], text)

    return score, total_points, time_spent


@bp.route("/dashboard")
@login_required
def dashboard():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tests WHERE is_active = 1 ORDER BY created_at DESC")
        active_tests = cur.fetchall()
        cur.execute(
            "SELECT test_id, status, score, total_points FROM results WHERE user_id = %s",
            (g.user["id"],),
        )
        my_results = {r["test_id"]: r for r in cur.fetchall()}
        cur.execute(
            "SELECT test_id, status, admin_comment FROM payment_requests WHERE user_id = %s",
            (g.user["id"],),
        )
        my_payments = {p["test_id"]: p for p in cur.fetchall()}
    return render_template(
        "user_dashboard.html",
        tests=active_tests,
        my_results=my_results,
        my_payments=my_payments,
    )


@bp.route("/test/<int:test_id>/start", methods=["POST"])
@login_required
def start_test(test_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tests WHERE id = %s AND is_active = 1", (test_id,))
        test = cur.fetchone()
        if not test:
            flash("Test topilmadi yoki hozircha faol emas.", "error")
            return redirect(url_for("user.dashboard"))

        if not has_test_access(db, g.user["id"], test):
            flash(
                "Bu pullik test. Qatnashish uchun avval to'lov chekini yuklang va "
                "administrator tasdiqlashini kutib turing.",
                "error",
            )
            return redirect(url_for("user.payment_page", test_id=test_id))

        cur.execute(
            "SELECT * FROM results WHERE user_id = %s AND test_id = %s",
            (g.user["id"], test_id),
        )
        result = cur.fetchone()

        if result is None:
            cur.execute(
                "INSERT INTO results (user_id, test_id, status, started_at) "
                "VALUES (%s, %s, 'in_progress', NOW())",
                (g.user["id"], test_id),
            )
            db.commit()
        elif result["status"] == "finished":
            flash("Siz bu testni allaqachon topshirgansiz.", "error")
            return redirect(url_for("user.test_result", test_id=test_id))

    return redirect(url_for("user.take_test", test_id=test_id))


@bp.route("/test/<int:test_id>/pay", methods=["GET", "POST"])
@login_required
def payment_page(test_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tests WHERE id = %s", (test_id,))
        test = cur.fetchone()
        if not test:
            flash("Test topilmadi.", "error")
            return redirect(url_for("user.dashboard"))
        if not test["is_paid"]:
            flash("Bu test bepul — to'lov shart emas.", "success")
            return redirect(url_for("user.dashboard"))

        cur.execute(
            "SELECT name, value FROM settings WHERE name IN "
            "('payment_card_number', 'payment_card_owner')"
        )
        settings = {row["name"]: row["value"] for row in cur.fetchall()}

    payment = get_payment_status(db, g.user["id"], test_id)

    if request.method == "POST":
        if payment and payment["status"] == "approved":
            flash("Bu test uchun to'lovingiz allaqachon tasdiqlangan.", "success")
            return redirect(url_for("user.dashboard"))

        file = request.files.get("receipt")
        if not file or file.filename == "":
            flash("Iltimos, to'lov chekini (rasm yoki PDF) yuklang.", "error")
            return redirect(url_for("user.payment_page", test_id=test_id))
        if not _allowed_receipt(file.filename):
            flash("Faqat JPG, PNG, WEBP yoki PDF fayl yuklash mumkin.", "error")
            return redirect(url_for("user.payment_page", test_id=test_id))

        ext = secure_filename(file.filename).rsplit(".", 1)[1].lower()
        stored_name = f"{uuid.uuid4().hex}.{ext}"
        file.save(os.path.join(Config.UPLOAD_FOLDER, stored_name))

        with db.cursor() as cur:
            cur.execute(
                "INSERT INTO payment_requests "
                "(user_id, test_id, receipt_path, status, admin_comment, created_at, "
                " reviewed_at, reviewed_by) "
                "VALUES (%s, %s, %s, 'pending', NULL, NOW(), NULL, NULL) "
                "ON DUPLICATE KEY UPDATE "
                "receipt_path = VALUES(receipt_path), status = 'pending', "
                "admin_comment = NULL, created_at = NOW(), reviewed_at = NULL, reviewed_by = NULL",
                (g.user["id"], test_id, stored_name),
            )
            db.commit()

        flash(
            "To'lov chekingiz qabul qilindi. Administrator tasdiqlagach, "
            "testga kirish huquqi ochiladi.",
            "success",
        )
        return redirect(url_for("user.dashboard"))

    return render_template(
        "pay_test.html", test=test, settings=settings, payment=payment
    )


@bp.route("/test/<int:test_id>/take")
@login_required
def take_test(test_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tests WHERE id = %s", (test_id,))
        test = cur.fetchone()
        if not test or not test["is_active"]:
            flash("Test topilmadi yoki hozircha faol emas.", "error")
            return redirect(url_for("user.dashboard"))

        cur.execute(
            "SELECT * FROM results WHERE user_id = %s AND test_id = %s",
            (g.user["id"], test_id),
        )
        result = cur.fetchone()
        if result is None:
            flash("Avval testni boshlang.", "error")
            return redirect(url_for("user.dashboard"))
        if result["status"] == "finished":
            return redirect(url_for("user.test_result", test_id=test_id))

        elapsed = (datetime.now() - result["started_at"]).total_seconds()
        remaining = test["time_limit_minutes"] * 60 - elapsed
        if remaining <= 0:
            _finish_attempt(db, result, {})
            flash("Vaqt tugagani sababli test avtomatik yakunlandi.", "error")
            return redirect(url_for("user.test_result", test_id=test_id))

        cur.execute(
            "SELECT id, question_text, option_a, option_b, option_c, option_d "
            "FROM questions WHERE test_id = %s ORDER BY order_no, id",
            (test_id,),
        )
        questions = cur.fetchall()

    # Savollar tartibini aralashtiramiz
    random.shuffle(questions)

    # Har bir savol uchun variantlar (A/B/C/D) tartibini aralashtiramiz.
    # `value` har doim asl harfni (a/b/c/d) saqlaydi, shuning uchun
    # baholash (grading) mantiqi o'zgarishsiz qoladi - faqat ko'rinish tartibi aralashadi.
    for q in questions:
        opts = [
            ("A", q["option_a"]),
            ("B", q["option_b"]),
            ("C", q["option_c"]),
            ("D", q["option_d"]),
        ]
        random.shuffle(opts)
        q["shuffled_options"] = opts

    return render_template(
        "take_test.html", test=test, questions=questions, remaining_seconds=int(remaining)
    )


@bp.route("/test/<int:test_id>/answer", methods=["POST"])
@login_required
def record_answer(test_id):
    """Foydalanuvchi bitta savolga javob belgilaganda (yoki o'zgartirganda)
    darhol saqlaydi — shu orqali admin panelida real vaqtda kuzatish mumkin."""
    db = get_db()
    data = request.get_json(silent=True) or request.form

    try:
        question_id = int(data.get("question_id"))
    except (TypeError, ValueError):
        return {"ok": False, "error": "invalid_question"}, 400

    selected = (data.get("selected_option") or "").strip().upper()
    if selected not in ("A", "B", "C", "D"):
        selected = None

    with db.cursor() as cur:
        cur.execute(
            "SELECT id, status FROM results WHERE user_id = %s AND test_id = %s",
            (g.user["id"], test_id),
        )
        result = cur.fetchone()
        if not result or result["status"] != "in_progress":
            return {"ok": False, "error": "no_active_attempt"}, 400

        cur.execute(
            "SELECT id, correct_option FROM questions WHERE id = %s AND test_id = %s",
            (question_id, test_id),
        )
        question = cur.fetchone()
        if not question:
            return {"ok": False, "error": "invalid_question"}, 400

        if selected is None:
            cur.execute(
                "DELETE FROM answers WHERE result_id = %s AND question_id = %s",
                (result["id"], question_id),
            )
        else:
            is_correct = 1 if selected == question["correct_option"] else 0
            cur.execute(
                "INSERT INTO answers (result_id, question_id, selected_option, is_correct) "
                "VALUES (%s, %s, %s, %s) "
                "ON DUPLICATE KEY UPDATE selected_option = VALUES(selected_option), "
                "is_correct = VALUES(is_correct)",
                (result["id"], question_id, selected, is_correct),
            )
        db.commit()

    return {"ok": True}


@bp.route("/test/<int:test_id>/submit", methods=["POST"])
@login_required
def submit_test(test_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute(
            "SELECT * FROM results WHERE user_id = %s AND test_id = %s",
            (g.user["id"], test_id),
        )
        result = cur.fetchone()

    if not result or result["status"] == "finished":
        return redirect(url_for("user.test_result", test_id=test_id))

    answers = {}
    for key, value in request.form.items():
        if key.startswith("q_") and value:
            try:
                qid = int(key[2:])
            except ValueError:
                continue
            answers[qid] = value

    _finish_attempt(db, result, answers)
    flash("Test muvaffaqiyatli topshirildi!", "success")
    return redirect(url_for("user.test_result", test_id=test_id))


@bp.route("/test/<int:test_id>/result")
@login_required
def test_result(test_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tests WHERE id = %s", (test_id,))
        test = cur.fetchone()
        cur.execute(
            "SELECT * FROM results WHERE user_id = %s AND test_id = %s",
            (g.user["id"], test_id),
        )
        result = cur.fetchone()
        if not test or not result or result["status"] != "finished":
            flash("Siz bu testni hali topshirmagansiz.", "error")
            return redirect(url_for("user.dashboard"))

        cur.execute(
            "SELECT COUNT(*) AS better_count FROM results "
            "WHERE test_id = %s AND status = 'finished' AND "
            "(score > %s OR (score = %s AND time_spent_seconds < %s))",
            (test_id, result["score"], result["score"], result["time_spent_seconds"]),
        )
        rank = cur.fetchone()["better_count"] + 1

        cur.execute(
            "SELECT id, question_text, option_a, option_b, option_c, option_d, correct_option "
            "FROM questions WHERE test_id = %s ORDER BY order_no, id",
            (test_id,),
        )
        questions = cur.fetchall()

        cur.execute(
            "SELECT question_id, selected_option, is_correct FROM answers WHERE result_id = %s",
            (result["id"],),
        )
        my_answers = {a["question_id"]: a for a in cur.fetchall()}

    return render_template(
        "test_result.html",
        test=test,
        result=result,
        rank=rank,
        questions=questions,
        my_answers=my_answers,
    )


@bp.route("/leaderboard/<int:test_id>")
@login_required
def leaderboard(test_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM tests WHERE id = %s", (test_id,))
        test = cur.fetchone()
        if not test:
            flash("Test topilmadi.", "error")
            return redirect(url_for("user.dashboard"))
        cur.execute(
            "SELECT u.full_name, u.username, r.score, r.total_points, r.time_spent_seconds, r.user_id "
            "FROM results r JOIN users u ON u.id = r.user_id "
            "WHERE r.test_id = %s AND r.status = 'finished' "
            "ORDER BY r.score DESC, r.time_spent_seconds ASC",
            (test_id,),
        )
        rows = cur.fetchall()
    return render_template("leaderboard.html", test=test, rows=rows)


@bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    db = get_db()
    if request.method == "POST" and request.form.get("action") == "generate_code":
        code = secrets.token_hex(4)
        with db.cursor() as cur:
            cur.execute(
                "UPDATE users SET telegram_link_code = %s WHERE id = %s",
                (code, g.user["id"]),
            )
        db.commit()
        flash("Havola yaratildi, pastdagi tugmani bosing.", "success")
        return redirect(url_for("user.profile"))

    with db.cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id = %s", (g.user["id"],))
        user = cur.fetchone()

    return render_template(
        "profile.html", user=user, bot_username=Config.TELEGRAM_BOT_USERNAME
    )
