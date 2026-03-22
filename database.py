import os
import psycopg2
from psycopg2.extras import RealDictCursor

SUPABASE_DB_URL = os.environ.get("SUPABASE_DB_URL", "")

def get_conn():
    return psycopg2.connect(SUPABASE_DB_URL, cursor_factory=RealDictCursor)

def init_db():
    """Create tables if they don't exist. Called once on bot startup."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id BIGINT PRIMARY KEY,
                    username TEXT,
                    banned BOOLEAN DEFAULT FALSE,
                    session_string TEXT
                );
            """)
            # Ensure session_string column exists if upgrading from an older schema
            try:
                cur.execute("ALTER TABLE users ADD COLUMN session_string TEXT;")
            except psycopg2.errors.DuplicateColumn:
                pass
            except Exception as e:
                # Rollback if transaction aborted
                conn.rollback()

            cur.execute("""
                CREATE TABLE IF NOT EXISTS stats (
                    key TEXT PRIMARY KEY,
                    value BIGINT DEFAULT 0
                );
            """)
            cur.execute("""
                INSERT INTO stats (key, value) VALUES ('downloads', 0)
                ON CONFLICT (key) DO NOTHING;
            """)
        conn.commit()
    print("✅ Database initialized (Supabase PostgreSQL)")

def add_user(user_id: int, username: str):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                INSERT INTO users (user_id, username, banned)
                VALUES (%s, %s, FALSE)
                ON CONFLICT (user_id) DO NOTHING;
            """, (user_id, username))
        conn.commit()

def save_session(user_id: int, session_string: str):
    """Save the Pyrogram session string to the user."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users SET session_string = %s WHERE user_id = %s
            """, (session_string, user_id))
        conn.commit()

def delete_session(user_id: int):
    """Remove the Pyrogram session string for the user."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("""
                UPDATE users SET session_string = NULL WHERE user_id = %s
            """, (user_id,))
        conn.commit()

def get_all_sessions() -> dict:
    """Return all non-null sessions as {user_id: session_string}."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, session_string FROM users WHERE session_string IS NOT NULL")
            rows = cur.fetchall()
            return {r["user_id"]: r["session_string"] for r in rows}

def is_banned(user_id: int) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT banned FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            return bool(row and row["banned"])

def set_ban(user_id: int, status: bool) -> bool:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET banned = %s WHERE user_id = %s",
                (status, user_id)
            )
            updated = cur.rowcount
        conn.commit()
    return updated > 0

def increment_downloads():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE stats SET value = value + 1 WHERE key = 'downloads'"
            )
        conn.commit()

def get_stats():
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT COUNT(*) AS cnt FROM users")
            users = cur.fetchone()["cnt"]
            cur.execute("SELECT value FROM stats WHERE key = 'downloads'")
            row = cur.fetchone()
            downloads = row["value"] if row else 0
    return users, downloads

def get_all_users() -> dict:
    """Returns {str(user_id): {username, banned}} — same interface as before."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT user_id, username, banned FROM users")
            rows = cur.fetchall()
    return {str(r["user_id"]): {"username": r["username"], "banned": r["banned"]} for r in rows}
