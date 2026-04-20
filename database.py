import os
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager

SUPABASE_DB_URL = os.environ.get("SUPABASE_DB_URL", "")

@contextmanager
def get_conn():
    conn = psycopg2.connect(SUPABASE_DB_URL, cursor_factory=RealDictCursor)
    try:
        yield conn
    finally:
        conn.close()

def init_db():
    """Create tables if they don't exist. Called once on bot startup."""
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS users (
                        user_id BIGINT PRIMARY KEY,
                        username TEXT,
                        banned BOOLEAN DEFAULT FALSE,
                        session_string TEXT,
                        silent BOOLEAN DEFAULT FALSE,
                        tier TEXT DEFAULT 'free',
                        daily_bytes BIGINT DEFAULT 0,
                        last_used_date DATE DEFAULT CURRENT_DATE,
                        premium_expiry TIMESTAMP DEFAULT NULL
                    );
                """)
                # Ensure columns exist if upgrading from an older schema
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS session_string TEXT;")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS silent BOOLEAN DEFAULT FALSE;")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS tier TEXT DEFAULT 'free';")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS daily_bytes BIGINT DEFAULT 0;")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS last_used_date DATE DEFAULT CURRENT_DATE;")
                cur.execute("ALTER TABLE users ADD COLUMN IF NOT EXISTS premium_expiry TIMESTAMP DEFAULT NULL;")
                
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
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS premium_keys (
                        key_string TEXT PRIMARY KEY,
                        tier TEXT NOT NULL,
                        days INT NOT NULL,
                        used_by BIGINT DEFAULT NULL,
                        used_at TIMESTAMP DEFAULT NULL
                    );
                """)
                
                cur.execute("""
                    CREATE TABLE IF NOT EXISTS link_cache (
                        link_hash TEXT PRIMARY KEY,
                        log_msg_id BIGINT NOT NULL
                    );
                """)
            conn.commit()
        print("✅ Database initialized (Supabase PostgreSQL)")
    except Exception as e:
        # Mask the password in the URL for safe logging
        masked_url = SUPABASE_DB_URL
        if "@" in SUPABASE_DB_URL:
            # Format: postgresql://[user]:[pass]@[host]:[port]/[db]
            prefix, rest = SUPABASE_DB_URL.split(":", 1)
            if "//" in rest:
                proto, remaining = rest.split("//", 1)
                if "@" in remaining:
                    credentials, host_info = remaining.split("@", 1)
                    if ":" in credentials:
                        user, pw = credentials.split(":", 1)
                        masked_url = f"{prefix}:{proto}//{user}:***@{host_info}"
                    else:
                        masked_url = f"{prefix}:{proto}//{credentials}@{host_info}"
        
        print(f"❌ DATABASE ERROR: {e}")
        print(f"🔗 Attempted URL: {masked_url}")
        raise e

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

