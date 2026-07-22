<div align=" center\>

![Header](https://capsule-render.vercel.app/api?type=rect&color=0:090d16,50:0f172a,100:020617&height=160&section=header&text=RESTRICTED%20CONTENT%20SAVER&fontSize=32&fontColor=38bdf8)

[![Typing SVG](https://readme-typing-svg.demolab.com?font=Fira+Code&size=18&pause=1000&color=38BDF8&center=true&vcenter=true&width=650&height=40&lines=%3E+INITIALIZING+PROTOCOL%3A+RESTRICTED_SAVER_v2.0;%3E+SWARM_NETWORK%3A+ACTIVE+%5BMULTI-SESSION+NODE+POOL%5D;%3E+STORAGE_POLICY%3A+300s+AUTO-PURGE+ENABLED;%3E+MEDIA_ENGINE%3A+FFMPEG_HARDWARE_ACCELERATED)](https://git.io/typing-svg)

![Status](https://img.shields.io/badge/SYSTEM_STATUS-ONLINE-10B981?style=for-the-badge&logo=prometheus&logoColor=white)
![Security](https://img.shields.io/badge/AUTO_PURGE-5_MINUTES-EF4444?style=for-the-badge&logo=shield&logoColor=white)
![Engine](https://img.shields.io/badge/ENGINE-PYROGRAM_v2-2563EB?style=for-the-badge&logo=telegram&logoColor=white)

---

</div>

> [!IMPORTANT]
> **Zero-Trace Protocol**: Downloaded media sent to regular users is automatically wiped after **5 minutes** (300 seconds).

---

## ?? System Runtime Preview

`ash
???(operator?swarm)-[~/save-restricted]
??$ python bot.py --swarm-mode --auto-purge 300
[+] Initializing Swarm Network Pool (Active Nodes: 4)... OK
[+] Queue Worker Initialized | Concurrency Limit: 16
[+] Auto-Purge Lifecycle Scheduler: Registered (300s Delay)
[+] FFmpeg Metadata & Thumbnail Extraction: Armed
[?] Restricted Content Saver Engine Online & Listening for Links!
`

---

## ? Core Modules

| Module | Operational Scope |
| :--- | :--- |
| **Restricted Saver** | Bypasses save/forward restrictions on private Telegram channels and groups. |
| **Auto-Destruct Engine** | Background scheduler purges delivered media after 5 minutes (300s). |
| **FFmpeg Probe** | Extracts duration, resolution, and generates crisp video thumbnail previews. |
| **Swarm Network** | Distributed multi-session account pool balancing heavy download loads. |
| **Timed Broadcast** | Owner broadcast with duration timers (5m, 6hr, 2d) and auto-unpinning. |
| **Vanishing Links** | User link messages self-delete automatically upon download start. |

---

## ?? System Pipeline

| Step | Component | Action |
| :---: | :--- | :--- |
| **1** | **User Ingestion** | User sends post link -> Bot validates link & enqueues job |
| **2** | **Swarm Retrieval** | Swarm Account Pool downloads media stream from Telegram servers |
| **3** | **FFmpeg Engine** | Probes video duration, width, height & extracts thumbnail frame |
| **4** | **Delivery** | Bot delivers processed media to User in private DM |
| **5** | **Auto-Purge** | Background timer purges media message after 5 minutes |

---

## ?? Command Center

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

## ?? Environment Variables

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

## ?? One-Click Deployment

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
