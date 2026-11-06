import os
from typing import Optional, Any
from helpers import download_media_adaptive, cleanup_media, get_video_metadata, schedule_auto_delete

class MediaPipeline:
    """
    Deep Media Intake & Delivery Module.
    Encapsulates zero-byte cloud cache hits, adaptive RAM streaming (< 75MB),
    Hydra shard downloading (> 75MB), thumbnail/metadata extraction,
    multi-format Telegram dispatch, and auto-purging.
    """
    def __init__(
        self,
        bot_client: Any,
        user_client: Any,
        swarm_pool: Any,
        cache_adapter: Any,
        log_channel: Optional[int] = None,
        link_log_channel: Optional[int] = None
    ):
        self.bot = bot_client
        self.user_app = user_client
        self.swarm_pool = swarm_pool
        self.cache = cache_adapter
        self.log_channel = log_channel
        self.link_log_channel = link_log_channel

    async def deliver_media(
        self,
        source_msg: Any,
        target_chat_id: int,
        user_id: int,
        is_admin: bool = False,
        downloader: Optional[Any] = None,
        progress_callback: Optional[Any] = None,
        progress_args: tuple = ()
    ) -> Optional[Any]:
        chat_id = source_msg.chat.id
        msg_id = source_msg.id

        # 1. Zero-Byte Cloud Cache Intercept
        if self.log_channel:
            cached_log_id = self.cache.get_cached_link(chat_id, msg_id)
            if cached_log_id:
                try:
                    sent = await self.bot.copy_message(
                        chat_id=target_chat_id,
                        from_chat_id=self.log_channel,
                        message_id=cached_log_id
                    )
                    if sent and not is_admin:
                        schedule_auto_delete(self.bot, target_chat_id, sent.id, 300)
                    return sent
                except Exception as e:
                    print(f"Cache copy failed, falling back to download: {e}")

        # 2. Extract media metadata
        media = (
            source_msg.photo or
            source_msg.video or
            source_msg.document or
            source_msg.audio or
            source_msg.voice
        )
        file_size_bytes = getattr(media, "file_size", 0) if media else 0
        caption = source_msg.caption or ""

        # 3. Adaptive Download: RAM Stream (< 75MB) vs Swarm Shard (> 75MB)
        if downloader is None:
            downloader = self.swarm_pool.acquire_worker()
        file_target = await download_media_adaptive(
            downloader,
            source_msg,
            file_size_bytes,
            progress=progress_callback,
            progress_args=progress_args
        )

        if not file_target:
            from memory_injector import HydraDownloader
            try:
                swarm_clients = [downloader] + [c for c in self.swarm_pool.get_all_pool_clients() if c != downloader]
                conns = self.swarm_pool.get_concurrency_limit(user_id, is_admin)
                hydra = HydraDownloader(swarm_clients, max_connections=conns)
                file_target = await hydra.download(
                    source_msg,
                    progress_callback=progress_callback,
                    progress_args=progress_args
                )
            except Exception as e:
                print(f"Hydra Sharding failed, falling back to client download: {e}")
                file_target = await downloader.download_media(
                    source_msg,
                    progress=progress_callback,
                    progress_args=progress_args
                )

        if not file_target:
            return None

        # 4. Dispatch Media According to Type
        sent_msg = None
        v_thumb = None
        try:
            if source_msg.photo:
                sent_msg = await self.bot.send_photo(
                    chat_id=target_chat_id,
                    photo=file_target,
                    caption=caption,
                    progress=progress_callback,
                    progress_args=progress_args
                )
            elif source_msg.video:
                if isinstance(file_target, str):
                    ext_dur, ext_w, ext_h, ext_thumb = get_video_metadata(file_target)
                    v_duration = (source_msg.video.duration or 0) or ext_dur
                    v_width = (source_msg.video.width or 0) or ext_w
                    v_height = (source_msg.video.height or 0) or ext_h
                    v_thumb = ext_thumb
                else:
                    v_duration = source_msg.video.duration or 0
                    v_width = source_msg.video.width or 0
                    v_height = source_msg.video.height or 0
                    if source_msg.video.thumbs:
                        try:
                            v_thumb = await downloader.download_media(source_msg.video.thumbs[0].file_id, in_memory=True)
                        except Exception:
                            v_thumb = None

                sent_msg = await self.bot.send_video(
                    chat_id=target_chat_id,
                    video=file_target,
                    caption=caption,
                    duration=v_duration,
                    width=v_width,
                    height=v_height,
                    thumb=v_thumb,
                    progress=progress_callback,
                    progress_args=progress_args
                )
            elif source_msg.document:
                sent_msg = await self.bot.send_document(
                    chat_id=target_chat_id,
                    document=file_target,
                    caption=caption,
                    progress=progress_callback,
                    progress_args=progress_args
                )
            elif source_msg.audio:
                sent_msg = await self.bot.send_audio(
                    chat_id=target_chat_id,
                    audio=file_target,
                    caption=caption,
                    progress=progress_callback,
                    progress_args=progress_args
                )
            elif source_msg.voice:
                sent_msg = await self.bot.send_voice(
                    chat_id=target_chat_id,
                    voice=file_target,
                    caption=caption,
                    progress=progress_callback,
                    progress_args=progress_args
                )
            else:
                sent_msg = await self.bot.send_document(
                    chat_id=target_chat_id,
                    document=file_target,
                    caption=caption,
                    progress=progress_callback,
                    progress_args=progress_args
                )

            # 5. Mirror to LOG_CHANNEL via Server-Side Copy & Save Cache
            if self.log_channel and sent_msg and str(self.log_channel) != str(target_chat_id):
                try:
                    log_sent = await sent_msg.copy(self.log_channel)
                    if log_sent:
                        self.cache.save_cached_link(chat_id, msg_id, log_sent.id)
                except Exception as log_err:
                    print(f"Failed to copy to log channel: {log_err}")

            # 6. Auto-Delete Schedule
            if sent_msg and not is_admin:
                schedule_auto_delete(self.bot, target_chat_id, sent_msg.id, 300)

            return sent_msg

        finally:
            cleanup_media(v_thumb)
            cleanup_media(file_target)
