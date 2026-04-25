import asyncio
import math
import time
import os
from pyrogram import Client
from pyrogram.raw.functions.upload import GetFile
from pyrogram.raw.types import InputDocumentFileLocation, InputPhotoFileLocation
from pyrogram.file_id import FileId, FileType
from pyrogram.errors import FloodWait

class HydraDownloader:
    """
    🚀 0.0001% TIER HACK: Asynchronous Memory Shard Injector (Swarm Network Edition)
    Abandons sequential TCP streaming and uses scatter-gather raw MTProto RPCs
    distributed across MULTIPLE donated Telegram accounts (The Swarm) to bypass 
    per-account rate limits completely.
    """
    def __init__(self, apps: list[Client], chunk_size=1024*1024, max_connections=5):
        self.apps = apps if isinstance(apps, list) else [apps]
        self.chunk_size = chunk_size
        self.max_connections = max_connections # Concurrent 1MB streams

    async def get_shard(self, file_id_obj, offset: int, limit: int, file_type: FileType):
        """Fetches a specific memory shard directly via MTProto using a Swarm Worker."""
        import random
        worker = random.choice(self.apps) # Multiplexing the load!
        
        # Cryptographic Skeleton Key parsing based on file type
        location = None
        if file_type == FileType.PHOTO:
            location = InputPhotoFileLocation(
                id=file_id_obj.media_id,
                access_hash=file_id_obj.access_hash,
                file_reference=file_id_obj.file_reference,
                thumb_size=file_id_obj.thumbnail_size or "w"
            )
        else:
            location = InputDocumentFileLocation(
                id=file_id_obj.media_id,
                access_hash=file_id_obj.access_hash,
                file_reference=file_id_obj.file_reference,
                thumb_size=""
            )
            
        success = False
        retries = 3
        while retries > 0 and not success:
            try:
                result = await worker.invoke(
                    GetFile(
                        location=location,
                        offset=offset,
                        limit=limit
                    ),
                    sleep_threshold=10, 
                )
                return offset, result.bytes
            except FloodWait as e:
                print(f"Swarm Worker {worker.name} hit FloodWait, sleeping {e.value}s...")
                await asyncio.sleep(e.value + 1)
                retries -= 1
            except Exception as e:
                print(f"Swarm Worker {worker.name} failed shard at offset {offset}: {e}")
                retries -= 1
        return offset, b""

    async def download(self, message, progress_callback=None, progress_args=()):
        media = message.photo or message.video or message.document or message.audio or message.voice
        if not media:
            return None
        
        file_id = media.file_id
        file_size = getattr(media, "file_size", getattr(media, "file_size", 0))
        
        if file_size == 0 or file_size < 1024 * 1024 * 5: # If < 5MB, revert to normal speed (overhead not worth it)
            return await self.apps[0].download_media(message, progress=progress_callback, progress_args=progress_args)
            
        file_id_obj = FileId.decode(file_id)
        
        # Calculate chunks
        total_chunks = math.ceil(file_size / self.chunk_size)
        offsets = [i * self.chunk_size for i in range(total_chunks)]
        
        downloaded = 0
        
        output_dir = "downloads/"
        os.makedirs(output_dir, exist_ok=True)
        file_name = getattr(media, "file_name", f"{message.id}_{file_id[:10]}")
        out_path = os.path.join(output_dir, file_name)
        
        start_time = time.time()
        print(f"🔥 [HYDRA SHARD INJECTOR] Saturating network with {total_chunks} shards...")
        
        try:
            # Create a sparse file of the exact size immediately to prevent fragmentation
            with open(out_path, "wb") as f:
                f.seek(file_size - 1)
                f.write(b"\0")
            
            # Random access concurrent writes
            with open(out_path, "r+b") as f:
                sem = asyncio.Semaphore(self.max_connections)
                
                async def process_shard(offset):
                    async with sem:
                        off, data = await self.get_shard(file_id_obj, offset, self.chunk_size, file_id_obj.file_type)
                        return off, data

                tasks = [process_shard(offset) for offset in offsets]
                last_cb = time.time()
                
                for f_task in asyncio.as_completed(tasks):
                    off, data = await f_task
                    if data:
                        f.seek(off)
                        f.write(data)
                        downloaded += len(data)
                        
                        # Throttle progress updates to avoid flood waits
                        now = time.time()
                        if progress_callback and (now - last_cb > 1.0 or downloaded == file_size):
                            last_cb = now
                            await progress_callback(downloaded, file_size, *progress_args)
                            
        except Exception as e:
            print(f"Hydra Downloader failed, reverting to slow fallback: {e}")
            return await self.apps[0].download_media(message, progress=progress_callback, progress_args=progress_args)
            
        print(f"✅ [HYDRA INJECTOR PROCESSED] {file_size/1024/1024:.2f}MB in {time.time() - start_time:.2f}s")
        return out_path
