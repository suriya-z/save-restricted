<div align=" center\>

# ?? RESTRICTED CONTENT SAVER & SWARM BOT

![Python](https://img.shields.io/badge/Python-3.11%2B-blue?style=for-the-badge&logo=python&logoColor=white)
![Pyrogram](https://img.shields.io/badge/Framework-Pyrogram%20v2-orange?style=for-the-badge&logo=telegram&logoColor=white)
![FFmpeg](https://img.shields.io/badge/Media-FFmpeg-green?style=for-the-badge&logo=ffmpeg&logoColor=white)
![License](https://img.shields.io/badge/License-MIT-purple?style=for-the-badge)
![Status](https://img.shields.io/badge/Deployment-Render%20Live-brightgreen?style=for-the-badge)

**An ultra-advanced, high-performance Telegram Restricted Content Downloader bot with Distributed Swarm Session Pooling, Automatic 5-Minute Media Self-Destruction, FFmpeg Video Thumbnail Generation, and Owner Control Center.**

[Features](#-key-features) ? [Architecture](#-architecture--how-it-works) ? [Commands](#-command-cheat-sheet) ? [Deployment](#-deployment) ? [Environment Variables](#-environment-variables)

---

</div>

## ?? Key Features

| Feature | Description |
| :--- | :--- |
| ?? **Restricted Bypass** | Effortlessly download videos, photos, documents & audio from private/restricted channels where saving or forwarding is disabled. |
| ? **5-Min Media Auto-Delete** | Downloaded media sent to regular users self-destructs after 5 minutes for maximum privacy and zero storage waste. |
| ?? **FFmpeg Metadata Engine** | Automatic resolution, duration, and high-quality thumbnail extraction for all downloaded video formats. |
| ?? **Distributed Swarm Pool** | Multi-session userpool network that distributes download loads across multiple Telegram user instances. |
| ?? **Timed Broadcasts & Pins** | Broadcast messages to all users with optional duration limits (5m, 6hr, 2d) and auto-unpinning timers. |
| ?? **Auto-Vanishing Links** | User link requests automatically delete upon download start to keep user chat clean. |
| ?? **Owner Control Center** | Dedicated /cmds dashboard for system statistics, user management, key generation, and swarm control. |
| ?? **Tiered Subscriptions** | Built-in key generation (/genkey) and redemption system (/redeem) for premium user quotas. |

---

## ?? Architecture & How It Works

`mermaid
graph TD
 User([?? User]) -->|1. Sends Post Link| Bot[?? Telegram Bot Client]
 Bot -->|2. Cleans & Queues Job| Queue[(?? Download Queue)]
 Queue -->|3. Fetches Media| Swarm[? Swarm User Accounts Pool]
 Swarm -->|4. Accesses Private Channel| TG[?? Telegram Servers]
 TG -->|5. Downloads Media File| Local[?? Local Temp Storage]
 Local -->|6. FFmpeg Metadata & Thumb| FFmpeg[?? FFmpeg / FFprobe Engine]
 FFmpeg -->|7. Sends Processed Media| Bot
 Bot -->|8. Delivers to User| User
 Bot -->|9. Schedules 5-Min Timer| Timer[? Auto Self-Destruct 300s]
 Timer -->|10. Purges Media Message| User
`

---

## ?? Command Cheat Sheet

### ?? Admin / Owner Commands (is_admin)

`ash
/cmds # Open the Owner Control Center menu
/broadcast [duration] <text> # Broadcast text/reply to all users & pin (e.g. /broadcast 5m Hello, /broadcast 2d Maintenance)
/stats # View system, database metrics & download counts
/users # List all registered user IDs
/ban <user_id> # Ban user from accessing the bot
/unban <user_id> # Restore user access
/genkey <tier> # Generate a single-use premium redeem key
/donate_account # Add a new Telegram user session string to the Swarm Network
`

### ?? User Commands

`ash
/start # Initialize bot & view usage guide
/myplan # Check current plan tier & remaining daily quota
/redeem <key> # Redeem a premium subscription key
/login # Connect personal Telegram session for private channel access
/logout # Remove connected personal Telegram session
/mysaved # View saved post history
/dump <link> # Dump batch post range
/album <link> # Download grouped media album
/watch <link> # Auto-forward new channel posts 24/7
`

---

## ?? Environment Variables

| Key | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| API_ID | Yes | ? | Telegram API ID from [my.telegram.org](https://my.telegram.org) |
| API_HASH | Yes | ? | Telegram API Hash from [my.telegram.org](https://my.telegram.org) |
| BOT_TOKEN | Yes | ? | Telegram Bot Token from [@BotFather](https://t.me/BotFather) |
| SESSION_STRING | Yes | ? | Primary Pyrogram v2 User Session String |
| OWNER_ID | Yes | ? | Telegram Numeric User ID of the Bot Owner |
| DATABASE_URL | No | local JSON | MongoDB connection string (falls back to local JSON database) |
| PORT | No | 10000 | Web server port for health checks / Render hosting |

---

## ?? One-Click Deployment

### Deploy on Render

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

1. Fork this repository to your GitHub account.
2. Create a new **Web Service** on Render connected to your repository.
3. Set Environment to **Python 3**.
4. Set Build Command: pip install -r requirements.txt
5. Set Start Command: python bot.py
6. Add all required [Environment Variables](#%EF%B8%8F-environment-variables).

---

## ?? Local Setup

`ash
# Clone the repository
git clone https://github.com/suriya-z/save-restricted.git
cd save-restricted

# Install dependencies
pip install -r requirements.txt

# Create .env file with your credentials
cp .env.example .env

# Run the bot
python bot.py
`

---

<div align=\center\>

Crafted with ?? for High-Performance Restricted Content Management.

</div>
