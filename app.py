import asyncio

# CRITICAL: Create an event loop BEFORE importing bot.py
# Pyrogram's sync.py calls asyncio.get_event_loop() at import time,
# which fails in Python 3.10+ if no loop exists.
asyncio.set_event_loop(asyncio.new_event_loop())

import threading
from bot import web_app, main

def start_bot():
    """Run the Pyrogram bot in a background thread with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except Exception as e:
        print(f"Bot crashed: {e}")
    finally:
        loop.close()

# Start the Telegram bot in the background when gunicorn loads this module
bot_thread = threading.Thread(target=start_bot, daemon=True)
bot_thread.start()

# Expose the Flask app for gunicorn
application = web_app
