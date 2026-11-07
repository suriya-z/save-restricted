import pytest
import os
from unittest.mock import MagicMock, AsyncMock, patch
import helpers
import memory_injector
import hacks
import socket

def test_helpers_is_owner_executes_cleanly():
    with patch("config.OWNER_IDS", [12345]):
        assert helpers.is_owner(12345) is True
        assert helpers.is_owner(99999) is False

def test_hacks_does_not_monkeypatch_socket_constructor():
    # Verify standard socket constructor is untouched
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        assert not isinstance(s, getattr(hacks, "FastSocket", type(None)))
    finally:
        s.close()

@pytest.mark.asyncio
async def test_hydra_downloader_rejects_corrupted_shards():
    mock_client = MagicMock()
    downloader = memory_injector.HydraDownloader(apps=[mock_client])
    
    # Mock message with 10MB file
    mock_msg = MagicMock()
    mock_media = MagicMock()
    mock_media.file_size = 10 * 1024 * 1024
    mock_media.file_id = "test_file_id"
    mock_media.file_name = "../traversal_test.mp4"
    mock_msg.photo = None
    mock_msg.video = mock_media
    mock_msg.document = None
    mock_msg.audio = None
    mock_msg.voice = None
    
    # Force get_shard to return empty bytes (simulating failed retries)
    downloader.get_shard = AsyncMock(return_value=(0, b""))
    
    with patch("memory_injector.FileId.decode") as mock_decode:
        mock_file_obj = MagicMock()
        mock_file_obj.file_type = MagicMock()
        mock_decode.return_value = mock_file_obj
        
        with pytest.raises(IOError, match="Hydra download incomplete"):
            await downloader.download(mock_msg)
    
    # Verify traversal was sanitized and no file was left in root
    assert not os.path.exists("traversal_test.mp4")
