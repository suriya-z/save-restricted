import asyncio

# CRITICAL: Create an event loop BEFORE importing bot.py
# Pyrogram's sync.py calls asyncio.get_event_loop() at import time.
asyncio.set_event_loop(asyncio.new_event_loop())

import threading
from bot import web_app, main

def start_bot():
    """Run the Pyrogram bot in a background thread with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        print("Bot thread: Starting Pyrogram...")
        loop.run_until_complete(main())
    except Exception as e:
        print(f"Bot thread crashed: {e}")
        import traceback
        traceback.print_exc()
    finally:
        loop.close()

# Start bot immediately (works when gunicorn uses --preload or 1 worker)
bot_thread = threading.Thread(target=start_bot, daemon=True)
bot_thread.start()
print("Bot background thread launched.")

# Expose the Flask app for gunicorn
application = web_app
