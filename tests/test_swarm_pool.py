import pytest
import time
from unittest.mock import MagicMock
from swarm_pool import SwarmPool

def test_acquire_worker_returns_fallback_when_empty():
    primary_client = MagicMock(name="primary_client")
    pool = SwarmPool(primary_client=primary_client)

    # Empty pool returns primary
    worker = pool.acquire_worker()
    assert worker == primary_client
    assert pool.active_worker_count() == 0

def test_register_and_acquire_workers():
    primary_client = MagicMock(name="primary_client")
    pool = SwarmPool(primary_client=primary_client)

    w1 = MagicMock(name="worker_1")
    w2 = MagicMock(name="worker_2")

    pool.add_active_client(101, w1)
    pool.add_active_client(102, w2)

    assert pool.active_worker_count() == 2

    # Multiple acquires rotate through available workers
    workers_seen = {pool.acquire_worker() for _ in range(10)}
    assert w1 in workers_seen
    assert w2 in workers_seen

def test_worker_floodwait_backoff():
    primary_client = MagicMock(name="primary_client")
    pool = SwarmPool(primary_client=primary_client)

    w1 = MagicMock(name="worker_1")
    pool.add_active_client(101, w1)

    # Report floodwait 60s
    pool.report_floodwait(w1, wait_seconds=60)

    # While backing off, acquire falls back to primary
    assert pool.acquire_worker() == primary_client

def test_concurrency_quota_for_owner_vs_standard():
    pool = SwarmPool(primary_client=MagicMock())
    assert pool.get_concurrency_limit(user_id=123, is_owner=False) == 5
    assert pool.get_concurrency_limit(user_id=999, is_owner=True) == 15
