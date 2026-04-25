import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID", "0"))
API_HASH = os.getenv("API_HASH", "")
BOT_TOKEN = os.getenv("BOT_TOKEN", "")
SESSION_STRING = os.getenv("SESSION_STRING", "")

# Hitter API Settings
HITTER_API_KEY = os.getenv("HITTER_API_KEY", "hitchk_e1b463dd1fe151d5683596b33877cd946b2a75ae1549cd74")
HITTER_API_URL = os.getenv("HITTER_API_URL", "https://hitter1month.replit.app")

# Channel where downloaded files are logged
LOG_CHANNEL_STR = os.getenv("LOG_CHANNEL", "")
LOG_CHANNEL = int(LOG_CHANNEL_STR.strip()) if LOG_CHANNEL_STR else None

# Channel where user metadata and post links are logged
LINK_LOG_CHANNEL_STR = os.getenv("LINK_LOG_CHANNEL", "")
LINK_LOG_CHANNEL = int(LINK_LOG_CHANNEL_STR.strip()) if LINK_LOG_CHANNEL_STR else None

# Optional: List of user IDs allowed to use the bot
# Comma separated list of integers
OWNER_ID_STR = os.getenv("OWNER_ID", "")
OWNER_IDS = [int(i.strip()) for i in OWNER_ID_STR.split(",") if i.strip()] if OWNER_ID_STR else []

def check_config():
    missing = []
    if not API_ID:
        missing.append("API_ID")
    if not API_HASH:
        missing.append("API_HASH")
    if not BOT_TOKEN:
        missing.append("BOT_TOKEN")
    if not SESSION_STRING:
        missing.append("SESSION_STRING")
    
    if missing:
        print(f"Error: Missing following environment variables: {', '.join(missing)}")
        print("Please set them in a .env file or environment variables.")
        return False
    return True
