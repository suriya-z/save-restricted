import pytest
from access_engine import AccessEngine, InMemoryAccessAdapter

@pytest.fixture
def in_memory_engine():
    adapter = InMemoryAccessAdapter()
    engine = AccessEngine(adapter=adapter, owner_ids=[999999])
    return engine, adapter

def test_owner_bypasses_all_restrictions(in_memory_engine):
    engine, _ = in_memory_engine
    owner_id = 999999

    # Owner can execute album, dump, and unlimited single downloads
    allowed, reason = engine.can_execute(owner_id, feature="album")
    assert allowed is True
    assert reason == ""

    allowed, reason = engine.can_execute(owner_id, feature="dump")
    assert allowed is True

    allowed, reason = engine.can_execute(owner_id, feature="single", file_size_bytes=2 * 1024 * 1024 * 1024)
    assert allowed is True

def test_free_user_blocked_from_exclusive_features(in_memory_engine):
    engine, adapter = in_memory_engine
    user_id = 1001
    adapter.set_user(user_id, tier="free", daily_bytes=0)

    # Album requires Gold
    allowed, reason = engine.can_execute(user_id, feature="album")
    assert allowed is False
    assert "Gold" in reason

    # Dump requires Gold
    allowed, reason = engine.can_execute(user_id, feature="dump")
    assert allowed is False
    assert "Gold" in reason

def test_free_user_file_and_daily_limits(in_memory_engine):
    engine, adapter = in_memory_engine
    user_id = 1002
    adapter.set_user(user_id, tier="free", daily_bytes=0)

    # Single file > 100MB blocked
    allowed, reason = engine.can_execute(user_id, feature="single", file_size_bytes=105 * 1024 * 1024)
    assert allowed is False
    assert "100MB" in reason

    # Single file 50MB allowed
    allowed, reason = engine.can_execute(user_id, feature="single", file_size_bytes=50 * 1024 * 1024)
    assert allowed is True

    # Record 480MB usage
    engine.record_usage(user_id, 480 * 1024 * 1024)

    # Further 30MB exceeds 500MB daily quota
    allowed, reason = engine.can_execute(user_id, feature="single", file_size_bytes=30 * 1024 * 1024)
    assert allowed is False
    assert "500MB" in reason

def test_gold_user_allowed_features_and_unlimited_quota(in_memory_engine):
    engine, adapter = in_memory_engine
    user_id = 2001
    adapter.set_user(user_id, tier="gold", daily_bytes=0)

    allowed, _ = engine.can_execute(user_id, feature="album")
    assert allowed is True

    allowed, _ = engine.can_execute(user_id, feature="dump")
    assert allowed is True

    allowed, _ = engine.can_execute(user_id, feature="single", file_size_bytes=1024 * 1024 * 1024)
    assert allowed is True
