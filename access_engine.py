from typing import Protocol, Tuple, Optional, List

class AccessAdapter(Protocol):
    def get_user_state(self, user_id: int) -> dict: ...
    def add_user_bytes(self, user_id: int, byte_count: int) -> None: ...

class InMemoryAccessAdapter:
    def __init__(self):
        self.users = {}

    def set_user(self, user_id: int, tier: str = "free", daily_bytes: int = 0):
        self.users[user_id] = {
            "tier": tier,
            "daily_bytes": daily_bytes
        }

    def get_user_state(self, user_id: int) -> dict:
        return self.users.get(user_id, {"tier": "free", "daily_bytes": 0})

    def add_user_bytes(self, user_id: int, byte_count: int) -> None:
        if user_id not in self.users:
            self.set_user(user_id)
        self.users[user_id]["daily_bytes"] += byte_count

class PostgresAccessAdapter:
    def __init__(self, database_module):
        self.db = database_module

    def get_user_state(self, user_id: int) -> dict:
        return self.db.get_user_plan(user_id)

    def add_user_bytes(self, user_id: int, byte_count: int) -> None:
        with self.db.get_conn() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    "UPDATE users SET daily_bytes = daily_bytes + %s WHERE user_id = %s",
                    (byte_count, user_id)
                )
            conn.commit()

class AccessEngine:
    """
    Deep Access & Quota Seam.
    Encapsulates Owner God Mode, Free/Gold tier capabilities, and quota invariants.
    """
    FREE_SINGLE_FILE_LIMIT = 100 * 1024 * 1024  # 100MB
    FREE_DAILY_LIMIT = 500 * 1024 * 1024        # 500MB

    def __init__(self, adapter: AccessAdapter, owner_ids: Optional[List[int]] = None):
        self.adapter = adapter
        self.owner_ids = set(owner_ids or [])

    def is_owner(self, user_id: int) -> bool:
        return user_id in self.owner_ids

    def can_execute(self, user_id: int, feature: str, file_size_bytes: int = 0) -> Tuple[bool, str]:
        # 1. Permanent Owner God Mode Bypass
        if self.is_owner(user_id):
            return True, ""

        state = self.adapter.get_user_state(user_id)
        tier = state.get("tier", "free").lower()
        daily_bytes = state.get("daily_bytes", 0)

        # 2. Exclusive Feature Gates
        if feature in ["album", "dump"]:
            if tier != "gold":
                return False, f"The `{feature}` feature is reserved for Gold Members."
            return True, ""

        # 3. Quota Limits for Free Tier
        if tier == "free":
            if file_size_bytes > self.FREE_SINGLE_FILE_LIMIT:
                return False, "File exceeds 100MB single-file limit for Free users."
            if daily_bytes + file_size_bytes > self.FREE_DAILY_LIMIT:
                return False, "This download puts you over your 500MB daily Free limit."

        return True, ""

    def record_usage(self, user_id: int, file_size_bytes: int) -> None:
        if self.is_owner(user_id) or file_size_bytes <= 0:
            return
        self.adapter.add_user_bytes(user_id, file_size_bytes)
