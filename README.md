# SmartState Recruitment Pipeline

Multi-channel recruitment automation system built on ClickUp for RecruitCloud.

## Client
**SmartState** — managed by RecruitCloud (isaac@recruitcloud.io)

## Overview
A centralized ClickUp-based pipeline that tracks candidates across four outreach channels (Instantly, Heyreach, LinkedIn Recruiter, Inbound) with built-in deduplication, sync scripts, and real-time Slack notifications.

## Architecture
```
Instantly (Email)  ──┐
                     ├──→ ClickUp (Source of Truth)
Heyreach (LinkedIn) ─┤
                     └──→ Slack #smartstate-responses (inbound replies only)
LinkedIn Recruiter ──→ ClickUp (manual)
Inbound ─────────────→ ClickUp (Phase 3)

Notifications System (scripts/notifications/)
├── instantly_notifier.py  ──→ Email replies → Slack
├── heyreach_notifier.py   ──→ LinkedIn replies → Slack (inbound only)
├── health_monitor.py      ──→ Sending account health → Slack
└── run_all.py             ──→ Orchestrator (runs all on schedule)
```

## Build Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | ClickUp Foundation (Space, Folders, Fields, Statuses) | ✅ COMPLETE |
| 1a | Instantly Lead Sync (491 leads across 9 campaigns) | ✅ COMPLETE |
| 1b | LinkedIn Profile Population (155 Product Owner leads) | ✅ COMPLETE |
| 1c | Instantly Email Sync (291 tasks updated with messages) | ✅ COMPLETE |
| 1d | Heyreach Conversation Sync (31 updated + 19 new tasks) | ✅ COMPLETE |
| 1e | Heyreach Campaign Creation (8 campaigns) | ✅ COMPLETE |
| 2 | Slack Notifications (inbound reply alerts, health monitor) | ✅ COMPLETE |
| 3 | Performance Reporting (reply rates, inbox health by channel) | 🔄 In Progress |
| 4 | Inbound Automations (resume scanning, email inbox monitoring) | Pending |
| 5 | Dedup Checker (block re-messaging existing candidates) | Pending |
| 6 | SLAs, Alerts, Reporting Dashboard | Pending |

## Phase 2 — Slack Notifications (COMPLETE)

### What was built
Real-time Slack notifications to `#smartstate-responses` (Recruitcloud workspace):

| Notifier | Trigger | Channel |
|---|---|---|
| `instantly_notifier.py` | Candidate replies to email campaign | `#smartstate-responses` |
| `heyreach_notifier.py` | Candidate replies to LinkedIn message (inbound only) | `#smartstate-responses` |
| `health_monitor.py` | Instantly sending account warmup/deliverability scores | `#smartstate-responses` |

### Running the notifier
```bash
# Run once
cd scripts/notifications
python3 run_all.py

# Run on continuous loop (every 15 min)
python3 run_all.py --loop

# Force health report now
python3 run_all.py --health
```

### Setup
1. Copy `scripts/notifications/config.py` → `scripts/notifications/config_local.py`
2. Fill in: `SLACK_WEBHOOK_URL`, `INSTANTLY_API_KEY`, `HEYREACH_API_KEY`, `CLICKUP_API_TOKEN`
3. All ClickUp list IDs, custom field IDs, and campaign mappings are pre-filled

### Cron setup (every 15 minutes)
```bash
*/15 * * * * python3 /path/to/scripts/notifications/run_all.py >> /tmp/smartstate_notifier.log 2>&1
0 */6 * * * python3 /path/to/scripts/notifications/run_all.py --health >> /tmp/smartstate_health.log 2>&1
```

## Current State (as of 2026-03-18)

### ClickUp Structure
- **Space:** SmartState
- **8 Folders** (one per job role), each with a Candidates list
- **11 Custom Fields:** Email, Phone, LinkedIn, Channel, Campaign/Sequence, Date Contacted, Date Replied, Interview Date, Candidate Rating, Salary Range, Notes
- **8 Pipeline Statuses:** Outreach Sent → Replied → Screening → Interviewed → Submitted to Client → Client Review → Hired → Complete

