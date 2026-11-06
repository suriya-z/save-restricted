import time
import random
from typing import Optional, Dict, List, Any

class SwarmPool:
    """
    Deep Swarm Pool Module.
    Encapsulates secondary user accounts, health tracking, FloodWait backoff,
    and concurrency distribution.
    """
    DEFAULT_STANDARD_CONCURRENCY = 5
    DEFAULT_OWNER_CONCURRENCY = 15

    def __init__(self, primary_client: Any, database_adapter: Optional[Any] = None):
        self.primary_client = primary_client
        self.db = database_adapter
        self.clients: Dict[int, Any] = {}
        self.backoff_until: Dict[int, float] = {}  # user_id -> timestamp

    def add_active_client(self, user_id: int, client: Any) -> None:
        self.clients[user_id] = client

    def active_worker_count(self) -> int:
        now = time.time()
        return sum(1 for uid in self.clients if self.backoff_until.get(uid, 0) <= now)

    def report_floodwait(self, client: Any, wait_seconds: int) -> None:
        now = time.time()
        for uid, c in self.clients.items():
            if c == client:
                self.backoff_until[uid] = now + wait_seconds
                break

    def acquire_worker(self) -> Any:
        now = time.time()
        available = [
            c for uid, c in self.clients.items()
            if self.backoff_until.get(uid, 0) <= now
        ]
        if not available:
            return self.primary_client
        return random.choice(available)

    def get_all_pool_clients(self) -> List[Any]:
        return [self.primary_client] + list(self.clients.values())

    def get_concurrency_limit(self, user_id: int, is_owner: bool = False) -> int:
        return self.DEFAULT_OWNER_CONCURRENCY if is_owner else self.DEFAULT_STANDARD_CONCURRENCY
