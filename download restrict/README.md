# Restricted Content Downloader Bot

This bot lets you download posts (videos, documents, photos) from Telegram channels or groups that have restricted saving and forwarding.

It works by using a real Telegram User account (which must be a member of the restricted channel) to download the media locally, and then uses a Bot account to send that media back to you in private DMs.

## Prerequisites

1.  **Python 3.8+**
2.  **API ID and API Hash**: Get these from [https://my.telegram.org/apps](https://my.telegram.org/apps).
3.  **Bot Token**: Get this by creating a bot via [@BotFather](https://t.me/BotFather).
4.  A Telegram User account that is a member of the restricted group/channel you want to download from.

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Generate a String Session

You need to authorize the bot to act as your User account. Run the session generator script:

```bash
python generate_session.py
```

It will ask you for your `API_ID`, `API_HASH`, phone number, and OTP. Follow the prompts. At the end, it will print a long string. **Save this `SESSION_STRING` safely.** It provides full access to your account.

### 3. Configure the Bot

Create a file named `.env` in this directory (`restricted_downloader_bot/.env`) and add the following:

```env
API_ID=your_api_id_here
API_HASH=your_api_hash_here
BOT_TOKEN=your_bot_token_from_botfather
SESSION_STRING=your_generated_string_session

# Optional: Restrict bot usage to specific Telegram User IDs (yours).
# If left empty, anyone can use the bot.
OWNER_ID=your_telegram_user_id
```

*You can get your Telegram User ID from bots like @userinfobot.*

### 4. Run the Bot

```bash
python bot.py
```

### 5. Usage

1. Open a chat with your newly created Bot on Telegram.
2. Send `/start`.
3. Send a link to a restricted post.
   - Example private link: `https://t.me/c/123456789/456`
   - Example public link: `https://t.me/channelname/789`
4. The bot (via the user account) will fetch the media and send it to you.