### Task Counts
| List | Tasks | Source |
|------|-------|--------|
| Senior Product Manager | 251 | Instantly + Heyreach |
| Mid-Level Flutter Developer | 113 | Instantly + Heyreach |
| Senior Flutter Developer | 127 | Instantly |
| Lead HTML/Markup Developer | 0 | Awaiting leads |
| Sr Front End Developer | 0 | Awaiting leads |
| Senior Backend Developer | 0 | Awaiting leads |
| Senior Manual QA Engineer | 0 | Awaiting leads |
| Affiliate Manager | 0 | Awaiting leads |

### Heyreach Campaigns (SmartState only)
| Campaign | Status | ID |
|---|---|---|
| Product Manager | IN_PROGRESS | 354909 |
| Mid Flutter | IN_PROGRESS | 349645 |
| Senior Flutter Developer | DRAFT | 357063 |
| Frontend Lead Leader V2 | FINISHED | 357067 |
| Frontend Mid-Level V2 | FINISHED | 357072 |
| Senior Backend Developer | DRAFT | 357074 |
| Senior Manual QA Engineer | DRAFT | 357075 |
| Affiliate Manager | DRAFT | 357076 |

### Instantly Campaigns (SmartState only)
| Campaign | Status | ID |
|---|---|---|
| Product Owner | Active | 3cc1f7ae-... |
| Senior Flutter | Completed | 8b6cb40c-... |
| Middle Flutter Developer | Completed | 6284a72c-... |
| Senior HTML | Completed | ff1fb3e5-... |
| Mid HTML | Completed | f241305e-... |
| Senior Front End | Completed | d0da5edd-... |
| Senior Back End | Completed | 0ccefc2b-... |
| Affiliate Manager | Completed | 05f6e117-... |
| Manual QA Postman | Error | b6a30d37-... |
| Frontend Lead Leader V2 | Draft | 2584f7fc-... |
| Frontend Mid-Level V2 | Draft | 33b44493-... |

## Scripts

### Notifications (`scripts/notifications/`)
- **`run_all.py`** — Orchestrator. Runs all notifiers. Supports `--loop` and `--health` flags.
- **`instantly_notifier.py`** — Polls Instantly v2 API for new email replies, posts to Slack.
- **`heyreach_notifier.py`** — Polls Heyreach for new inbound LinkedIn messages, posts to Slack.
- **`health_monitor.py`** — Checks Instantly warmup health per sending account, posts report to Slack. Fires urgent alert for Critical accounts.
- **`slack_client.py`** — Slack message formatting and posting utilities.
- **`state_manager.py`** — Persistent state (state.json) to prevent duplicate notifications.
- **`config.py`** — Config template. Copy to `config_local.py` and fill in secrets.

### Sync Scripts (`scripts/sync/`)
- **`sync_to_clickup.py`** — Fetches leads from Instantly API, creates ClickUp tasks.
- **`sync_messages.py`** — Pulls emails from Instantly, updates ClickUp Notes + Date Replied.
- **`sync_heyreach_v2.py`** — Fetches Heyreach conversations, updates ClickUp tasks.
- **`dedup_clickup.py`** — Finds and removes duplicate tasks within each ClickUp list.
- **`bulk_sync_remaining.py`** — Syncs remaining Instantly campaigns to ClickUp.

### Utility Scripts (`scripts/utils/`)
- **`update_all_linkedin.py`** — Bulk updates LinkedIn URLs across ClickUp tasks.
- **`extract_linkedin_all.py`** — Extracts LinkedIn URLs from Instantly leads.
- **`check_remaining.py`** — Checks remaining campaign lead counts in Instantly.

### Configuration
- Copy `scripts/notifications/config.py` → `scripts/notifications/config_local.py` and fill in API keys.
- Copy `scripts/config_template.py` → `scripts/config.py` for sync scripts.
- **Never commit `config_local.py` or `config.py`** — gitignored.

## API Keys Required
| Service | Used For |
|---|---|
| Instantly v2 API | Email reply polling, account health |
| Heyreach API | LinkedIn conversation polling |
| ClickUp API v2 | Task lookup for reply notifications |
| Slack Incoming Webhook | Posting to #smartstate-responses |

## API Notes
- **Instantly API v2:** Auth via `Authorization: Bearer <key>`. Base URL `https://api.instantly.ai/api/v2`.
- **Heyreach API:** Auth via `X-API-KEY` header. Base URL `https://api.heyreach.io/api/public`.
- **ClickUp API v2:** 100 req/min. Scripts use 0.65s delay + 62s pause every 95 requests.
- **Rate limiting:** All scripts use 0.65s delay between API calls to stay within limits.
