import sqlite3

DB_NAME = "database.db"


def init_db():
    """Bazani va jadvallarni yaratadi (agar mavjud bo'lmasa)."""
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            total_score INTEGER DEFAULT 0
        )
    """)
    cur.execute("""
        CREATE TABLE IF NOT EXISTS results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            subject_id TEXT,
            lesson_id INTEGER,
            score INTEGER,
            total_questions INTEGER,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    conn.commit()
    conn.close()


def add_user(user_id, full_name):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT user_id FROM users WHERE user_id=?", (user_id,))
    if not cur.fetchone():
        cur.execute(
            "INSERT INTO users (user_id, full_name, total_score) VALUES (?, ?, 0)",
            (user_id, full_name),
        )
        conn.commit()
    conn.close()


def save_result(user_id, subject_id, lesson_id, score, total_questions):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO results (user_id, subject_id, lesson_id, score, total_questions) VALUES (?,?,?,?,?)",
        (user_id, subject_id, lesson_id, score, total_questions),
    )
    cur.execute(
        "UPDATE users SET total_score = total_score + ? WHERE user_id=?",
        (score, user_id),
    )
    conn.commit()
    conn.close()


def get_user_stats(user_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute("SELECT full_name, total_score FROM users WHERE user_id=?", (user_id,))
    user = cur.fetchone()
    cur.execute("SELECT COUNT(*) FROM results WHERE user_id=?", (user_id,))
    lessons_done = cur.fetchone()[0]
    conn.close()
    return user, lessons_done


def get_leaderboard(limit=10):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT full_name, total_score FROM users ORDER BY total_score DESC LIMIT ?",
        (limit,),
    )
    rows = cur.fetchall()
    conn.close()
    return rows


def get_completed_lessons(user_id, subject_id):
    conn = sqlite3.connect(DB_NAME)
    cur = conn.cursor()
    cur.execute(
        "SELECT DISTINCT lesson_id FROM results WHERE user_id=? AND subject_id=?",
        (user_id, subject_id),
    )
    rows = [r[0] for r in cur.fetchall()]
    conn.close()
    return rows