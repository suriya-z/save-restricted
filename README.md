<div align="center">

![Header Banner](https://capsule-render.vercel.app/api?type=waving&color=0:0d1117,50:161b22,100:21262d&height=180&section=header&text=RESTRICTED%20CONTENT%20SAVER&fontSize=34&fontColor=58a6ff)

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Pyrogram](https://img.shields.io/badge/Pyrogram-v2.0-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://docs.pyrogram.org)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-Supabase-336791?style=for-the-badge&logo=postgresql&logoColor=white)](https://supabase.com)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Engine-0078D4?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://ffmpeg.org)
[![Render](https://img.shields.io/badge/Render-Live_Deploy-46E3B7?style=for-the-badge&logo=render&logoColor=white)](https://render.com)

---

</div>

> [!IMPORTANT]
> **Zero-Trace Protocol**: Downloaded media files delivered to regular users automatically self-destruct after **5 minutes** (300 seconds). Owner downloads are exempt.

---

## Core Capabilities

| Module | Operational Scope |
| :--- | :--- |
| **MediaPipeline** | Zero-Byte Cloud Cache intercept, RAM-only streaming ($\le 75\text{MB}$), and Hydra multi-connection sharding ($> 75\text{MB}$). |
| **AccessEngine** | Enforces Owner God Mode bypass, Gold tier feature locks (`/album`, `/dump`), and Free single/daily limits. |
| **Swarm Session Pool** | Multiplexes download traffic across active donated Telegram accounts with automated FloodWait backoff. |
| **Auto-Destruct Engine** | Background scheduler automatically purges delivered media after 300 seconds. |
| **FFmpeg Processor** | Extracts duration, resolution, and generates crisp video thumbnail previews. |
| **Timed Broadcast** | Owner broadcast with duration timers (5m, 6hr, 2d) and auto-unpinning. |
| **Vanishing Links** | User post-link messages self-delete automatically upon download start. |

---

## System Architecture & Pipeline

| Step | Component | Operational Details |
| :---: | :--- | :--- |
| **01** | **Ingestion** | Post link received $\rightarrow$ Validated & enqueued in Async Download Queue |
| **02** | **Cache Intercept** | Checks `LOG_CHANNEL` for identical post $\rightarrow$ Instant server-side 0-byte copy |
| **03** | **Swarm Retrieval** | Active Swarm Account fetches media stream from Telegram servers (RAM pipe or Hydra) |
| **04** | **FFmpeg Processing** | Probes video duration, resolution & extracts video thumbnail frame |
| **05** | **Delivery & Mirror** | Bot uploads & delivers media to user; mirrors to `LOG_CHANNEL` for future cache hits |
| **06** | **Zero-Trace Purge** | Automated 300s timer purges delivered media from user chat |

---

## Quick Start (Local Setup)

1. **Clone the repository:**
   ```bash
   git clone https://github.com/suriya-z/save-restricted.git
   cd save-restricted
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure Environment:**
   ```bash
   cp .env.example .env
   ```
   Fill in your API credentials and Supabase database URL in `.env`.

4. **Generate User Session String (if needed):**
   ```bash
   python generate_session.py
   ```
   Follow the interactive terminal prompts and copy the output into `SESSION_STRING` in `.env`.

5. **Run the Test Suite:**
   ```bash
   python -m pytest tests/ -v
   ```

6. **Launch the Bot:**
   ```bash
   python bot.py
   ```

---

## Environment Variables

| Variable | Required | Default | Description |
| :--- | :---: | :---: | :--- |
| `API_ID` | **Yes** | — | Telegram API ID from [my.telegram.org](https://my.telegram.org) |
| `API_HASH` | **Yes** | — | Telegram API Hash from [my.telegram.org](https://my.telegram.org) |
| `BOT_TOKEN` | **Yes** | — | Telegram Bot Token from [@BotFather](https://t.me/BotFather) |
| `SESSION_STRING` | **Yes** | — | Primary Pyrogram v2 User Session String (`python generate_session.py`) |
| `SUPABASE_DB_URL` | **Yes** | — | Supabase / PostgreSQL Connection URI (`postgresql://postgres:...`) |
| `OWNER_IDS` | No | — | Comma-separated numeric User IDs with permanent Owner God Mode |
| `LOG_CHANNEL` | Recommended | — | Private channel ID (`-100...`) for zero-byte cache lookups & album buffers |
| `LINK_LOG_CHANNEL`| No | — | Private channel ID (`-100...`) for link metadata audit logging |
| `PORT` | No | `8080` | Keep-alive health check server port for Render / Docker deployments |

---

## Command Reference

### Owner Commands (`is_admin`)

| Command | Description |
| :--- | :--- |
| `/cmds` | Display owner dashboard & command menu |
| `/broadcast [duration] <text>` | Broadcast message to all users & auto-pin (5m, 6hr, 2d) |
| `/stats` | View server CPU, RAM, database metrics & download counts |
| `/users` | List all registered user IDs |
| `/ban <user_id>` | Ban user from accessing the bot |
| `/unban <user_id>` | Restore user access |
| `/genkey <tier>` | Generate premium redeem license key |
| `/donate_account` | Add Telegram session string to Swarm Pool |

### User Commands

| Command | Description |
| :--- | :--- |
| `/start` | Start bot & view quick-start instructions |
| `/myplan` | View subscription plan & remaining quota |
| `/redeem <key>` | Redeem premium license key |
| `/login` | Connect personal Telegram session |
| `/logout` | Remove personal Telegram session |
| `/mysaved` | View saved download history |
| `/dump <link>` | Batch download post range (Gold tier exclusive) |
| `/album <link>` | Download grouped media album (Gold tier exclusive) |
| `/watch <link>` | Enable 24/7 channel auto-forwarder |

---

## One-Click Deployment (Render)

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

1. Fork this repository to your GitHub account.
2. In the Render Dashboard, select **New +** $\rightarrow$ **Web Service**.
3. Connect your repository.
4. Set the following configuration:
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python bot.py`
5. Under **Environment Variables**, add all required variables from [Environment Variables](#environment-variables).
6. Deploy! Render will detect the keep-alive health check on port `8080`.

---

<div align="center">

High-Performance Restricted Content Management Engine.

</div>
