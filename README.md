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
> **Zero-Trace Protocol**: Downloaded media sent to regular users is automatically wiped after **5 minutes** (300 seconds).

---

## System Runtime Preview

`ash
[+] Initializing Swarm Network Pool (Active Nodes: 4)... OK
[+] Queue Worker Initialized | Concurrency Limit: 16
[+] Auto-Purge Lifecycle Scheduler: Registered (300s Delay)
[+] FFmpeg Metadata & Thumbnail Extraction: Armed
[*] Restricted Content Saver Engine Online & Listening for Links!
`

---

## Core Capabilities

| Module | Operational Scope |
| :--- | :--- |
| **Restricted Saver** | Bypasses save/forward restrictions on private Telegram channels and groups. |
| **Auto-Destruct Engine** | Background scheduler purges delivered media after 5 minutes (300s). |
| **FFmpeg Probe** | Extracts duration, resolution, and generates crisp video thumbnail previews. |
| **Swarm Network** | Distributed multi-session account pool balancing heavy download loads. |
| **Timed Broadcast** | Owner broadcast with duration timers (5m, 6hr, 2d) and auto-unpinning. |
| **Vanishing Links** | User post-link messages self-delete automatically upon download start. |

---

## System Architecture & Workflow

| Phase | System Module | Operational Mechanics |
| :---: | :--- | :--- |
| **01** | **Ingestion** | Post link received -> Validated & enqueued in Async Download Queue |
| **02** | **Swarm Retrieval** | Active Swarm Account fetches media stream from Telegram servers |
| **03** | **FFmpeg Processing** | Probes video duration, resolution & extracts video thumbnail frame |
| **04** | **Delivery** | Bot uploads & delivers processed media to User in private DM |
| **05** | **Zero-Trace Purge** | Automated 300s timer purges delivered media from user chat |

---

## Command Reference

### Owner Commands (is_admin)

| Command | Description |
| :--- | :--- |
| /cmds | Display owner dashboard & command menu |
| /broadcast [duration] <text> | Broadcast message to all users & auto-pin (5m, 6hr, 2d) |
| /stats | View server CPU, RAM, database metrics & download counts |
| /users | List all registered user IDs |
| /ban <user_id> | Ban user from accessing the bot |
| /unban <user_id> | Restore user access |
| /genkey <tier> | Generate premium redeem license key |
| /donate_account | Add Telegram session string to Swarm Pool |

### User Commands

| Command | Description |
| :--- | :--- |
| /start | Start bot & view quick-start instructions |
| /myplan | View subscription plan & remaining quota |
| /redeem <key> | Redeem premium license key |
| /login | Connect personal Telegram session |
| /logout | Remove personal Telegram session |
| /mysaved | View saved download history |
| /dump <link> | Batch download post range |
| /album <link> | Download grouped media album |
| /watch <link> | Enable 24/7 channel auto-forwarder |

---

## Environment Variables

| Variable | Required | Description |
| :--- | :---: | :--- |
| API_ID | Yes | Telegram API ID from my.telegram.org |
| API_HASH | Yes | Telegram API Hash from my.telegram.org |
| BOT_TOKEN | Yes | Bot Token from @BotFather |
| SESSION_STRING | Yes | Primary Pyrogram v2 User Session String |
| OWNER_ID | Yes | Numeric User ID of the Bot Owner |
| DATABASE_URL | No | MongoDB Connection String (falls back to local JSON) |
| PORT | No | Health check port (10000) |

---

## One-Click Deployment

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

1. Fork this repository.
2. Create a new **Web Service** on Render.
3. Build Command: pip install -r requirements.txt
4. Start Command: python bot.py
5. Configure Environment Variables.

---

<div align=\center\>

High-Performance Restricted Content Management.

</div>
