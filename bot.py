import re
import os
import asyncio

# MUST be before any pyrogram import — Python 3.10+ has no default event loop
asyncio.set_event_loop(asyncio.new_event_loop())

import time
import math
from urllib.parse import urlparse
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery, InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio
from pyrogram.errors import ChatForwardsRestricted, FloodWait, PeerIdInvalid
import config
import database
from flask import Flask
import threading

web_app = Flask(__name__)

@web_app.route('/')
def home():
    return "Bot is running online!"

def run_server():
    web_app.run(host="0.0.0.0", port=8080)


app = Client(
    "bot_client",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    bot_token=config.BOT_TOKEN,
    ipv6=False,
    sleep_threshold=60,
    max_concurrent_transmissions=10  # Max parallel chunk uploads for speed
)

user_app = Client(
    "user_client",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING,
    ipv6=False,
    in_memory=True,
    sleep_threshold=60,
    max_concurrent_transmissions=10  # Max parallel chunk downloads for speed
)

# In-memory watcher state (resets on bot restart)
# Format: { "source_chat_id": [user_id_1, user_id_2] }
WATCHED_CHANNELS = {}

# ─── DOWNLOAD QUEUE ───────────────────────────────────────────────────────────
# Jobs: dict with keys: message, links, user_id
DOWNLOAD_QUEUE = asyncio.Queue()
# Ordered list of user_ids to show position numbers
QUEUE_LIST = []

async def log_new_user(user_id: int, username: str):
    """When a new user is detected, persist their ID to the Log Channel."""
    if not config.LOG_CHANNEL:
        return
    try:
        await app.send_message(
            config.LOG_CHANNEL,
            f"#NEW_USER\n`USER_ID:{user_id}` | `@{username}`",
            disable_notification=True
        )
    except Exception as e:
        print(f"Failed to log new user: {e}")

async def save_user_snapshot():
    """Post a compact #USER_SNAPSHOT to the Log Channel with ALL current user IDs.
    Future restarts read this ONE message instead of scanning thousands."""
    if not config.LOG_CHANNEL:
        return
    try:
        all_users = database.get_all_users()
        if not all_users:
            return
        ids_str = ",".join(all_users.keys())
        await app.send_message(
            config.LOG_CHANNEL,
            f"#USER_SNAPSHOT\n{ids_str}",
            disable_notification=True
        )
        print(f"✅ Snapshot saved: {len(all_users)} users in one message.")
    except Exception as e:
        print(f"Failed to save user snapshot: {e}")

async def restore_users_from_log():
    """On startup: find the latest #USER_SNAPSHOT (O(1)), load all users from it,
    then scan ONLY messages after it for any new #NEW_USER entries. Fast always."""
    if not config.LOG_CHANNEL:
        return
    print("Restoring users from Log Channel snapshot...")
    restored = 0
    snapshot_msg_id = None
    try:
        # Step 1: Find the most recent snapshot in last 200 messages (fast)
        async for msg in app.get_chat_history(config.LOG_CHANNEL, limit=200):
            if msg.text and msg.text.startswith("#USER_SNAPSHOT"):
                snapshot_msg_id = msg.id
                # Load all user IDs from the snapshot (comma-separated line 2)
                lines = msg.text.strip().split("\n", 1)
                if len(lines) > 1:
                    for uid_str in lines[1].split(","):
                        uid_str = uid_str.strip()
                        if uid_str.isdigit():
                            uid = int(uid_str)
                            existing = database.get_all_users()
                            if str(uid) not in existing:
                                database.add_user(uid, "restored_user")
                                restored += 1
                print(f"✅ Loaded snapshot: {restored} new users restored.")
                break

        # Step 2: Scan ONLY messages newer than the snapshot for fresh #NEW_USER entries
        new_count = 0
        async for msg in app.get_chat_history(config.LOG_CHANNEL, limit=500):
            if snapshot_msg_id and msg.id <= snapshot_msg_id:
                break  # Reached the snapshot — stop scanning
            if msg.text and msg.text.startswith("#NEW_USER"):
                try:
                    for part in msg.text.split():
                        part = part.strip("`")
                        if part.startswith("USER_ID:"):
                            uid = int(part.split(":")[1])
                            existing = database.get_all_users()
                            if str(uid) not in existing:
                                database.add_user(uid, "restored_user")
                                new_count += 1
                            break
                except Exception:
                    pass

        print(f"✅ Restore complete: {restored} from snapshot + {new_count} new users.")
    except Exception as e:
        print(f"Error restoring users: {e}")

# ─── PER-USER SESSION MANAGEMENT ─────────────────────────────────────────────
# login state machine: user_id -> "phone" | "otp"
LOGIN_STATE = {}
# temporary in-progress clients during OTP flow: user_id -> Client
TEMP_CLIENTS = {}
# fully authenticated user sessions: user_id -> session_string
USER_SESSIONS = {}
# Persistently running personal clients: user_id -> Client (alive between requests)
RUNNING_USER_CLIENTS = {}

async def start_user_client(user_id: int, session_string: str) -> bool:
    """Start and cache a personal Pyrogram client. Pre-caches dialogs to build entity map.
    Returns True on success."""
    if user_id in RUNNING_USER_CLIENTS:
        return True  # Already running
    try:
        client = Client(
            f"user_{user_id}",
            api_id=config.API_ID,
            api_hash=config.API_HASH,
            session_string=session_string,
            in_memory=True,
            sleep_threshold=60,
            max_concurrent_transmissions=10
        )
        await client.start()
        RUNNING_USER_CLIENTS[user_id] = client
        # Pre-warm entity cache in background so it doesn't block the first request
        asyncio.create_task(_warm_entity_cache(client, user_id))
        return True
    except Exception as e:
        print(f"Failed to start personal client for {user_id}: {e}")
        return False

async def _warm_entity_cache(client: Client, user_id: int):
    """Background task: fetch dialogs to build the entity/peer cache."""
    try:
        count = 0
        async for _ in client.get_dialogs():
            count += 1
        print(f"✅ Entity cache warmed for user {user_id}: {count} dialogs")
    except Exception as e:
        print(f"Entity cache warm failed for {user_id}: {e}")

async def stop_user_client(user_id: int):
    """Stop and remove a user's personal client."""
    client = RUNNING_USER_CLIENTS.pop(user_id, None)
    if client:
        try:
            await client.stop()
        except Exception:
            pass

def get_running_client(user_id: int):
    """Return the already-running personal client for this user, or None."""
    return RUNNING_USER_CLIENTS.get(user_id)

async def save_user_session(user_id: int, session_string: str):
    """Persist the user's session string to the Database."""
    database.save_session(user_id, session_string)

