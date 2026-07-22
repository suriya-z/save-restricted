<div align=" center\>

# ? RESTRICTED CONTENT SAVER & SWARM BOT

An ultra-fast, high-performance Telegram Restricted Content Saver powered by Distributed Swarm Session Pooling, Automatic 5-Minute Media Self-Destruction, and FFmpeg Video Processing.

[![Python](https://img.shields.io/badge/Python-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Pyrogram](https://img.shields.io/badge/Pyrogram-v2.0-26A5E4?style=for-the-badge&logo=telegram&logoColor=white)](https://docs.pyrogram.org)
[![FFmpeg](https://img.shields.io/badge/FFmpeg-Engine-0078D4?style=for-the-badge&logo=ffmpeg&logoColor=white)](https://ffmpeg.org)
[![Render](https://img.shields.io/badge/Render-Live_Deploy-46E3B7?style=for-the-badge&logo=render&logoColor=black)](https://render.com)

---

</div>

> [!IMPORTANT]
> **Privacy First**: All downloaded media files delivered to regular users are automatically purged after **5 minutes** (300 seconds).

---

## ? Core Capabilities

| Core Module | Functionality & Impact |
| :--- | :--- |
| **Bypass Engine** | Saves videos, audio, photos, & documents from restricted private channels where saving or forwarding is disabled. |
| **Auto-Destruct** | Automated 5-minute background timer purges delivered media to maintain chat privacy and conserve storage. |
| **FFmpeg Metadata** | Automatically extracts resolution, video duration, and generates crisp video thumbnails. |
| **Swarm Pool** | Multi-session user account pooling to balance download traffic and prevent rate limits. |
| **Timed Broadcast** | Owner broadcast tool supporting timed message pins and auto-unpinning (5m, 6hr, 2d). |
| **Vanishing Links** | User post-link messages vanish automatically as soon as the download job begins. |

---

## ?? System Architecture

`mermaid
graph LR
 subgraph Client Layer
 A[?? User Request] --> B[?? Bot Client]
 end
 
 subgraph Core Engine
 B --> C[?? Job Queue]
 C --> D[? Swarm User Pool]
 D --> E[?? Telegram Data Centers]
 E --> F[?? Local Temp Storage]
 F --> G[?? FFmpeg Metadata Engine]
 end
 
 subgraph Delivery & Lifecycle
 G --> H[?? Delivered Media]
 H --> I[? 5-Min Purge Timer]
 I --> J[??? Auto Self-Destruct]
 end
`

---

## ?? Command Center

<details>
<summary><b>?? Owner & Admin Control Center (Click to expand)</b></summary>

<br>

| Command | Syntax | Purpose |
| :--- | :--- | :--- |
| /cmds | /cmds | Display owner dashboard & command menu |
| /broadcast | /broadcast [duration] <text> | Broadcast message to all users & auto-pin (e.g. 5m, 2d) |
| /stats | /stats | Monitor server RAM, CPU, database & total download metrics |
| /users | /users | List registered user IDs |
| /ban | /ban <user_id> | Restrict user access |
| /unban | /unban <user_id> | Restore user access |
| /genkey | /genkey <tier> | Generate premium redeem license key |
| /donate_account | /donate_account | Add session string to Swarm Pool |

</details>

<details>
<summary><b>?? Standard User Commands (Click to expand)</b></summary>

<br>

| Command | Syntax | Purpose |
| :--- | :--- | :--- |
| /start | /start | Start bot & view quick-start instructions |
| /myplan | /myplan | View subscription plan tier & remaining quota |
| /redeem | /redeem <key> | Redeem premium subscription key |
| /login | /login | Connect personal Telegram account for private channel access |
| /logout | /logout | Remove personal Telegram account |
| /mysaved | /mysaved | Access saved download history |
| /dump | /dump <link> | Download range/batch of posts |
| /album | /album <link> | Download grouped media album |
| /watch | /watch <link> | Enable 24/7 channel auto-forwarder |

</details>

---

## ?? Environment Configuration

`ini
API_ID=1234567
API_HASH=your_api_hash_here
BOT_TOKEN=123456789:ABCdefGHIjklMNOpqrsTUVwxyZ
SESSION_STRING=your_pyrogram_v2_user_session_string
OWNER_ID=987654321
DATABASE_URL=mongodb+srv://... # Optional: defaults to local JSON storage
PORT=10000 # Optional: web server health check port
`

---

## ?? One-Click Deploy

[![Deploy to Render](https://render.com/images/deploy-to-render-button.svg)](https://render.com)

1. Fork this repository.
2. Create a new **Web Service** on Render.
3. Build Command: pip install -r requirements.txt
4. Start Command: python bot.py
5. Configure Environment Variables.

---

<div align=\center\>

Built for speed, efficiency, and privacy.

</div>
