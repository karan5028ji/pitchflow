# Changelog

All notable changes to the **Kxrn PR Outreach Studio** will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---

## [1.0.0] - 2026-09-17

### Added
- **Interactive Pitch Composer**:
  - Live dual-mode segmented control: *Live Preview* (Apple/Gmail preview with 1x1 tracking pixel indicator) vs. *Edit Pitch & Template*.
  - Subject line input field with live dynamic preview.
  - Quick-insert token chips: `{{First_Name}}`, `{{Track_Name}}`, `{{Stream_Link}}`, `{{Artist_Bio_Link}}`, `{{Publication}}`, `{{Recent_Article}}`, and `{Spintax}`.
  - Template persistence via `POST /api/templates/{type}` and reset to default stock.
- **Universal Clipboard & Multi-Delimiter CSV Import**:
  - Auto-delimiter detection supporting Excel/Google Sheets copy-paste (`\t`), commas, semicolons, and pipes.
  - Case-insensitive, fuzzy header matching (`name`, `email`, `publication`, `persona`, `recent_work`).
  - Graceful fallback extracting email addresses from headerless tabular rows.
  - Automatic lead enrichment: existing leads update their publication/article details instead of failing or silently skipping.
- **Instant SMTP Verification & Sender Synchronization**:
  - `POST /api/test-credentials` now auto-persists credentials entered in the Settings form and immediately dispatches a diagnostic verification email to the user's sender address.
- **Docker & Production Packaging**:
  - Added multi-stage `Dockerfile` and `docker-compose.yml` for 1-command deployment.
  - Comprehensive launch documentation, `.env.example`, and sanitized configuration templates.

### Changed
- Complete visual overhaul of the UI following Apple Human Interface Guidelines (HIG):
  - Frosted glassmorphism (`backdrop-filter: blur(28px) saturate(190%)`).
  - Native Apple typographic hierarchy with calibrated letter tracking.
  - Obsidian palette (`#060609`) with layered natural shadows and micro-interactions.
  - Slide-in navigation drawer for mobile and tablet devices.
- Refactored DOM rendering to eliminate DOM rebuild storms using atomic column updates.

---

## [0.8.0] - 2026-09-16

### Added
- **The Weekend Blocker**:
  - Automated detection of Saturdays and Sundays to halt cold outreach campaigns.
  - Prevents pitches from accumulating over weekends and getting discarded on Monday mornings.
  - One-click manual override toggle for urgent releases.
- **Test Mode (Send to Self)**:
  - Dedicated preview modal allowing artists to send rendered pitches with tracking pixels to secondary devices (Yahoo, Outlook, personal Gmail) before starting campaign batches.
- **Opt-Out & Auto-Blacklisting Engine**:
  - Automated IMAP scan parsing replies for negative intent keywords (`"unsubscribe"`, `"remove me"`, `"stop emailing"`, `"pass"`).
  - Instantly marks leads as `Blacklisted` to permanently safeguard Gmail domain reputation.
- **Anti-Spam Deliverability Guidelines**:
  - In-app alerts warning against direct MP3 or heavy photo attachments, guiding users to cloud press kits and private streaming links.

---

## [0.5.0] - 2026-09-15

### Added
- **Dual-Mode CRM**:
  - Notion API client for real-time cloud workspace synchronization.
  - Local JSON database fallback (`data/local_leads.json`) for 100% offline functionality.
  - Interactive Kanban board and high-density Table view with real-time status filtering.
- **Invisible Open-Tracking Pixel**:
  - Lightweight 1x1 transparent GIF/PNG pixel serverless handler (`/t/{id}.png`).
  - Real-time notification webhooks on first open.
- **In-Thread Follow-up Engine**:
  - Thread ID matching to deliver gentle follow-up reminders inside original email threads after 4 days of inactivity.

---

## [0.1.0] - 2026-09-14

### Added
- Initial release of the core PR outreach engine.
- Spintax generator for high-variance email body synthesis.
- Variable slot interpolation (`{{First_Name}}`, `{{Publication}}`, etc.).
- Human-jitter rate limiter enforcing 3–7 minute delays and 30 email daily caps.
- CLI interface (`python main.py {gui|status|send|follow-ups|check-replies}`).
