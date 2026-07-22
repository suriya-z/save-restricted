<div align=" center\>

# RESTRICTED CONTENT SAVER & SWARM BOT

An ultra-fast, high-performance Telegram Restricted Content Downloader powered by Distributed Swarm Session Pooling, Automatic 5-Minute Media Self-Destruction, and FFmpeg Video Processing.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Pyrogram](https://img.shields.io/badge/Pyrogram-v2.0-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://docs.pyrogram.org)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Engine-0078D4?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://ffmpeg.org)
[![Render](https://img.shields.io/badge/Render-Live_Deploy-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://render.com)

---

</div>

> [!IMPORTANT]
> **Privacy Policy**: All media files downloaded by regular users automatically self-destruct after **5 minutes** (300 seconds). Owner downloads are exempt.

---

## Core Capabilities

| Capability | Description |
| :--- | :--- |
| **Restricted Saver** | Downloads restricted videos, photos, documents & audio from private channels/groups. |
| **5-Min Purge** | Background scheduler automatically purges delivered media after 5 minutes. |
| **FFmpeg Processor** | Auto-extracts video duration, width, height, and generates clean video thumbnail previews. |
| **Swarm Session Pool** | Distributes download traffic across multiple Telegram user accounts to eliminate rate limits. |
| **Timed Broadcast** | Owner broadcast with duration timers (5m, 6hr, 2d) and automated unpinning. |
| **Auto-Vanishing Links** | User link messages vanish as soon as the download task begins. |

---

## System Workflow

`
 [ User Request ] ??? [ Bot Client ] ??? [ Download Queue ] ??? [ Swarm User Pool ]
 ?
 [ Auto-Destruct (5m) ] ??? [ Delivered Media ] ??? [ FFmpeg Engine ] ??
`

---

## Command Reference

### Owner Commands (is_admin)

| Command | Description |
| :--- | :--- |
| /cmds | Display owner dashboard & command menu |
| /broadcast [duration] <text> | Broadcast message to all users & auto-pin (5m, 6hr, 2d) |
| /stats | View system resource usage, database metrics & download counts |
| /users | List all registered user IDs |
| /ban <user_id> | Ban user from accessing the bot |
| /unban <user_id> | Restore user access |
| /genkey <tier> | Generate premium redeem license key |
| /donate_account | Add Telegram account session string to Swarm Pool |

### User Commands

| Command | Description |
| :--- | :--- |
| /start | Start bot & view usage guide |
| /myplan | View current subscription plan & remaining quota |
| /redeem <key> | Redeem premium key |
| /login | Connect personal Telegram session for private channels |
| /logout | Disconnect personal Telegram session |
| /mysaved | Access saved download history |
| /dump <link> | Download range/batch of posts |
| /album <link> | Download grouped media album |
| /watch <link> | Auto-forward new channel posts 24/7 |

---

## Environment Variables

| Variable | Required | Description |
| :--- | :---: | :--- |
| API_ID | Yes | Telegram API ID from [my.telegram.org](https://my.telegram.org) |
| API_HASH | Yes | Telegram API Hash from [my.telegram.org](https://my.telegram.org) |
| BOT_TOKEN | Yes | Bot Token from [@BotFather](https://t.me/BotFather) |
| SESSION_STRING | Yes | Primary Pyrogram v2 User Session String |
| OWNER_ID | Yes | Numeric User ID of the Bot Owner |
| DATABASE_URL | No | MongoDB URL (falls back to local JSON database) |
| PORT | No | Web server port for health checks (10000) |

---

## One-Click Deployment

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

1. Fork this repository.
2. Create a new **Web Service** on Render connected to your repo.
3. Build Command: pip install -r requirements.txt
4. Start Command: python bot.py
5. Configure Environment Variables.

---

<div align=\center\>

Built for high performance, reliability, and privacy.

</div>