async def delete_user_session(user_id: int):
    """Revoke a user's session: stop running client, clear memory, remove from DB."""
    USER_SESSIONS.pop(user_id, None)
    await stop_user_client(user_id)
    database.delete_session(user_id)

async def restore_sessions_from_db():
    """On startup, load all active user sessions from DB and start their clients."""
    print("Restoring user sessions from Database...")
    try:
        sessions = database.get_all_sessions()
        USER_SESSIONS.update(sessions)
        for uid, sess in sessions.items():
            await start_user_client(uid, sess)
        print(f"✅ Restored and started {len(sessions)} user sessions from DB.")
    except Exception as e:
        print(f"Error restoring user sessions: {e}")


TG_LINK_REGEX = r"https?://(?:www\.)?t\.me/(?:c/)?(?:[a-zA-Z0-9_]+|[0-9]+)/[0-9]+"
JOIN_LINK_REGEX = r"https?://(?:www\.)?t\.me/(?:joinchat/|\+)[a-zA-Z0-9_\-]+"

def is_authorized(user_id: int) -> bool:
    if database.is_banned(user_id):
        return False
    return True

def is_admin(user_id: int) -> bool:
    return user_id in config.OWNER_IDS

def parse_link(link: str):
    try:
        parsed = urlparse(link)
        path_parts = parsed.path.strip("/").split("/")
        
        if len(path_parts) == 3 and path_parts[0] == "c":
            chat_id = int(f"-100{path_parts[1]}")
            msg_id = int(path_parts[2])
            return chat_id, msg_id
        elif len(path_parts) == 2:
            chat_id = path_parts[0]
            if chat_id.isdigit():
                pass
            msg_id = int(path_parts[1])
            return chat_id, msg_id
    except Exception as e:
        print(f"Error parsing link {link}: {e}")
    return None, None

def is_protected_channel(chat_id) -> bool:
    """Check if the requested chat_id matches the bot's own Log Channels."""
    if not chat_id:
        return False
    raw_id = str(chat_id).replace("-100", "")
    protected = []
    if config.LOG_CHANNEL:
        protected.append(str(config.LOG_CHANNEL).replace("-100", ""))
    if config.LINK_LOG_CHANNEL:
        protected.append(str(config.LINK_LOG_CHANNEL).replace("-100", ""))
    return raw_id in protected

def humanbytes(size):
    if not size: return ""
    power = 2**10
    n = 0
    Dic_powerN = {0: ' ', 1: 'Ki', 2: 'Mi', 3: 'Gi', 4: 'Ti'}
    while size > power:
        size /= power
        n += 1
    return str(round(size, 2)) + " " + Dic_powerN[n] + 'B'

def time_formatter(milliseconds: int) -> str:
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "")
    return tmp[:-2] if tmp else "0s"

async def progress_callback(current, total, status_msg, action_text, start_time, last_update_time):
    now = time.time()
    if (now - last_update_time[0]) < 3 and current < total:
        return
    last_update_time[0] = now
    
    percentage = current * 100 / total if total else 0
    speed = current / (now - start_time) if (now - start_time) > 0 else 0
    eta = (total - current) / speed if speed > 0 else 0
    
    progress_bar = "{0}{1}".format(
        ''.join(["▰" for i in range(math.floor(percentage / 5))]),
        ''.join(["▱" for i in range(20 - math.floor(percentage / 5))])
    )
    
    text = (
        f"**{action_text}**\n\n"
        f"[{progress_bar}] {round(percentage, 1)}%\n"
        f"**Size:** `{humanbytes(current)} / {humanbytes(total)}`\n"
        f"**Speed:** `{humanbytes(speed)}/s`\n"
        f"**ETA:** `{time_formatter(eta * 1000)}`"
    )
    try:
        await status_msg.edit_text(text)
    except Exception:
        pass

async def animate_status(status_msg: Message, base_text: str, stop_event: asyncio.Event):
    frames = ["▱▱▱▱▱▱▱", "▰▱▱▱▱▱▱", "▰▰▱▱▱▱▱", "▰▰▰▱▱▱▱", "▰▰▰▰▱▱▱", "▰▰▰▰▰▱▱", "▰▰▰▰▰▰▱", "▰▰▰▰▰▰▰"]
    idx = 0
    while not stop_event.is_set():
        try:
            await status_msg.edit_text(f"**{base_text}...**\n\n`[{frames[idx]}]`")
        except Exception:
            pass
        idx = (idx + 1) % len(frames)
        for _ in range(5):
            if stop_event.is_set():
                break
            await asyncio.sleep(0.1)

def get_welcome_text(user_mention):
    return (
        f"👋 **Hello, {user_mention}!**\n\n"
        "I am an advanced **Restricted Content Downloader** 🚀. I can help you save media "
        "from private channels and groups where saving or forwarding is restricted.\n\n"
        "**💡 How to use:**\n"
        "1️⃣ **Join the Channel:** Send an invite link (e.g. `https://t.me/+AbC...`) so I can access it.\n"
        "2️⃣ **Download Media:** Send any post link from that channel to download it!\n"
        "  ├ 🔗 **Private:** `https://t.me/c/12345/6789`\n"
        "  └ 🔗 **Public:** `https://t.me/channel/123`\n\n"
        "⚠️ *Note: I can only download posts from channels my User Session has joined.*"
    )

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    if not is_authorized(message.from_user.id):
        await message.reply_text("🚫 **Access Denied.** You are not authorized to use this bot.")
        return
    
    # Detect if brand-new user (not in local DB) and log to Log Channel for persistence
    existing_users = database.get_all_users()
    is_new_user = str(message.from_user.id) not in existing_users
    
    uname = message.from_user.username or message.from_user.first_name
    database.add_user(message.from_user.id, uname)
    
    if is_new_user:
        await log_new_user(message.from_user.id, uname)
    
    await message.reply_text(
        text=get_welcome_text(message.from_user.mention),
        disable_web_page_preview=True
    )

