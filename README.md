# PitchFlow — Autonomous Music PR Studio 🎵✉️

> **The God-Tier Cold Outreach & Curator CRM for Indie Artists & Labels**  
> Crafted with Apple Human Interface Guidelines (HIG) aesthetics, intelligent CRM pipelines, deliverability safeguards, and zero-setup configuration.

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110%2B-009688.svg)](https://fastapi.tiangolo.com)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED.svg)](https://docker.com)
[![Tests](https://img.shields.io/badge/Tests-19%2F19%20Passing-emerald.svg)](tests/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

---

## 🌟 Overview

**PitchFlow** is a modern, enterprise-grade cold email automation suite and visual CRM designed specifically for independent music artists, managers, and labels. It replaces costly, complex SaaS platforms (like Lemlist, Mailchimp, or Woodpecker) while landing directly into the **Primary Inbox** using genuine Gmail SMTP delivery, randomized human-jitter dispatching, and invisible 1x1 open-tracking pixels.

Every setting, credential, pitch template, and curator contact can be managed entirely through the interactive Web Dashboard — **no `.env` file editing or terminal restarts required.**

---

## ✨ Key Features

### 🎨 Apple Cupertino Human Interface Design
- **Obsidian Dark Canvas & Frosted Glass**: Built on a luxury `#060609` obsidian palette with multi-layered translucency (`backdrop-filter: blur(28px) saturate(190%)`).
- **Apple Typography Stack**: Native San Francisco and Inter typographic hierarchy with calibrated letter tracking.
- **Fluid Micro-Interactions**: Tactile button presses, smooth segmented navigation, mobile-responsive sliding drawer, and password visibility toggles.

### ✍️ Interactive Pitch Composer & Template Studio
- **Dual-Mode Workspace**: Seamlessly switch between **Live Preview** (Apple/Gmail simulation with 1x1 tracking pixel indicator) and **Edit Pitch & Template**.
- **Live Editable Subject Line**: Refine headline hooks directly in the previewer with instant token interpolation.
- **Quick-Insert Token Chips**: One-click tags for `{{First_Name}}`, `{{Track_Name}}`, `{{Stream_Link}}`, `{{Artist_Bio_Link}}`, `{{Publication}}`, `{{Recent_Article}}`, and `{Spintax}`.
- **Persistent Template Management**: Save custom templates permanently to disk or reset back to stock in one click.

### 📋 Universal Clipboard & Multi-Delimiter CSV Import
- **Google Sheets & Excel Ready**: Automatically detects tab delimiters (`\t`) when copying directly from spreadsheets, as well as commas, semicolons, and pipes.
- **Fuzzy Header Matching**: Case-insensitive matching for `Name`, `Email`, `Publication`, `Persona`, and `Recent Work`.
- **Headerless Extraction**: Scans unformatted rows and extracts valid email addresses automatically.
- **Smart Lead Enrichment**: Duplicate contacts are updated with newly provided articles and outlets instead of being skipped.

### 🛑 Deliverability Safeguards & Weekend Blocker
- **The Weekend Blocker**: Automatically pauses batch dispatch and follow-ups on Saturdays and Sundays to prevent pitches from being buried in Monday morning trash. Includes a manual override toggle.
- **Human Jitter Simulation**: Randomized 3 to 7 minute delays between successive emails to mimic authentic human sending behavior.
- **Daily Quota Management**: Enforces strict configurable daily send caps (default: 30/day) with real-time visual progress gauges.
- **Anti-Attachment Shield**: Promotes deliverability by steering users toward cloud press kits and private streaming links instead of heavy MP3 attachments.

### 🚫 IMAP Opt-Out & Auto-Blacklisting Engine
- Scans incoming replies in real-time via Gmail IMAP.
- Detects opt-out keywords (`"unsubscribe"`, `"remove me"`, `"pass"`, `"stop emailing"`) and automatically transitions the contact to **Blacklisted 🚫** to safeguard domain health.

### 🔐 Zero-Setup In-App Credential Vault
- Enter Gmail address, Google App Password, and Notion API credentials directly inside the UI.
- **Instant SMTP Verification**: Automatically saves newly entered credentials and dispatches a live diagnostic test email to your Gmail address with one click.

---

## 🏗️ Architecture

```
                                  +-----------------------------+
                                  |      PitchFlow Web UI         |
                                  |   (Cupertino Glassmorphism) |
                                  +--------------+--------------+
                                                 |
                                     REST API / WebSockets
                                                 |
                                  +--------------v--------------+
                                  |     FastAPI Orchestrator    |
                                  +---+----------+----------+---+
                                      |          |          |
            +-------------------------+          |          +-------------------------+
            |                                    |                                    |
+-----------v-----------+            +-----------v-----------+            +-----------v-----------+
|    Config Vault       |            |   Dispatch Engine     |            |      CRM Storage      |
|  (data/app_config)    |            |  - Spintax Generator  |            |  - Local JSON Store   |
|  - Gmail SMTP / IMAP  |            |  - Human Jitter Delays|            |  - Notion Cloud Sync  |
|  - Quota Safeguards   |            |  - Weekend Blocker    |            |  - Pipeline Kanban    |
+-----------------------+            +-----------+-----------+            +-----------------------+
                                                 |
                                  +--------------v--------------+
                                  |   Gmail SMTP & Vercel Pixel |
                                  |   Tracking & IMAP Scanner   |
                                  +-----------------------------+
```

---

## 🚀 Quickstart Guide

### Option 1: 1-Click Windows Launcher
Double-click:
```text
Launch-PR-Bot.bat
```
Your browser will automatically launch **`http://localhost:8000`**.

---

### Option 2: Run via Python CLI
1. **Clone & enter repository**:
   ```bash
   git clone https://github.com/your-username/pr-outreach-automator.git
   cd pr-outreach-automator
   ```

2. **Create & activate virtual environment**:
   ```bash
   python -m venv venv
   # Windows:
   .\venv\Scripts\activate
   # macOS / Linux:
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Start the studio**:
   ```bash
   python main.py gui
   ```

---

### Option 3: Docker & Docker Compose
Run the entire studio in an isolated container:
```bash
docker compose up -d
```
Access the studio at `http://localhost:8000`.

---

## ⚙️ In-App Setup in 60 Seconds

1. Open the **Settings** tab in the web dashboard.
2. Enter your **Artist / Sender Name** and **Gmail Address**.
3. Enter your 16-letter **Google App Password** ([Generate one in Google Account Security](https://myaccount.google.com/apppasswords)).
4. Click **"Verify SMTP (Send Test Email)"** — check your inbox for the immediate green diagnostic email.
5. (Optional) Toggle **Notion CRM** if syncing with a cloud workspace.
6. Set your song release details (Track Name, Spotify Link, EPK Link).
7. Click **"Save All Changes"**. You're ready to pitch!

---

## 📁 Repository Structure

```
pr-outreach-automator/
├── api/                           # FastAPI REST API & Vercel Tracking Pixel
│   ├── index.py                   # Endpoints (/api/leads, /api/config, /api/templates, /t/{id}.png)
│   └── requirements.txt           # Vercel serverless dependencies
├── config/
│   ├── settings.py                # Core configuration & defaults
│   └── templates/                 # Pitch templates with spintax & variable slots
│       ├── blog_pitch.txt         # For music journalists & bloggers
│       ├── playlist_pitch.txt     # For Spotify / Apple Music curators
│       └── follow_up.txt          # In-thread follow-up template
├── web/
│   └── index.html                 # Cupertino single-page web app
├── src/
│   ├── config_store.py            # In-app settings manager (data/app_config.json)
│   ├── orchestrator.py            # Outreach coordinator & batch scheduler
│   ├── crm/                       # Dual-mode CRM (Notion API & Local JSON storage)
│   ├── engine/                    # Spintax, rate limiter, personalizer, dispatcher
│   ├── inbox/                     # IMAP reply scanner & thread matcher
│   └── tracker/                   # 1x1 open tracking pixel generator
├── data/
│   ├── app_config.example.json    # Sanitized configuration template
│   ├── local_leads.json           # Offline CRM lead database
│   └── imports/                   # Sample Apollo / spreadsheet CSV exports
├── tests/                         # Full automated test suite (19 unit tests)
├── Dockerfile                     # Multi-stage production container
├── docker-compose.yml             # Single-command container orchestration
├── vercel.json                    # 1-command deployment configuration for tracking pixel
├── Launch-PR-Bot.bat              # 1-click Windows desktop launcher
├── requirements.txt               # Main Python dependencies
└── main.py                        # Studio CLI & GUI entry point
```

---

## 💻 CLI Commands Reference

Prefer working in the terminal? Every GUI feature is accessible via CLI:

| Command | Description |
|---|---|
| `python main.py gui` | Launch Web Studio and open in browser |
| `python main.py status` | Display pipeline status and quota analytics |
| `python main.py send --dry-run` | Preview generated pitches in terminal |
| `python main.py send --limit 5` | Dispatch next 5 pitches with 3–7 min human jitter |
| `python main.py follow-ups` | Send due in-thread follow-up emails |
| `python main.py check-replies` | Scan Gmail inbox via IMAP for replies & opt-outs |
| `python main.py add-lead` | Add a single curator interactively |
| `python main.py import-csv <file>` | Import contacts from a CSV file |
| `python main.py test-send --to email` | Send a diagnostic test email to device |

---

## 🧪 Automated Test Suite

Run the test suite anytime:
```bash
python -m unittest discover tests
```

```text
Ran 19 tests in 3.471s - OK
```
*Tests cover: Spintax parsing & permutations, variable interpolation, MIME email dispatching, 1x1 pixel tracking, weekend detection, rate limits, CSV multi-delimiter ingestion, and REST API routes.*

---

## 🔒 Security & Privacy

- **No Remote Credential Storage**: All Google App Passwords and API tokens are stored locally on your machine in `data/app_config.json`.
- **Git-Ignored Secrets**: `data/app_config.json` is strictly git-ignored to prevent accidental commits to public repositories.
- **Restricted CORS**: API endpoints are locked to localhost origins to defend against cross-origin browser attacks.
- **HTML Sanitization**: All user-rendered strings in the CRM and console are sanitized to prevent XSS.

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

Developed with ❤️ for independent musicians and indie record labels.
