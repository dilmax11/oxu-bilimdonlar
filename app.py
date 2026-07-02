import os
from datetime import timedelta

from flask import Flask, g, redirect, url_for, render_template

import db
from auth_utils import load_logged_in_user
from routes.auth import bp as auth_bp
from routes.user import bp as user_bp
from routes.admin import bp as admin_bp
from config import Config


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    app.permanent_session_lifetime = timedelta(days=7)

    os.makedirs(Config.UPLOAD_FOLDER, exist_ok=True)

    db.init_app(app)

    app.register_blueprint(auth_bp)
    app.register_blueprint(user_bp)
    app.register_blueprint(admin_bp)

    app.before_request(load_logged_in_user)

    @app.route("/")
    def index():
        # Kirgan foydalanuvchilarni to'g'ridan-to'g'ri panellariga yo'naltir
        if g.user is not None:
            if g.user["role"] == "admin":
                return redirect(url_for("admin.dashboard"))
            return redirect(url_for("user.dashboard"))

        # Mehmonlar uchun ochiq landing sahifasi
        database = db.get_db()
        with database.cursor() as cur:
            # Platformadagi umumiy statistika
            cur.execute("SELECT COUNT(*) AS c FROM users WHERE role='user'")
            total_users = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) AS c FROM results WHERE status='finished'")
            total_attempts = cur.fetchone()["c"]

            cur.execute("SELECT COUNT(*) AS c FROM tests")
            total_tests = cur.fetchone()["c"]

            # Kelayotgan / rejadagi testlar (starts_at kelajakda YOKI hali boshlanmagan)
            cur.execute(
                "SELECT id, title, description, starts_at, ends_at, "
                "prize_info, time_limit_minutes, is_paid, price "
                "FROM tests "
                "WHERE is_active = 1 AND (starts_at IS NULL OR starts_at > NOW()) "
                "ORDER BY CASE WHEN starts_at IS NULL THEN 1 ELSE 0 END, starts_at ASC "
                "LIMIT 6"
            )
            upcoming = cur.fetchall()

            # Yakunlangan testlar va g'oliblar (eng ko'p ishtiroki bor testlar)
            cur.execute(
                "SELECT t.id, t.title, t.prize_info, t.ends_at, "
                "COUNT(r.id) AS participant_count, "
                "MAX(r.score) AS top_score, "
                "(SELECT q2.total_points FROM results q2 "
                " WHERE q2.test_id = t.id AND q2.status='finished' "
                " ORDER BY q2.finished_at DESC LIMIT 1) AS total_points "
                "FROM tests t "
                "JOIN results r ON r.test_id = t.id AND r.status = 'finished' "
                "WHERE t.is_active = 0 AND t.ends_at IS NOT NULL AND t.ends_at < NOW() "
                "GROUP BY t.id "
                "ORDER BY t.ends_at DESC "
                "LIMIT 6"
            )
            finished_tests = cur.fetchall()

            # Har bir yakunlangan test uchun g'olibni olish
            winners = {}
            for ft in finished_tests:
                cur.execute(
                    "SELECT u.full_name, u.username, r.score, r.total_points, r.time_spent_seconds "
                    "FROM results r JOIN users u ON u.id = r.user_id "
                    "WHERE r.test_id = %s AND r.status='finished' "
                    "ORDER BY r.score DESC, r.time_spent_seconds ASC LIMIT 1",
                    (ft["id"],),
                )
                winners[ft["id"]] = cur.fetchone()

            # So'nggi g'oliblar lenti (barcha testlardan)
            cur.execute(
                "SELECT u.full_name, t.title, r.score, r.total_points "
                "FROM results r "
                "JOIN users u ON u.id = r.user_id "
                "JOIN tests t ON t.id = r.test_id "
                "WHERE r.status = 'finished' "
                "ORDER BY r.finished_at DESC LIMIT 5"
            )
            recent_winners = cur.fetchall()

        return render_template(
            "landing.html",
            total_users=total_users,
            total_attempts=total_attempts,
            total_tests=total_tests,
            upcoming=upcoming,
            finished_tests=finished_tests,
            winners=winners,
            recent_winners=recent_winners,
        )

    @app.template_filter("mmss")
    def mmss_filter(total_seconds):
        if total_seconds is None:
            return "—"
        total_seconds = int(total_seconds)
        return f"{total_seconds // 60:02d}:{total_seconds % 60:02d}"

    return app


app = create_app()

if __name__ == "__main__":
    app.run(debug=Config.DEBUG, host="0.0.0.0", port=5000)
