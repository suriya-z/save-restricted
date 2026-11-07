import logging

# 1MB Chunk Override (Pyrogram transmission speed optimization)
try:
    from pyrogram.client import Client
    if hasattr(Client, "MAX_CHUNK_SIZE"):
        Client.MAX_CHUNK_SIZE = 1024 * 1024  # 1MB chunks
except Exception as e:
    logging.warning(f"Failed to inject 1MB Chunk Hack: {e}")
