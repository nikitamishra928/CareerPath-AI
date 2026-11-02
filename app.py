
import os
import sqlite3
from functools import wraps
from urllib.parse import quote_plus

from flask import (
    Flask,
    flash,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for
)

from werkzeug.security import (
    check_password_hash,
    generate_password_hash
)

from model.recommendation import (
    get_recommendations,
    get_career,
    get_skill_gap
)


app = Flask(__name__)

app.secret_key = os.getenv(
    "SECRET_KEY",
    "local-development-key-change-before-deployment"
)

DB_PATH = os.path.join(app.root_path, "careerpath.db")


# ==========================================
# DATABASE CONNECTION
# ==========================================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def init_db():
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS students (
            student_id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            education TEXT DEFAULT '',
            interests TEXT DEFAULT '',
            skills TEXT DEFAULT '',
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS learning_progress (
            progress_id INTEGER PRIMARY KEY AUTOINCREMENT,
            student_id INTEGER NOT NULL,
            career_title TEXT NOT NULL,
            skill_name TEXT NOT NULL,
            status TEXT NOT NULL DEFAULT 'Not Started',
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

            UNIQUE(student_id, career_title, skill_name),

            FOREIGN KEY(student_id)
                REFERENCES students(student_id)
                ON DELETE CASCADE
        );
        """)


# ==========================================
# LOGIN PROTECTION
# ==========================================

def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):

        if "student_id" not in session:
            flash(
                "Please log in to continue.",
                "warning"
            )
            return redirect(url_for("login"))

        return view(*args, **kwargs)

    return wrapped


# ==========================================
# CURRENT STUDENT
# ==========================================

def current_student():

    with get_db() as conn:

        row = conn.execute(
            """
            SELECT
                student_id,
                name,
                email,
                education,
                interests,
                skills
            FROM students
            WHERE student_id = ?
            """,
            (session["student_id"],)
        ).fetchone()

        return dict(row) if row else None


# ==========================================
# LEARNING RESOURCES
# ==========================================

def get_learning_resources(skill):

    skill_query = quote_plus(skill)

    return {
        "description": (
            f"Build your knowledge of {skill} through "
            "structured lessons, practical examples, "
            "and hands-on exercises."
        ),

        "video_url": (
            "https://www.youtube.com/results?search_query="
            f"{skill_query}+tutorial+for+beginners"
        ),

        "article_url": (
            "https://www.google.com/search?q="
            f"{skill_query}+official+documentation+tutorial"
        )
    }


# ==========================================
# HOME PAGE
# ==========================================

@app.route("/")
def index():

    if session.get("student_id"):
        return redirect(url_for("dashboard"))

    return render_template("index.html")


# ==========================================
# REGISTRATION
# ==========================================

@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "POST":

        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        if not name or not email or len(password) < 8:

            flash(
                "Enter your name and email, and use a password with at least 8 characters.",
                "danger"
            )

            return render_template("register.html")

        try:

            with get_db() as conn:

                conn.execute(
                    """
                    INSERT INTO students
                    (name, email, password_hash)
                    VALUES (?, ?, ?)
                    """,
                    (
                        name,
                        email,
                        generate_password_hash(password)
                    )
                )

            flash(
                "Account created. You can now sign in.",
                "success"
            )

            return redirect(url_for("login"))

        except sqlite3.IntegrityError:

            flash(
                "That email address is already registered.",
                "warning"
            )

    return render_template("register.html")


# ==========================================
# LOGIN
# ==========================================

@app.route("/login", methods=["GET", "POST"])
def login():

    if request.method == "POST":

        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")

        with get_db() as conn:

            row = conn.execute(
                """
                SELECT student_id, name, password_hash
                FROM students
                WHERE email = ?
                """,
                (email,)
            ).fetchone()

            student = dict(row) if row else None

        if student and check_password_hash(
            student["password_hash"],
            password
        ):

            session.clear()

            session["student_id"] = student["student_id"]
            session["student_name"] = student["name"]

            return redirect(url_for("dashboard"))

        flash(
            "Email or password is incorrect.",
            "danger"
        )

    return render_template("login.html")


# ==========================================
# LOGOUT
# ==========================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been signed out.",
        "success"
    )

    return redirect(url_for("index"))


# ==========================================
# STUDENT PROFILE
# ==========================================

@app.route("/profile", methods=["GET", "POST"])
@login_required
def profile():

    if request.method == "POST":

        values = (
            request.form.get("education", "").strip(),
            request.form.get("interests", "").strip(),
            request.form.get("skills", "").strip(),
            session["student_id"]
        )

        with get_db() as conn:

            conn.execute(
                """
                UPDATE students
                SET education = ?,
                    interests = ?,
                    skills = ?
                WHERE student_id = ?
                """,
                values
            )

        flash(
            "Your profile has been updated.",
            "success"
        )

        return redirect(url_for("profile"))

    return render_template(
        "profile.html",
        student=current_student()
    )


# ==========================================
# DASHBOARD
# ==========================================

@app.route("/dashboard")
@login_required
def dashboard():

    student = current_student()

    with get_db() as conn:

        rows = conn.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM learning_progress
            WHERE student_id = ?
            GROUP BY status
            """,
            (session["student_id"],)
        ).fetchall()

        counts = {
            row["status"]: row["total"]
            for row in rows
        }

        recent = [
            dict(row)
            for row in conn.execute(
                """
                SELECT career_title, skill_name, status
                FROM learning_progress
                WHERE student_id = ?
                ORDER BY updated_at DESC
                LIMIT 6
                """,
                (session["student_id"],)
            ).fetchall()
        ]

    total = sum(counts.values())

    completed = counts.get("Completed", 0)

    percent = (
        round(completed / total * 100)
        if total else 0
    )

    recommendations = get_recommendations(
        student.get("skills") or "",
        student.get("interests") or ""
    )

    return render_template(
        "dashboard.html",
        student=student,
        counts=counts,
        total=total,
        completed=completed,
        percent=percent,
        recent=recent,
        recommendations=recommendations[:3]
    )