def set_silent(user_id: int, status: bool) -> bool:
    """Toggle silent mode for a user."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "UPDATE users SET silent = %s WHERE user_id = %s",
                (status, user_id)
            )
            updated = cur.rowcount
        conn.commit()
    return updated > 0

def get_silent(user_id: int) -> bool:
    """Check if the user has silent mode enabled."""
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT silent FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if row and row["silent"]:
                return True
    return False

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

# --- PREMIUM & QUOTA FUNCTIONS ---
from datetime import datetime
import config

def check_and_update_limit(user_id: int, file_size_bytes: int) -> tuple[bool, str]:
    """Checks if a download is allowed for the user's tier. Updates daily_bytes if allowed.
    Returns (True, "") if allowed, or (False, "reason string") if denied."""
    
    # 0. Owner God Mode (0.1% Bypass)
    if user_id in config.OWNER_IDS:
        return True, ""
        
    with get_conn() as conn:
        with conn.cursor() as cur:
            # 1. Clear old daily limits and downgrade expired premium internally
            cur.execute("""
                UPDATE users 
                SET daily_bytes = 0 
                WHERE last_used_date < CURRENT_DATE;
            """)
            cur.execute("""
                UPDATE users
                SET last_used_date = CURRENT_DATE
                WHERE user_id = %s;
            """, (user_id,))
            
            cur.execute("""
                UPDATE users
                SET tier = 'free', premium_expiry = NULL
                WHERE premium_expiry < NOW() AND tier != 'free';
            """)
            
            # 2. Get user tier and usage
            cur.execute("SELECT tier, daily_bytes FROM users WHERE user_id = %s", (user_id,))
            row = cur.fetchone()
            if not row:
                return False, "User not found in DB. Please hit /start again."
                
            tier = row["tier"]
            daily_bytes = row["daily_bytes"]
            
            # 3. Check Free Limits
            if tier == 'free':
                if file_size_bytes > 100 * 1024 * 1024:
                    return False, "File exceeds **100MB** single-file limit for Free users."
                if daily_bytes + file_size_bytes > 500 * 1024 * 1024:
                    return False, "This file puts you over your **500MB** daily Free limit."
            
            # 4. If approved, add bytes
            cur.execute("UPDATE users SET daily_bytes = daily_bytes + %s WHERE user_id = %s", (file_size_bytes, user_id))
        conn.commit()
    return True, ""

def get_user_plan(user_id: int) -> dict:
    with get_conn() as conn:
        with conn.cursor() as cur:
            # Clean expired first
            cur.execute("UPDATE users SET tier = 'free', premium_expiry = NULL WHERE premium_expiry < NOW() AND tier != 'free'")
            
            cur.execute("SELECT tier, daily_bytes, premium_expiry FROM users WHERE user_id = %s", (user_id,))
            return cur.fetchone() or {"tier": "free", "daily_bytes": 0, "premium_expiry": None}

def generate_key(key_string: str, tier: str, days: int):
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("INSERT INTO premium_keys (key_string, tier, days) VALUES (%s, %s, %s)", (key_string, tier, days))
        conn.commit()

def redeem_key(user_id: int, key_string: str) -> tuple[bool, str]:
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT tier, days, used_by FROM premium_keys WHERE key_string = %s", (key_string,))
            key_data = cur.fetchone()
            if not key_data:
                return False, "Invalid key."
            if key_data["used_by"]:
                return False, "Key has already been used."
            
            tier = key_data["tier"]
            days = key_data["days"]
            
            # Apply key
            cur.execute("UPDATE premium_keys SET used_by = %s, used_at = NOW() WHERE key_string = %s", (user_id, key_string))
            
            # Update user plan
            cur.execute("""
                UPDATE users 
                SET tier = %s, 
                    premium_expiry = COALESCE(premium_expiry, NOW()) + floor(%s * 86400) * interval '1 second'
                WHERE user_id = %s
            """, (tier, days, user_id))
            
            
        conn.commit()
    return True, f"Successfully upgraded to **{tier.title()} Plan** for {days} days!"

# --- ZERO-BYTE LINK CACHING (0.1% HACK) ---

import hashlib

def _hash_link(chat_id, msg_id):
    raw = f"{chat_id}_{msg_id}"
    return hashlib.md5(raw.encode()).hexdigest()

def get_cached_link(chat_id, msg_id) -> int:
    """Returns the message ID in the log channel if it exists, else None."""
    link_hash = _hash_link(chat_id, msg_id)
    with get_conn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT log_msg_id FROM link_cache WHERE link_hash = %s", (link_hash,))
            row = cur.fetchone()
            if row:
                return row["log_msg_id"]
    return None

def save_cached_link(chat_id, msg_id, log_msg_id: int):
    """Saves a successfully logged file into the Zero-Byte cache."""
    link_hash = _hash_link(chat_id, msg_id)
    try:
        with get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute("""
                    INSERT INTO link_cache (link_hash, log_msg_id) 
                    VALUES (%s, %s)
                    ON CONFLICT (link_hash) DO NOTHING
                """, (link_hash, log_msg_id))
            conn.commit()
    except Exception as e:
        print(f"Failed to cache link: {e}")
