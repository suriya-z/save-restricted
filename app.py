import threading
import asyncio
from bot import web_app, main

def start_bot():
    """Run the Pyrogram bot in a separate thread with its own event loop."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        loop.run_until_complete(main())
    except Exception as e:
        print(f"Bot error: {e}")
    finally:
        loop.close()

# Start the Telegram bot in the background when gunicorn loads this module
bot_thread = threading.Thread(target=start_bot, daemon=True)
bot_thread.start()

# Expose the Flask app for gunicorn
application = web_app
