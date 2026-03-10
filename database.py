import json
import os

DB_FILE = "database.json"

def load_db():
    if not os.path.exists(DB_FILE):
        return {"users": {}, "downloads": 0}
    try:
        with open(DB_FILE, "r") as f:
            return json.load(f)
    except:
        return {"users": {}, "downloads": 0}

def save_db(db_data):
    with open(DB_FILE, "w") as f:
        json.dump(db_data, f, indent=4)

def add_user(user_id: int, username: str):
    db = load_db()
    user_id_str = str(user_id)
    if user_id_str not in db["users"]:
        db["users"][user_id_str] = {
            "username": username,
            "banned": False
        }
        save_db(db)

def is_banned(user_id: int) -> bool:
    db = load_db()
    user_id_str = str(user_id)
    if user_id_str in db["users"] and db["users"][user_id_str].get("banned", False):
        return True
    return False

def set_ban(user_id: int, status: bool) -> bool:
    db = load_db()
    user_id_str = str(user_id)
    if user_id_str in db["users"]:
        db["users"][user_id_str]["banned"] = status
        save_db(db)
        return True
    return False

def increment_downloads():
    db = load_db()
    db["downloads"] = db.get("downloads", 0) + 1
    save_db(db)

def get_stats():
    db = load_db()
    return len(db["users"]), db.get("downloads", 0)

def get_all_users():
    db = load_db()
    return db["users"]