# ==========================================
# CAREER RECOMMENDATIONS
# ==========================================

@app.route("/recommendations")
@login_required
def recommendations():

    student = current_student()

    results = get_recommendations(
        student.get("skills") or "",
        student.get("interests") or ""
    )

    return render_template(
        "recommendations.html",
        student=student,
        recommendations=results
    )


# ==========================================
# SKILL ROADMAP
# ==========================================

@app.route("/roadmap")
@login_required
def roadmap():

    student = current_student()

    results = get_recommendations(
        student.get("skills") or "",
        student.get("interests") or ""
    )

    return render_template(
        "roadmap.html",
        student=student,
        recommendations=results
    )


# ==========================================
# CAREER DETAILS + LEARNING RESOURCES
# ==========================================

@app.route("/career/<slug>")
@login_required
def career_detail(slug):

    student = current_student()

    career = get_career(slug)

    if not career:

        flash(
            "Career path not found.",
            "warning"
        )

        return redirect(url_for("recommendations"))

    current_skills = [
        skill.strip()
        for skill in (
            student.get("skills") or ""
        ).split(",")
        if skill.strip()
    ]

    gap = get_skill_gap(
        current_skills,
        career["skills"]
    )

    with get_db() as conn:

        rows = conn.execute(
            """
            SELECT skill_name, status
            FROM learning_progress
            WHERE student_id = ?
            AND career_title = ?
            """,
            (
                session["student_id"],
                career["title"]
            )
        ).fetchall()

    saved = {
        row["skill_name"]: row["status"]
        for row in rows
    }

    resources = {}

    for item in gap:

        item["status"] = saved.get(
            item["skill"],
            "Not Started"
        )

        resources[item["skill"]] = get_learning_resources(
            item["skill"]
        )

    return render_template(
        "career.html",
        career=career,
        gap=gap,
        resources=resources
    )


# ==========================================
# UPDATE LEARNING PROGRESS
# ==========================================

@app.route("/progress/update", methods=["POST"])
@login_required
def update_progress():

    payload = request.get_json(silent=True) or {}

    career_title = str(
        payload.get("career_title", "")
    )[:120]

    skill_name = str(
        payload.get("skill_name", "")
    )[:100]

    status = payload.get("status")

    allowed = {
        "Not Started",
        "In Progress",
        "Completed"
    }

    from model.recommendation import CAREERS

    known = next(
        (
            career
            for career in CAREERS
            if career["title"] == career_title
            and skill_name in career["skills"]
        ),
        None
    )

    if not known or status not in allowed:

        return jsonify({
            "ok": False,
            "message": "Invalid skill or status."
        }), 400

    with get_db() as conn:

        conn.execute(
            """
            INSERT INTO learning_progress
            (
                student_id,
                career_title,
                skill_name,
                status
            )
            VALUES (?, ?, ?, ?)

            ON CONFLICT(
                student_id,
                career_title,
                skill_name
            )
            DO UPDATE SET
                status = excluded.status,
                updated_at = CURRENT_TIMESTAMP
            """,
            (
                session["student_id"],
                career_title,
                skill_name,
                status
            )
        )

    return jsonify({
        "ok": True,
        "message": "Progress saved."
    })


# ==========================================
# PROGRESS API
# ==========================================

@app.route("/api/progress")
@login_required
def progress_api():

    with get_db() as conn:

        rows = conn.execute(
            """
            SELECT status, COUNT(*) AS total
            FROM learning_progress
            WHERE student_id = ?
            GROUP BY status
            """,
            (session["student_id"],)
        ).fetchall()

    return jsonify({
        row["status"]: row["total"]
        for row in rows
    })


# ==========================================
# START APPLICATION
# ==========================================

if __name__ == "__main__":

    init_db()

    app.run(debug=True)

else:

    init_db()
