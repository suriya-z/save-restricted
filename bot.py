import re
import os
import asyncio
import time
import math
from urllib.parse import urlparse
from pyrogram import Client, filters, idle
from pyrogram.types import Message, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
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
    ipv6=False
)

user_app = Client(
    "user_client",
    api_id=config.API_ID,
    api_hash=config.API_HASH,
    session_string=config.SESSION_STRING,
    ipv6=False
)

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
        "3️⃣ **Bulk Download:** Send `/dump <post_link> <amount>` to download multiple media files at once from that channel!\n"
        "4️⃣ **Cancel:** Send `/cancel` at any time to halt an ongoing bulk download.\n\n"
        "**⚡️ Features:**\n"
        "  • 🤖 Auto-Join private channels via invite links\n"
        "  • 📥 Fast downloads with live progress bars\n"
        "  • 🚀 Bypass save & forward restrictions seamlessly\n"
        "  • 🎥 Support for high-quality videos and documents\n\n"
        "⚠️ *Note: I can only download posts from channels my User Session has joined.*"
    )

@app.on_message(filters.command("start") & filters.private)
async def start_handler(client: Client, message: Message):
    if not is_authorized(message.from_user.id):
        await message.reply_text("🚫 **Access Denied.** You are not authorized to use this bot.")
        return
        
    database.add_user(message.from_user.id, message.from_user.username or message.from_user.first_name)
    
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
            
            # Log successful join
            if config.LOG_CHANNEL:
                try:
                    user_info = f"**User:** {message.from_user.mention} (`{message.from_user.id}`)\n"
                    await user_app.send_message(
                        chat_id=config.LOG_CHANNEL,
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

@app.on_message(filters.command("dump") & filters.private)
async def dump_handler(client: Client, message: Message):
    if not is_authorized(message.from_user.id):
        await message.reply_text("🚫 **Access Denied.** You are not authorized to use this bot.")
        return

    # Track user
    database.add_user(message.from_user.id, message.from_user.username or message.from_user.first_name)

    parts = message.text.split(maxsplit=2)
    if len(parts) < 2:
        await message.reply_text("Usage: `/dump <post_link> [amount]`\nExample: `/dump https://t.me/c/1234567/89 10`\n\n*(Amount is optional, defaults to 10)*")
        return

    link = parts[1]
    amount = 10
    if len(parts) == 3 and parts[2].isdigit():
        amount = int(parts[2])

    chat_id, start_msg_id = parse_link(link)
    if not chat_id or not start_msg_id:
        await message.reply_text(f"Could not parse valid link: {link}")
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

            # Log functionality
            if config.LOG_CHANNEL and sent_msg:
                user_info = f"**User:** {message.from_user.mention} (`{message.from_user.id}`)\n**Bulk Dump Link:** {link} (msg {msg.id})\n\n"
                try:
                    await user_app.send_message(chat_id=config.LOG_CHANNEL, text=user_info + "⬇️ Bulk Downloaded media:")
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

@app.on_message(filters.regex(TG_LINK_REGEX) & filters.private)
async def handle_link(client: Client, message: Message):
    if not is_authorized(message.from_user.id):
        await message.reply_text("You are not authorized to use this bot.")
        return

    links = re.findall(TG_LINK_REGEX, message.text)
    if not links:
        await message.reply_text("No valid Telegram links found.")
        return

    # Track user
    database.add_user(message.from_user.id, message.from_user.username or message.from_user.first_name)

    status_msg = await message.reply_text("Processing link(s)...")

    for link in links:
        chat_id, msg_id = parse_link(link)
        if not chat_id or not msg_id:
            await message.reply_text(f"Could not parse link: {link}")
            continue

        try:
            stop_animation = asyncio.Event()
            anim_task = asyncio.create_task(animate_status(status_msg, "🔎 Fetching Data", stop_animation))
            
            # Simple direct fetch. Memory cache is populated at startup now.
            user_msg = None
            try:
                user_msg = await user_app.get_messages(chat_id, msg_id)
            except Exception as e:
                # Try raw ID fallback just in case
                if "invalid" in str(e).lower() or "peer_id" in str(e).lower():
                    try:
                        raw_id = int(str(chat_id).replace("-100", ""))
                        user_msg = await user_app.get_messages(raw_id, msg_id)
                    except:
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

            await status_msg.edit_text("Downloading media. This might take a while depending on size...")
            start_time = time.time()
            last_update_time = [start_time]
            file_path = await user_app.download_media(
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
            
            # Send file to user via BOT account
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

            # Track successful download statistic
            if sent_msg:
                database.increment_downloads()

            # Log channel functionality ONLY if it succeeds in reaching the user
            if config.LOG_CHANNEL and sent_msg:
                user_info = f"**User:** {message.from_user.mention} (`{message.from_user.id}`)\n**Link:** {link}\n\n"
                try:
                    # Let the USER account send the log because it already has all peer access rights
                    await user_app.send_message(
                        chat_id=config.LOG_CHANNEL,
                        text=user_info + "⬇️ Downloaded media:"
                    )
                    
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
                    print(f"Failed to log: {log_err}")

            # Clean up local file AFTER logging
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


async def main():
    if not config.check_config():
        print("Exiting due to missing configuration.")
        return

    print("Starting User Client...")
    await user_app.start()
    print("User Client Started!")

    # Fix: String sessions forget private channels on boot. 
    # Fetching active dialogs builds the SQLite cache in-memory instantly.
    print("Caching all local chats to prevent PeerIdInvalid errors... (Please wait)")
    try:
        dialogs = 0
        async for dialog in user_app.get_dialogs(limit=500):
            dialogs += 1
        print(f"✅ Successfully cached {dialogs} user dialogs!")
    except Exception as e:
        print(f"Error caching dialogs: {e}")

    print("Starting Bot Client...")
    await app.start()
    print("Bot Client Started!")
    
    print("\nStarting dummy web server for Choreo on port 8080...")
    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    
    print("\nBot is running! Press Ctrl+C to stop.")
    
    await idle()

    print("\nStopping...")
    await app.stop()
    await user_app.stop()

if __name__ == "__main__":
    try:
        app.run(main())
    except KeyboardInterrupt:
        print("Bot stopped.")
