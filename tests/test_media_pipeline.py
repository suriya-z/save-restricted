import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from media_pipeline import MediaPipeline

@pytest.fixture
def mock_pipeline():
    sent_video_mock = MagicMock(id=777)
    sent_video_mock.copy = AsyncMock(return_value=MagicMock(id=9999))

    bot_client = MagicMock()
    bot_client.copy_message = AsyncMock(return_value=MagicMock(id=999))
    bot_client.send_photo = AsyncMock(return_value=MagicMock(id=888))
    bot_client.send_video = AsyncMock(return_value=sent_video_mock)
    bot_client.send_document = AsyncMock(return_value=MagicMock(id=666))

    user_client = MagicMock()
    user_client.download_media = AsyncMock(return_value="fake_path.mp4")

    swarm_pool = MagicMock()
    swarm_pool.acquire_worker.return_value = user_client
    swarm_pool.get_all_pool_clients.return_value = [user_client]
    swarm_pool.get_concurrency_limit.return_value = 5

    cache_adapter = MagicMock()
    cache_adapter.get_cached_link = MagicMock(return_value=None)
    cache_adapter.save_cached_link = MagicMock()

    pipeline = MediaPipeline(
        bot_client=bot_client,
        user_client=user_client,
        swarm_pool=swarm_pool,
        cache_adapter=cache_adapter,
        log_channel=-1001234567890
    )
    return pipeline, bot_client, user_client, cache_adapter

@pytest.mark.asyncio
async def test_cache_hit_triggers_zero_byte_cloud_copy(mock_pipeline):
    pipeline, bot_client, user_client, cache_adapter = mock_pipeline
    cache_adapter.get_cached_link.return_value = 4242  # Cache hit!

    source_msg = MagicMock()
    source_msg.chat.id = -1005555
    source_msg.id = 123
    source_msg.photo = MagicMock()
    source_msg.video = None

    sent = await pipeline.deliver_media(
        source_msg=source_msg,
        target_chat_id=111,
        user_id=222,
        is_admin=True
    )

    # Must invoke copy_message directly from log_channel
    bot_client.copy_message.assert_awaited_once_with(
        chat_id=111,
        from_chat_id=-1001234567890,
        message_id=4242
    )
    # Must NOT download anything
    user_client.download_media.assert_not_called()
    assert sent.id == 999

@pytest.mark.asyncio
async def test_ram_streaming_invoked_for_payloads_under_threshold(mock_pipeline):
    pipeline, bot_client, user_client, _ = mock_pipeline

    source_msg = MagicMock()
    source_msg.chat.id = -1005555
    source_msg.id = 124
    source_msg.photo = None
    source_msg.document = None
    source_msg.audio = None
    source_msg.voice = None
    source_msg.video = MagicMock(file_size=20 * 1024 * 1024, duration=60, width=1920, height=1080, thumbs=None)
    source_msg.caption = "Test Video"

    with patch("media_pipeline.download_media_adaptive", new=AsyncMock(return_value="in_memory_buf")) as mock_adaptive, \
         patch("media_pipeline.cleanup_media") as mock_cleanup:

        sent = await pipeline.deliver_media(
            source_msg=source_msg,
            target_chat_id=111,
            user_id=222,
            is_admin=True
        )

        mock_adaptive.assert_awaited_once()
        bot_client.send_video.assert_awaited_once()
        mock_cleanup.assert_called()
        assert sent.id == 777
