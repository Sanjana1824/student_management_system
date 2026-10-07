"""Student Management System - Flask + SQLite REST API with a dashboard UI."""
import os
import re
import sqlite3
from flask import Flask, jsonify, render_template, request, g

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DB_PATH = os.path.join(BASE_DIR, "students.db")

app = Flask(__name__)

SCHEMA = """
CREATE TABLE IF NOT EXISTS students (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    roll_no     TEXT    NOT NULL UNIQUE,
    name        TEXT    NOT NULL,
    email       TEXT    NOT NULL UNIQUE,
    department  TEXT    NOT NULL,
    year        INTEGER NOT NULL CHECK (year BETWEEN 1 AND 4),
    gpa         REAL    NOT NULL CHECK (gpa BETWEEN 0 AND 10),
    created_at  TEXT    DEFAULT CURRENT_TIMESTAMP
);
"""

SEED = [
    ("CS101", "Aarav Sharma", "aarav@college.edu", "Computer Science", 3, 8.7),
    ("CS102", "Diya Reddy", "diya@college.edu", "Computer Science", 2, 9.1),
    ("EC201", "Rohan Mehta", "rohan@college.edu", "Electronics", 4, 7.4),
    ("ME301", "Sneha Iyer", "sneha@college.edu", "Mechanical", 1, 6.8),
    ("CV401", "Karthik Rao", "karthik@college.edu", "Civil", 3, 7.9),
    ("EE501", "Ananya Das", "ananya@college.edu", "Electrical", 2, 8.2),
    ("CS103", "Vikram Singh", "vikram@college.edu", "Computer Science", 4, 5.9),
    ("EC202", "Meera Nair", "meera@college.edu", "Electronics", 1, 9.4),
]


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(DB_PATH)
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_exc):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    with sqlite3.connect(DB_PATH) as db:
        db.executescript(SCHEMA)
        if db.execute("SELECT COUNT(*) FROM students").fetchone()[0] == 0:
            db.executemany(
                "INSERT INTO students (roll_no, name, email, department, year, gpa) "
                "VALUES (?, ?, ?, ?, ?, ?)", SEED)


def validate(data):
    """Return (clean_dict, error_message)."""
    try:
        clean = {
            "roll_no": str(data.get("roll_no", "")).strip().upper(),
            "name": str(data.get("name", "")).strip(),
            "email": str(data.get("email", "")).strip().lower(),
            "department": str(data.get("department", "")).strip(),
            "year": int(data.get("year")),
            "gpa": round(float(data.get("gpa")), 2),
        }
    except (TypeError, ValueError):
        return None, "Year and GPA must be numbers."
    if not all([clean["roll_no"], clean["name"], clean["email"], clean["department"]]):
        return None, "Roll number, name, email and department are required."
    if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", clean["email"]):
        return None, "Enter a valid email address."
    if not 1 <= clean["year"] <= 4:
        return None, "Year must be between 1 and 4."
    if not 0 <= clean["gpa"] <= 10:
        return None, "GPA must be between 0 and 10."
    return clean, None


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/students", methods=["GET"])
def list_students():
    q = request.args.get("q", "").strip()
    dept = request.args.get("department", "").strip()
    sql, params = "SELECT * FROM students WHERE 1=1", []
    if q:
        sql += " AND (name LIKE ? OR roll_no LIKE ? OR email LIKE ?)"
        params += [f"%{q}%"] * 3
    if dept:
        sql += " AND department = ?"
        params.append(dept)
    sql += " ORDER BY roll_no"
    rows = get_db().execute(sql, params).fetchall()
    return jsonify([dict(r) for r in rows])


@app.route("/api/students", methods=["POST"])
def create_student():
    clean, err = validate(request.get_json(silent=True) or {})
    if err:
        return jsonify(error=err), 400
    try:
        db = get_db()
        cur = db.execute(
            "INSERT INTO students (roll_no, name, email, department, year, gpa) "
            "VALUES (:roll_no, :name, :email, :department, :year, :gpa)", clean)
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="Roll number or email already exists."), 409
    return jsonify(id=cur.lastrowid, **clean), 201


@app.route("/api/students/<int:sid>", methods=["PUT"])
def update_student(sid):
    clean, err = validate(request.get_json(silent=True) or {})
    if err:
        return jsonify(error=err), 400
    try:
        db = get_db()
        cur = db.execute(
            "UPDATE students SET roll_no=:roll_no, name=:name, email=:email, "
            "department=:department, year=:year, gpa=:gpa WHERE id=:id",
            {**clean, "id": sid})
        db.commit()
    except sqlite3.IntegrityError:
        return jsonify(error="Roll number or email already exists."), 409
    if cur.rowcount == 0:
        return jsonify(error="Student not found."), 404
    return jsonify(id=sid, **clean)


@app.route("/api/students/<int:sid>", methods=["DELETE"])
def delete_student(sid):
    db = get_db()
    cur = db.execute("DELETE FROM students WHERE id = ?", (sid,))
    db.commit()
    if cur.rowcount == 0:
        return jsonify(error="Student not found."), 404
    return jsonify(deleted=sid)


@app.route("/api/stats")
def stats():
    db = get_db()
    total, avg = db.execute("SELECT COUNT(*), COALESCE(AVG(gpa),0) FROM students").fetchone()
    top = db.execute("SELECT name, gpa FROM students ORDER BY gpa DESC LIMIT 1").fetchone()
    by_dept = db.execute(
        "SELECT department, COUNT(*) AS count FROM students GROUP BY department ORDER BY count DESC").fetchall()
    by_year = db.execute(
        "SELECT year, COUNT(*) AS count FROM students GROUP BY year ORDER BY year").fetchall()
    bands = db.execute("""
        SELECT SUM(gpa >= 9) AS a, SUM(gpa >= 8 AND gpa < 9) AS b,
               SUM(gpa >= 7 AND gpa < 8) AS c, SUM(gpa >= 6 AND gpa < 7) AS d,
               SUM(gpa < 6) AS e FROM students""").fetchone()
    return jsonify(
        total=total, avg_gpa=round(avg, 2),
        top_student=dict(top) if top else None,
        departments=len(by_dept),
        by_department=[dict(r) for r in by_dept],
        by_year=[dict(r) for r in by_year],
        gpa_bands=[bands[k] or 0 for k in ("a", "b", "c", "d", "e")],
    )


@app.route("/health")
def health():
    return jsonify(status="ok")


init_db()

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=False)