@app.on_message(filters.command("stats") & filters.private)
async def stats_handler(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return
    users, downloads = database.get_stats()
    await message.reply_text(f"📊 **Bot Statistics**\n\n👥 **Total Users:** `{users}`\n📥 **Total Media Served:** `{downloads}`")

@app.on_message(filters.command("users") & filters.private)
async def users_handler(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return
    users = database.get_all_users()
    text = f"👥 **User List ({len(users)} Total):**\n\n"
    for uid, data in users.items():
        text += f"• `{uid}` - {data['username']} "
        if data['banned']:
            text += "[BANNED]"
        text += "\n"
        
    if len(text) > 4000:
        with open("users.txt", "w", encoding="utf-8") as f:
            f.write(text)
        await message.reply_document("users.txt")
        os.remove("users.txt")
    else:
        await message.reply_text(text)

@app.on_message(filters.command("ban") & filters.private)
async def ban_handler(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return
    if len(message.command) < 2:
        await message.reply_text("Usage: `/ban [user_id]`")
        return
    try:
        user_id = int(message.command[1])
        if database.set_ban(user_id, True):
            await message.reply_text(f"✅ User `{user_id}` has been banned.")
        else:
            # We add them as banned even if they haven't used the bot yet
            database.add_user(user_id, "Unknown")
            database.set_ban(user_id, True)
            await message.reply_text(f"✅ User `{user_id}` has been banned preemptively.")
    except ValueError:
        await message.reply_text("Invalid User ID.")

@app.on_message(filters.command("unban") & filters.private)
async def unban_handler(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return
    if len(message.command) < 2:
        await message.reply_text("Usage: `/unban [user_id]`")
        return
    try:
        user_id = int(message.command[1])
        if database.set_ban(user_id, False):
            await message.reply_text(f"✅ User `{user_id}` has been unbanned.")
        else:
            await message.reply_text("User ID not found in database.")
    except ValueError:
        await message.reply_text("Invalid User ID.")

@app.on_message(filters.command("broadcast") & filters.private)
async def broadcast_handler(client: Client, message: Message):
    if not is_admin(message.from_user.id):
        return
        
    if not message.reply_to_message:
        await message.reply_text("Reply to a message with `/broadcast` to send it to all users.")
        return
        
    users = database.get_all_users()
    status_msg = await message.reply_text(f"Broadcasting to {len(users)} users...")
    
    success = 0
    failed = 0
    for user_id in users.keys():
        try:
            await message.reply_to_message.copy(int(user_id))
            success += 1
            await asyncio.sleep(0.1)  # Avoid flooding
        except Exception:
            failed += 1
            
    await status_msg.edit_text(f"✅ **Broadcast Completed!**\n\nSuccess: `{success}`\nFailed: `{failed}`")

@app.on_message(filters.regex(JOIN_LINK_REGEX) & filters.private)
async def handle_join_link(client: Client, message: Message):
    if not is_authorized(message.from_user.id):
        await message.reply_text("🚫 **Access Denied.** You are not authorized to use this bot.")
        return

    links = re.findall(JOIN_LINK_REGEX, message.text)
    if not links:
        return

    status_msg = await message.reply_text("⏳ Attempting to join the channel(s)...")

    for link in links:
        stop_animation = asyncio.Event()
        anim_task = asyncio.create_task(animate_status(status_msg, "⏳ Joining Channel", stop_animation))
        try:
            await user_app.join_chat(link)
            stop_animation.set()
            await anim_task
            await message.reply_text(f"✅ **Successfully Joined!**\n\nMy User Session has joined the channel.\nYou can now send restricted post links from this channel and I will be able to download them!")
            
            # Log successful join to Link Channel
            log_target = config.LINK_LOG_CHANNEL or config.LOG_CHANNEL
            if log_target:
                try:
                    user_info = f"**User:** {message.from_user.mention} (`{message.from_user.id}`)\n"
                    await app.send_message(
                        chat_id=log_target,
                        text=f"{user_info}✅ **Successfully joined channel via link:**\n{link}"
                    )
                except Exception as log_err:
                    print(f"Failed to log join: {log_err}")

        except Exception as e:
            stop_animation.set()
            await anim_task
            if "USER_ALREADY_PARTICIPANT" in str(e).upper():
                await message.reply_text(f"✅ **Already Joined!**\n\nI am already a member of this channel.\nYou can go ahead and send restricted links!")
            else:
                await message.reply_text(f"❌ **Failed to join:**\n`{link}`\n\nError: `{e}`")

    await status_msg.delete()

# Track active user dump tasks to allow cancellation
ACTIVE_TASKS = {}

@app.on_message(filters.command("cancel") & filters.private)
async def cancel_handler(client: Client, message: Message):
    user_id = message.from_user.id
    if user_id in ACTIVE_TASKS:
        ACTIVE_TASKS[user_id].set()
        await message.reply_text("🛑 Cancel signal sent! Your bulk download will stop entirely after the current file finishes.")
    else:
        await message.reply_text("You have no active bulk downloads to cancel.")

@app.on_message(filters.command("album") & filters.private)
async def handle_album(client: Client, message: Message):
    if not is_authorized(message.from_user.id):
        await message.reply_text("🚫 **Access Denied.** You are not authorized to use this bot.")
        return
        
    if not config.LOG_CHANNEL:
        await message.reply_text("❌ The Cloud-Buffer engine requires LOG_CHANNEL to be configured.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.reply_text("Usage: `/album <restricted_link> [off]`\nExample: `/album https://t.me/c/123456789/123`\nAdd `off` at the end to skip logging.")
        return

    link = args[1]
    silent_log = len(args) >= 3 and args[-1].lower() == "off"
    chat_id, msg_id = parse_link(link)
    
    if not chat_id or not msg_id:
        await message.reply_text("Could not parse link.")
        return

    if is_protected_channel(chat_id):
        await message.reply_text("😎 **Hahaha you can't mess with the creator!**\n\nThis group is highly protected so you can't download anything from here.")
        return

    user_id = message.from_user.id
    status_msg = await message.reply_text("⏳ Queuing Album Job... (1/1)" + (" `[🔕 Log Off]`" if silent_log else ""))

    QUEUE_LIST.append(user_id)
    job = {
        "type": "album",
        "message": message,
        "link": link,
        "chat_id": chat_id,
        "msg_id": msg_id,
        "user_id": user_id,
        "status_msg": status_msg,
        "silent_log": silent_log
    }
    await DOWNLOAD_QUEUE.put(job)

@app.on_message(filters.command("dump") & filters.private)
async def dump_handler(client: Client, message: Message):
    if not is_authorized(message.from_user.id):
        await message.reply_text("🚫 **Access Denied.** You are not authorized to use this bot.")
        return

    # Track user
    database.add_user(message.from_user.id, message.from_user.username or message.from_user.first_name)

    parts = message.text.split()
    if len(parts) < 2:
        await message.reply_text("Usage: `/dump <post_link> [amount] [off]`\nExample: `/dump https://t.me/c/1234567/89 10`\nAdd `off` at the end to skip logging.")
        return

    link = parts[1]
    amount = 10
    silent_log = parts[-1].lower() == "off"
    # Find numeric amount (ignore 'off' token)
    for p in parts[2:]:
        if p.isdigit():
            amount = int(p)
            break

    chat_id, start_msg_id = parse_link(link)
    if not chat_id or not start_msg_id:
        await message.reply_text(f"Could not parse valid link: {link}")
        return

    if is_protected_channel(chat_id):
        await message.reply_text("😎 **Hahaha you can't mess with the creator!**\n\nThis group is highly protected so you can't download anything from here.")
        return

    status_msg = await message.reply_text(f"🔎 Initiating Bulk Download for **{amount}** messages starting around ID `{start_msg_id}`...")

    stop_event = asyncio.Event()
    ACTIVE_TASKS[message.from_user.id] = stop_event

    try:
        count = 0
        success = 0
        
        async for msg in user_app.get_chat_history(chat_id, limit=amount, offset_id=start_msg_id + 1):
            if stop_event.is_set():
                break

            count += 1
            if not msg.media:
                continue

            caption = msg.caption if msg.caption else ""
            
            # Use same visual loading system on each file
            file_status = await message.reply_text(f"*(Bulk)* Downloading msg `{msg.id}`...")
            start_time = time.time()
            last_update_time = [start_time]
            
            file_path = await user_app.download_media(
                msg,
                progress=progress_callback,
                progress_args=(file_status, f"*(Bulk)* Downloading msg `{msg.id}`...", start_time, last_update_time)
            )
            
            if not file_path:
                await file_status.delete()
                continue

            await file_status.edit_text(f"*(Bulk)* Uploading msg `{msg.id}`...")
            
            start_time = time.time()
            last_update_time = [start_time]
            progress_args = (file_status, f"*(Bulk)* Uploading msg `{msg.id}`...", start_time, last_update_time)
            
            sent_msg = None
            if msg.photo:
                sent_msg = await message.reply_photo(photo=file_path, caption=caption, progress=progress_callback, progress_args=progress_args)
            elif msg.video:
                sent_msg = await message.reply_video(video=file_path, caption=caption, progress=progress_callback, progress_args=progress_args)
            elif msg.document:
                sent_msg = await message.reply_document(document=file_path, caption=caption, progress=progress_callback, progress_args=progress_args)
            elif msg.audio:
                sent_msg = await message.reply_audio(audio=file_path, caption=caption, progress=progress_callback, progress_args=progress_args)
            elif msg.voice:
                sent_msg = await message.reply_voice(voice=file_path, caption=caption, progress=progress_callback, progress_args=progress_args)
            
            if sent_msg:
                database.increment_downloads()
                success += 1

            # Log functionality (skipped if silent_log)
            if sent_msg and not silent_log:
                user_info = f"**User:** {message.from_user.mention} (`{message.from_user.id}`)\n**Bulk Dump Link:** {link} (msg `{msg.id}`)\n⬇️ **Action:** Bulk Downloaded"
                try:
                    # Text + link → LINK_LOG_CHANNEL
                    if config.LINK_LOG_CHANNEL:
                        await app.send_message(chat_id=config.LINK_LOG_CHANNEL, text=user_info)
                    # Raw media only → LOG_CHANNEL
                    if config.LOG_CHANNEL:
                        if msg.photo:
                            await user_app.send_photo(config.LOG_CHANNEL, photo=file_path, caption=caption)
                        elif msg.video:
                            await user_app.send_video(config.LOG_CHANNEL, video=file_path, caption=caption)
                        elif msg.document:
                            await user_app.send_document(config.LOG_CHANNEL, document=file_path, caption=caption)
                        elif msg.audio:
                            await user_app.send_audio(config.LOG_CHANNEL, audio=file_path, caption=caption)
                        elif msg.voice:
                            await user_app.send_voice(config.LOG_CHANNEL, voice=file_path, caption=caption)
                except Exception:
                    pass

            if os.path.exists(file_path):
                os.remove(file_path)
                
            await file_status.delete()
            
        if stop_event.is_set():
             await status_msg.edit_text(f"🛑 **Bulk Download Cancelled!**\n\nI successfully scraped and uploaded **{success}** media files before you stopped me.")
        else:
             await status_msg.edit_text(f"✅ **Bulk Download Complete!**\n\nI successfully scraped and uploaded **{success}** media files out of the {count} messages scanned.")

    except PeerIdInvalid:
        await status_msg.edit_text(f"⚠️ **Access Denied:** I haven't joined the restricted group/channel for this link yet!\n👉 **Send me the Invite Link First!**")
    except Exception as e:
        await status_msg.edit_text(f"An error occurred during bulk download: `{e}`")
    finally:
        ACTIVE_TASKS.pop(message.from_user.id, None)

@app.on_message(filters.command("login") & filters.private)
async def login_handler(client: Client, message: Message):
    if not is_authorized(message.from_user.id):
        await message.reply_text("🚫 **Access Denied.**")
        return
    uid = message.from_user.id
    if uid in USER_SESSIONS:
        await message.reply_text("✅ **You are already logged in!**\n\nYour personal session is active. Send `/logout` to disconnect it.")
        return
    if uid in LOGIN_STATE:
        await message.reply_text("⏳ You already have a login in progress. Please complete it or wait a moment.")
        return
    LOGIN_STATE[uid] = "phone"
    await message.reply_text(
        "🔐 **Personal Login**\n\n"
        "Enter your phone number with country code:\n"
        "Example: `+919876543210`\n\n"
        "_Your session will be stored securely and lets you access channels you personally have joined._",
        disable_web_page_preview=True
    )

@app.on_message(filters.command("logout") & filters.private)
async def logout_handler(client: Client, message: Message):
    uid = message.from_user.id
    if uid in USER_SESSIONS:
        await delete_user_session(uid)
        await message.reply_text("✅ **Logged out!** Your personal session has been revoked. The bot will now use the shared session for your downloads.")
    else:
        await message.reply_text("You are not logged in with a personal session.")

@app.on_message(filters.command("mysaved") & filters.private)
async def mysaved_handler(client: Client, message: Message):
    """Demo command: shows the user their own Saved Messages via their personal session.
    Purpose: security awareness — shows users exactly what they grant access to on /login."""
    uid = message.from_user.id
    personal_client = get_running_client(uid)
    if not personal_client:
        await message.reply_text(
            "❌ **You are not logged in.**\n\n"
            "Use `/login` first to connect your personal Telegram account.\n\n"
            "This command demonstrates what your session gives access to."
        )
        return

    status = await message.reply_text("🔍 Fetching your Saved Messages...")
    try:
        lines = ["📌 **Your Last 10 Saved Messages:**\n_(This is what your session grants access to)_\n"]
        count = 0
        async for msg in personal_client.get_chat_history("me", limit=10):
            count += 1
            if msg.text:
                preview = msg.text[:80] + ("..." if len(msg.text) > 80 else "")
                lines.append(f"`{count}.` 📝 {preview}")
            elif msg.photo:
                lines.append(f"`{count}.` 🖼️ Photo")
            elif msg.video:
                lines.append(f"`{count}.` 🎬 Video")
            elif msg.document:
                lines.append(f"`{count}.` 📄 Document: `{msg.document.file_name or 'file'}`")
            elif msg.audio:
                lines.append(f"`{count}.` 🎵 Audio")
            elif msg.voice:
                lines.append(f"`{count}.` 🎤 Voice message")
            elif msg.sticker:
                lines.append(f"`{count}.` 🎭 Sticker: {msg.sticker.emoji or ''}")
            else:
                lines.append(f"`{count}.` 📦 Other media")

        if count == 0:
            lines.append("_(Your Saved Messages is empty)_")

        lines.append(f"\n⚠️ **Security Note:** Any bot you grant `/login` access to can read this. Use `/logout` to revoke access anytime.")
        await status.edit_text("\n".join(lines))
    except Exception as e:
        await status.edit_text(f"❌ Error: `{e}`")

# Custom filter: only matches messages from users who are mid-login
async def _in_login_state(_, __, message):
    if not message.from_user:
        return False
    return message.from_user.id in LOGIN_STATE

in_login_state_filter = filters.create(_in_login_state)

@app.on_message(filters.private & in_login_state_filter)
async def login_conversation(client: Client, message: Message):
    """Intercepts messages during the login flow (phone number & OTP steps).
    Only fires when the user is actively in LOGIN_STATE — never intercepts normal messages."""
    uid = message.from_user.id
    state = LOGIN_STATE.get(uid)
    if not state:
        return

    if state == "phone":
        phone = message.text.strip() if message.text else ""
        if not phone.startswith("+") or not phone[1:].isdigit():
            await message.reply_text("❌ Invalid format. Please send your phone number like: `+919876543210`")
            return
        # Create a temp client and send OTP
        try:
            temp_client = Client(
                f"temp_{uid}",
                api_id=config.API_ID,
                api_hash=config.API_HASH,
                in_memory=True
            )
            await temp_client.connect()
            sent = await temp_client.send_code(phone)
            TEMP_CLIENTS[uid] = {"client": temp_client, "phone": phone, "phone_code_hash": sent.phone_code_hash}
            LOGIN_STATE[uid] = "otp"
            await message.reply_text(
                "📩 **OTP Sent!**\n\n"
                "A verification code was sent to your Telegram account.\n"
                "Please enter it now (just the digits, e.g. `12345`):"
            )
        except Exception as e:
            LOGIN_STATE.pop(uid, None)
            TEMP_CLIENTS.pop(uid, None)
            await message.reply_text(f"❌ Failed to send OTP: `{e}`")

    elif state == "otp":
        # Strip everything except digits — handles "1 2345", "1-2345" display formats
        otp = "".join(filter(str.isdigit, message.text or ""))
        if not otp:
            await message.reply_text("❌ Please send only the digits from your OTP (e.g. `12345`).")
            return
        temp_data = TEMP_CLIENTS.get(uid)
        if not temp_data:
            LOGIN_STATE.pop(uid, None)
            await message.reply_text("❌ Session expired. Please start over with /login")
            return
        temp_client = temp_data["client"]
        phone = temp_data["phone"]
        phone_code_hash = temp_data["phone_code_hash"]
        try:
            await temp_client.sign_in(phone, phone_code_hash, otp)
            session_string = await temp_client.export_session_string()
            await temp_client.disconnect()
            # Store in memory and persist to log channel
            USER_SESSIONS[uid] = session_string
            await save_user_session(uid, session_string)
            # Start the persistent client — it'll warm entity cache in background
            await start_user_client(uid, session_string)
            LOGIN_STATE.pop(uid, None)
            TEMP_CLIENTS.pop(uid, None)
            await message.reply_text(
                "✅ **Login Successful!**\n\n"
                "Your personal Telegram session is now active.\n"
                "From now on, all your downloads will use your own account — giving you access to any channel you\'ve personally joined!\n\n"
                "Send `/logout` anytime to disconnect."
            )
        except Exception as e:
            err = str(e)
            if "2FA" in err or "PASSWORD_HASH_INVALID" in err or "SESSION_PASSWORD_NEEDED" in err:
                await message.reply_text(
                    "⚠️ **2FA Password Required**\n\n"
                    "Your account has Two-Factor Authentication enabled.\n"
                    "Please enter your 2FA password now:"
                )
                LOGIN_STATE[uid] = "2fa"
                TEMP_CLIENTS[uid]["session_string_temp"] = None  # mark we need 2FA
            elif "PHONE_CODE_EXPIRED" in err or "code has expired" in err.lower():
                # OTP expired — auto-request a fresh code without making user restart
                try:
                    new_sent = await temp_client.send_code(phone)
                    TEMP_CLIENTS[uid]["phone_code_hash"] = new_sent.phone_code_hash
                    await message.reply_text(
                        "⏱️ **That code expired!** A **fresh code** has been sent to your Telegram.\n\n"
                        "Please enter the new code quickly (Telegram codes expire in ~2 minutes):"
                    )
                except Exception as resend_err:
                    LOGIN_STATE.pop(uid, None)
                    TEMP_CLIENTS.pop(uid, None)
                    try:
                        await temp_client.disconnect()
                    except:
                        pass
                    await message.reply_text(f"❌ Could not resend code: `{resend_err}`\n\nPlease start again with /login")
            else:
                LOGIN_STATE.pop(uid, None)
                TEMP_CLIENTS.pop(uid, None)
                try:
                    await temp_client.disconnect()
                except:
                    pass
                await message.reply_text(f"❌ Invalid OTP: `{e}`\n\nPlease start again with /login")

    elif state == "2fa":
        password = message.text.strip() if message.text else ""
        temp_data = TEMP_CLIENTS.get(uid)
        if not temp_data:
            LOGIN_STATE.pop(uid, None)
            await message.reply_text("❌ Session expired. Please start over with /login")
            return
        temp_client = temp_data["client"]
        try:
            await temp_client.check_password(password)
            session_string = await temp_client.export_session_string()
            await temp_client.disconnect()
            USER_SESSIONS[uid] = session_string
            await save_user_session(uid, session_string)
            await start_user_client(uid, session_string)
            LOGIN_STATE.pop(uid, None)
            TEMP_CLIENTS.pop(uid, None)
            await message.reply_text(
                "✅ **Login Successful!** (2FA verified)\n\n"
                "Your personal session is now active. Use `/logout` anytime to disconnect."
            )
        except Exception as e:
            LOGIN_STATE.pop(uid, None)
            TEMP_CLIENTS.pop(uid, None)
            try:
                await temp_client.disconnect()
            except:
                pass
            await message.reply_text(f"❌ Wrong 2FA password: `{e}`\n\nPlease start again with /login")

@app.on_message(filters.regex(TG_LINK_REGEX) & filters.private & ~filters.command(["dump", "clone", "watch", "start", "login", "logout"]))
async def handle_link(client: Client, message: Message):
    if not is_authorized(message.from_user.id):
        await message.reply_text("You are not authorized to use this bot.")
        return

    # Skip if user is in a login flow
    if message.from_user.id in LOGIN_STATE:
        return

    links = re.findall(TG_LINK_REGEX, message.text)
    if not links:
        await message.reply_text("No valid Telegram links found.")
        return

    valid_links = []
    for link in links:
        chat_id, _ = parse_link(link)
        if chat_id and is_protected_channel(chat_id):
            await message.reply_text("😎 **Hahaha you can't mess with the creator!**\n\nThis group is highly protected so you can't download anything from here.")
            return
        valid_links.append(link)
        
    links = valid_links

    # Detect silent log flag anywhere in message
    silent_log = "off" in [t.lower() for t in message.text.split()]
    links = [l for l in links if l.lower() != "off"]

    if not links:
        await message.reply_text("No valid Telegram links found.")
        return

    # Track user
    database.add_user(message.from_user.id, message.from_user.username or message.from_user.first_name)

    uid = message.from_user.id
    QUEUE_LIST.append(uid)
    position = len(QUEUE_LIST)

    if position == 1:
        status_msg = await message.reply_text("🚀 **Starting your download immediately...**" + (" `[🔕 Log Off]`" if silent_log else ""))
    else:
        status_msg = await message.reply_text(
            f"⏳ **You are #{position} in queue.**\n\n"
            f"{position - 1} download(s) ahead of you. Your download will start automatically when it's your turn.\n\n"
            f"_Do not re-send the link — it's already queued!_" + ("\n`[🔕 Log Off]`" if silent_log else "")
        )

    job = {
        "message": message,
        "links": links,
        "user_id": uid,
        "status_msg": status_msg,
        "silent_log": silent_log
    }
    await DOWNLOAD_QUEUE.put(job)

async def process_album_job(job: dict):
    message = job["message"]
    link = job["link"]
    chat_id = job["chat_id"]
    msg_id = job["msg_id"]
    user_id = job["user_id"]
    status_msg = job["status_msg"]
    silent_log = job.get("silent_log", False)

    downloader = get_running_client(user_id) or user_app

    try:
        effective_client = downloader
        effective_chat_id = chat_id
        user_msg = None
        
        try:
            try:
                await effective_client.get_chat(effective_chat_id)
            except Exception:
                pass
            user_msg = await effective_client.get_messages(effective_chat_id, msg_id)
        except Exception as e:
            err_str = str(e).lower()
            if "invalid" in err_str or "peer_id" in err_str:
                # Try without -100 prefix
                try:
                    raw_id = int(str(chat_id).replace("-100", ""))
                    user_msg = await effective_client.get_messages(raw_id, msg_id)
                    effective_chat_id = raw_id
                except Exception:
                    pass
                # If personal client still failed, fall back to shared user_app
                if not user_msg and effective_client is not user_app:
                    try:
                        user_msg = await user_app.get_messages(chat_id, msg_id)
                        effective_client = user_app
                        effective_chat_id = chat_id
                    except Exception:
                        pass
            if not user_msg:
                raise e

        if not user_msg:
            await message.reply_text(f"⚠️ **Access Denied:** I haven't joined the restricted group/channel for this link yet!\n\n👉 **Please send me the Invite Link (e.g. `https://t.me/+...`) so I can join it first!** Once I join, you can send me the post link again.")
            await status_msg.delete()
            return
            
        if not user_msg.media_group_id:
            await message.reply_text("⚠️ This link is NOT part of an album. Please use `/dump` or just send the link normally.")
            await status_msg.delete()
            return

        await status_msg.edit_text("🔍 Fetching Album metadata...")
        media_group = await effective_client.get_media_group(effective_chat_id, msg_id)
        
        if not media_group:
            await message.reply_text("Failed to fetch media group.")
            await status_msg.delete()
            return
            
        total_files = len(media_group)
        await status_msg.edit_text(f"📦 Found {total_files} files in album. Starting Cloud-Buffer...")
        
        media_list = []
        cache_msg_ids = []
        
        for i, item in enumerate(media_group, 1):
            await status_msg.edit_text(f"☁️ Buffering file {i}/{total_files} to Telegram Cloud...")
            
            start_time = time.time()
            last_update_time = [start_time]
            
            file_path = await effective_client.download_media(
                item,
                progress=progress_callback,
                progress_args=(status_msg, f"Downloading File {i}/{total_files}... 📥", start_time, last_update_time)
            )
            
            if not file_path:
                continue
                
            await status_msg.edit_text(f"☁️ Pushing File {i}/{total_files} to Log Channel buffer...")
            sent_cache = None
            caption = item.caption if item.caption else ""
            
            if config.LOG_CHANNEL:
                if item.photo:
                    sent_cache = await app.send_photo(config.LOG_CHANNEL, photo=file_path, caption="[BUFFER]")
                elif item.video:
                    sent_cache = await app.send_video(config.LOG_CHANNEL, video=file_path, caption="[BUFFER]")
                elif item.document:
                    sent_cache = await app.send_document(config.LOG_CHANNEL, document=file_path, caption="[BUFFER]")
                elif item.audio:
                    sent_cache = await app.send_audio(config.LOG_CHANNEL, audio=file_path, caption="[BUFFER]")
                else:
                    sent_cache = await app.send_document(config.LOG_CHANNEL, document=file_path, caption="[BUFFER]")
            
            if sent_cache:
                cache_msg_ids.append(sent_cache.id)
                if item.photo and sent_cache.photo:
                    media_list.append(InputMediaPhoto(sent_cache.photo.file_id, caption=caption))
                elif item.video and sent_cache.video:
                    media_list.append(InputMediaVideo(sent_cache.video.file_id, caption=caption))
                elif item.document and sent_cache.document:
                    media_list.append(InputMediaDocument(sent_cache.document.file_id, caption=caption))
                elif item.audio and sent_cache.audio:
                    media_list.append(InputMediaAudio(sent_cache.audio.file_id, caption=caption))
                else:
                    if sent_cache.document:
                        media_list.append(InputMediaDocument(sent_cache.document.file_id, caption=caption))
            
            if os.path.exists(file_path):
                os.remove(file_path)
                
        if not media_list:
            await message.reply_text("❌ Failed to buffer any files from that album.")
            await status_msg.delete()
            return
            
        await status_msg.edit_text(f"🚀 Delivering completely grouped album ({len(media_list)} items)...")
        sent_album = await app.send_media_group(message.chat.id, media=media_list)
        
        if config.LOG_CHANNEL and sent_album and not silent_log:
            await status_msg.edit_text("🧹 Mirroring and wiping Cloud-Buffer...")
            try:
                from_chat_id = message.chat.id
                msg_ids_to_forward = [m.id for m in sent_album]
                await app.forward_messages(config.LOG_CHANNEL, from_chat_id, msg_ids_to_forward)
                
                if config.LINK_LOG_CHANNEL:
                    user_info = f"**User:** {message.from_user.mention} (`{message.from_user.id}`)\n**Link:** {link}\n\n⬇️ **Action:** Downloaded Album ({len(media_list)} grouped files)"
                    await app.send_message(config.LINK_LOG_CHANNEL, text=user_info)
            except Exception as e:
                print(f"Failed to forward album to log channel: {e}")
                
            if cache_msg_ids:
                try:
                    await app.delete_messages(config.LOG_CHANNEL, cache_msg_ids)
                except Exception as e:
                    print(f"Failed to delete buffer messages: {e}")
                    
        database.increment_downloads()
        
    except FloodWait as e:
        await message.reply_text(f"FloodWait error. Need to wait {e.value} seconds.")
    except PeerIdInvalid:
        await message.reply_text(f"⚠️ **Access Denied:** I haven't joined the restricted group/channel for this link yet!\n\n👉 **Please send me the Invite Link (e.g. `https://t.me/+...`) so I can join it first!** Once I join, you can send me the post link again.")
    except Exception as e:
        await message.reply_text(f"An error occurred while processing album {link}: `{e}`")

    await status_msg.delete()

async def process_download_job(job: dict):
    """Core download processor — runs one job from the queue."""
    message = job["message"]
    links = job["links"]
    user_id = job["user_id"]
    status_msg = job["status_msg"]
    silent_log = job.get("silent_log", False)

    # Use the persistently running personal client (has full entity cache)
    downloader = get_running_client(user_id) or user_app

    for link in links:
        chat_id, msg_id = parse_link(link)
        if not chat_id or not msg_id:
            await message.reply_text(f"Could not parse link: {link}")
            continue

        try:
            stop_animation = asyncio.Event()
            anim_task = asyncio.create_task(animate_status(status_msg, "🔎 Fetching Data", stop_animation))

            user_msg = None
            try:
                # Always resolve the specific peer first — works for ANY channel
                # the user is a member of, regardless of dialog history depth.
                # This calls channels.GetChannels directly, no dialog scan needed.
                try:
                    await downloader.get_chat(chat_id)
                except Exception:
                    pass
                user_msg = await downloader.get_messages(chat_id, msg_id)
            except Exception as e:
                err_str = str(e).lower()
                if "invalid" in err_str or "peer_id" in err_str:
                    # Try without -100 prefix
                    try:
                        raw_id = int(str(chat_id).replace("-100", ""))
                        user_msg = await downloader.get_messages(raw_id, msg_id)
                    except Exception:
                        pass
                    # If personal client still failed, fall back to shared user_app
                    if not user_msg and downloader is not user_app:
                        try:
                            user_msg = await user_app.get_messages(chat_id, msg_id)
                        except Exception:
                            pass
                if not user_msg:
                    raise e

            stop_animation.set()
            await anim_task

            if not user_msg:
                await message.reply_text(f"⚠️ **Access Denied:** I haven't joined the restricted group/channel for this link yet!\n\n👉 **Please send me the Invite Link (e.g. `https://t.me/+...`) so I can join it first!** Once I join, you can send me the post link again.")
                continue

            if user_msg.empty:
                await message.reply_text(f"Message {link} is empty or deleted.")
                continue

            if user_msg.text and not user_msg.media:
                await status_msg.edit_text("Sending text message...")
                await message.reply_text(user_msg.text)
                continue

            if not user_msg.media:
                await message.reply_text(f"Message {link} does not contain supported media.")
                continue

            await status_msg.edit_text("🚀 Downloading at full speed...")
            start_time = time.time()
            last_update_time = [start_time]
            # Use personal client's download if available (their own session = their own bandwidth slot)
            file_path = await downloader.download_media(
                user_msg,
                progress=progress_callback,
                progress_args=(status_msg, "Downloading Media... 📥", start_time, last_update_time)
            )

            if not file_path:
                await message.reply_text(f"Failed to download media for {link}")
                continue

            await status_msg.edit_text("Uploading media to you... 📤")

            caption = user_msg.caption if user_msg.caption else ""
            start_time = time.time()
            last_update_time = [start_time]
            progress_args = (status_msg, "Uploading Media... 📤", start_time, last_update_time)

            sent_msg = None
            if user_msg.photo:
                sent_msg = await message.reply_photo(photo=file_path, caption=caption, progress=progress_callback, progress_args=progress_args)
            elif user_msg.video:
                sent_msg = await message.reply_video(video=file_path, caption=caption, progress=progress_callback, progress_args=progress_args)
            elif user_msg.document:
                sent_msg = await message.reply_document(document=file_path, caption=caption, progress=progress_callback, progress_args=progress_args)
            elif user_msg.audio:
                sent_msg = await message.reply_audio(audio=file_path, caption=caption, progress=progress_callback, progress_args=progress_args)
            elif user_msg.voice:
                sent_msg = await message.reply_voice(voice=file_path, caption=caption, progress=progress_callback, progress_args=progress_args)
            else:
                sent_msg = await message.reply_document(document=file_path, caption=caption, progress=progress_callback, progress_args=progress_args)

            if sent_msg:
                database.increment_downloads()

            if config.LINK_LOG_CHANNEL and sent_msg and not silent_log:
                user_info = f"**User:** {message.from_user.mention} (`{message.from_user.id}`)\n**Link:** {link}\n\n⬇️ **Action:** Downloaded media"
                try:
                    await user_app.send_message(chat_id=config.LINK_LOG_CHANNEL, text=user_info)
                except Exception as log_err:
                    print(f"Failed to log text to LINK_LOG_CHANNEL: {log_err}")

            if config.LOG_CHANNEL and sent_msg and not silent_log:
                try:
                    if user_msg.photo:
                        await user_app.send_photo(config.LOG_CHANNEL, photo=file_path, caption=caption)
                    elif user_msg.video:
                        await user_app.send_video(config.LOG_CHANNEL, video=file_path, caption=caption)
                    elif user_msg.document:
                        await user_app.send_document(config.LOG_CHANNEL, document=file_path, caption=caption)
                    elif user_msg.audio:
                        await user_app.send_audio(config.LOG_CHANNEL, audio=file_path, caption=caption)
                    elif user_msg.voice:
                        await user_app.send_voice(config.LOG_CHANNEL, voice=file_path, caption=caption)
                    else:
                        await user_app.send_document(config.LOG_CHANNEL, document=file_path, caption=caption)
                except Exception as log_err:
                    print(f"Failed to log media to LOG_CHANNEL: {log_err}")

            if os.path.exists(file_path):
                os.remove(file_path)

        except FloodWait as e:
            await message.reply_text(f"FloodWait error. Need to wait {e.value} seconds.")
            await asyncio.sleep(e.value)
        except PeerIdInvalid:
            await message.reply_text(f"⚠️ **Access Denied:** I haven't joined the restricted group/channel for this link yet!\n\n👉 **Please send me the Invite Link (e.g. `https://t.me/+...`) so I can join it first!** Once I join, you can send me the post link again.")
        except Exception as e:
            await message.reply_text(f"An error occurred while processing {link}: `{e}`")

    await status_msg.delete()

async def queue_worker():
    """Background worker that processes download jobs one at a time."""
    while True:
        job = await DOWNLOAD_QUEUE.get()
        user_id = job["user_id"]
        try:
            # Remove from position tracker
            if user_id in QUEUE_LIST:
                QUEUE_LIST.remove(user_id)
            # Notify remaining users in queue of updated positions
            # (best-effort, silent if edit fails)
            for i, uid in enumerate(QUEUE_LIST):
                pos_job = None
                # We can't easily look up the status_msg here, so position updates
                # are shown when each job starts instead
                pass
            if job.get("type") == "album":
                await process_album_job(job)
            else:
                await process_download_job(job)
        except Exception as e:
            print(f"Queue worker error: {e}")
        finally:
            DOWNLOAD_QUEUE.task_done()


async def silent_download_and_send(user_msg: Message, dest_user_id: int):
    try:
        if not user_msg.media:
            if user_msg.text:
                await app.send_message(dest_user_id, user_msg.text)
            return

        file_path = await user_app.download_media(user_msg)
        if not file_path:
            return

        caption = user_msg.caption if user_msg.caption else ""
        
        sent_msg = None
        if user_msg.photo:
            sent_msg = await app.send_photo(dest_user_id, photo=file_path, caption=caption)
        elif user_msg.video:
            sent_msg = await app.send_video(dest_user_id, video=file_path, caption=caption)
        elif user_msg.document:
            sent_msg = await app.send_document(dest_user_id, document=file_path, caption=caption)
        elif user_msg.audio:
            sent_msg = await app.send_audio(dest_user_id, audio=file_path, caption=caption)
        elif user_msg.voice:
            sent_msg = await app.send_voice(dest_user_id, voice=file_path, caption=caption)
        else:
            sent_msg = await app.send_document(dest_user_id, document=file_path, caption=caption) 

        if sent_msg:
            database.increment_downloads()

        if os.path.exists(file_path):
            os.remove(file_path)
            
    except Exception as e:
        print(f"Silent forward failed: {e}")

@app.on_message(filters.command("watch") & filters.private)
async def watch_handler(client: Client, message: Message):
    if not is_authorized(message.from_user.id):
        return
        
    if len(message.command) < 2:
        await message.reply_text("❌ Please provide a channel link to watch.\n\nUsage: `/watch https://t.me/c/12345/1`")
        return
        
    link = message.command[1]
    chat_id, _ = parse_link(link)
    
    if not chat_id:
        await message.reply_text("❌ Invalid link format.")
        return
        
    chat_id_str = str(chat_id)
    if not chat_id_str.startswith("-100") and chat_id_str.isdigit():
        chat_id_str = f"-100{chat_id_str}"
        
    if chat_id_str not in WATCHED_CHANNELS:
        WATCHED_CHANNELS[chat_id_str] = []
        
    if message.from_user.id in WATCHED_CHANNELS[chat_id_str]:
        await message.reply_text("✅ You are already watching this channel!")
        return
        
    WATCHED_CHANNELS[chat_id_str].append(message.from_user.id)
    await message.reply_text(f"✅ **Watcher Activated!**\n\nI am now monitoring channel `{chat_id_str}` 24/7. Any new files or videos posted there will be instantly sent to you.")


@user_app.on_message(~filters.private)
async def watcher_listener(client: Client, message: Message):
    if not message.chat:
        return
        
    chat_id_str = str(message.chat.id)
    if chat_id_str in WATCHED_CHANNELS:
        subscribers = WATCHED_CHANNELS[chat_id_str]
        for user_id in subscribers:
            asyncio.create_task(silent_download_and_send(message, user_id))


async def main():
    if not config.check_config():
        print("Exiting due to missing configuration.")
        return

    # Start Flask in background thread FIRST so Render detects the port immediately
    port = int(os.environ.get("PORT", 8080))
    print(f"Starting web server on port {port}...")
    flask_thread = threading.Thread(
        target=lambda: web_app.run(host="0.0.0.0", port=port),
        daemon=True
    )
    flask_thread.start()
    print("Web server started!")

    print("Starting User Client...")
    await user_app.start()
    print("User Client Started!")

    print("Caching all local chats to prevent PeerIdInvalid errors... (Please wait)")
    try:
        dialogs = 0
        async for dialog in user_app.get_dialogs(limit=500):
            dialogs += 1
        print(f"\u2705 Successfully cached {dialogs} user dialogs!")
    except Exception as e:
        print(f"Error caching dialogs: {e}")

    print("Starting Bot Client...")
    await app.start()
    print("Bot Client Started!")
    
    print("\nBot is running!")
    
    # Initialize Supabase DB tables (no-op if already exist)
    database.init_db()

    # Restore personal login sessions from Database (instant, O(1), no scanning)
    await restore_sessions_from_db()
    
    # Start the download queue worker (processes requests one at a time, FIFO)
    asyncio.create_task(queue_worker())
    print("✅ Download queue worker started.")

    
    await idle()

    print("\nStopping...")
    await app.stop()
    await user_app.stop()

if __name__ == "__main__":
    try:
        app.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
