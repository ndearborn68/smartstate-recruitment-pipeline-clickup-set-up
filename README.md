# SmartState Recruitment Pipeline

Multi-channel recruitment automation system built on ClickUp for RecruitCloud.

## Client
**SmartState** — managed by RecruitCloud (isaac@recruitcloud.io)

## Overview
A centralized ClickUp-based pipeline that tracks candidates across four outreach channels (Instantly, Heyreach, LinkedIn Recruiter, Inbound) with built-in deduplication and sync scripts.

## Architecture
```
ClickUp (Source of Truth)
├── Instantly (Email Campaigns) ──→ ClickUp via sync_to_clickup.py
├── Heyreach (LinkedIn Outreach) ──→ ClickUp via sync_heyreach_v2.py
├── LinkedIn Recruiter (Manual) ──→ ClickUp via Claude OCR (Phase 2)
├── Inbound (Email Resume Scan) ──→ ClickUp via automation (Phase 3)
│
├── sync_messages.py ──→ Emails/messages → ClickUp Notes field
├── update_all_linkedin.py ──→ LinkedIn URLs → ClickUp tasks
└── dedup_clickup.py ──→ Duplicate cleanup
```

## Build Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | ClickUp Foundation (Space, Folders, Fields, Statuses) | COMPLETE |
| 1a | Instantly Lead Sync (444 leads across 3 campaigns) | COMPLETE |
| 1b | LinkedIn Profile Population (155 Product Owner leads) | COMPLETE |
| 1c | Instantly Email Sync (291 tasks updated with messages) | COMPLETE |
| 1d | Heyreach Conversation Sync (31 updated + 19 new tasks) | COMPLETE |
| 1e | Heyreach Campaign Creation (6 new draft campaigns) | COMPLETE |
| 2 | Claude as Interface (MCP task management, OCR, dedup) | Pending |
| 3 | Inbound Automations (reply detection, resume scanning) | Pending |
| 4 | Slack Notifications (reply alerts to recruiter channel) | Pending |
| 5 | SLAs, Alerts, Reporting Dashboard | Pending |
| 6 | Gemini Notes Integration (interview notes as comments) | Pending |

## Current State (as of 2026-03-09)

### ClickUp Structure
- **Space:** SmartState
- **8 Folders** (one per job role), each with a Candidates list
- **11 Custom Fields** per list: Email, Phone, LinkedIn, Channel, Campaign/Sequence, Date Contacted, Date Replied, Interview Date, Candidate Rating, Salary Range, Notes
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

### Heyreach Campaigns
| Campaign | Status | Heyreach ID |
|----------|--------|-------------|
| Product Manager | Active | 354909 |
| Mid Flutter | Active | 349645 |
| Senior Flutter Developer | Draft | 357063 |
| Lead HTML Markup Developer | Draft | 357067 |
| Sr Front End Developer | Draft | 357072 |
| Senior Backend Developer | Draft | 357074 |
| Senior Manual QA Engineer | Draft | 357075 |
| Affiliate Manager | Draft | 357076 |

## Scripts

### Sync Scripts (`scripts/sync/`)
- **`sync_to_clickup.py`** — Fetches leads from Instantly API, creates ClickUp tasks with custom fields (Channel, Email, Campaign, Date Contacted, LinkedIn). Handles rate limiting (100 req/min).
- **`sync_messages.py`** — Pulls emails from Instantly API, extracts last sent + all replies per lead, updates ClickUp Notes field and Date Replied.
- **`sync_heyreach_v2.py`** — Fetches Heyreach LinkedIn conversations, updates existing ClickUp tasks with Heyreach notes, creates new tasks for Heyreach-only leads.
- **`dedup_clickup.py`** — Finds and removes duplicate tasks within each ClickUp list (matches by email).
- **`sync_heyreach_v1.py`** — (Deprecated) First attempt, timed out on shared lead lists.

### Utility Scripts (`scripts/utils/`)
- **`update_all_linkedin.py`** — Updates all ClickUp tasks across campaigns with LinkedIn URLs from Instantly data.
- **`extract_linkedin_all.py`** — Fetches individual Instantly leads to extract LinkedIn URLs (handles `LinkedIn_personURL` field).
- **`check_remaining.py`** — Checks remaining 6 Instantly campaigns for lead counts.
- Other helper scripts for LinkedIn extraction and lead re-fetching.

### Configuration
- Copy `scripts/config_template.py` → `scripts/config.py` and fill in API keys.
- **Never commit `config.py`** — it contains secrets.

## Key Files
- `docs/smartstate-build-plan.md` — Master build plan with all decisions
- `mockups/smartstate-clickup-mockup.html` — Interactive visual mockup
- `phases/` — Detailed specs per phase
- `scripts/` — All sync and utility scripts
- `data/` — LinkedIn mappings and reference data

## Known Issues / Open Items
1. **REJECTED status missing** — Lists have "complete" but no separate REJECTED status
2. **Channel field is single-select** — Dual-channel leads (Instantly + Heyreach) only show one channel
3. **No auto-sync** — Scripts must be run manually; scheduled sync not yet configured
4. **5 empty lists** — Awaiting leads from Instantly/Heyreach for HTML, Front End, Backend, QA, Affiliate roles
5. **No exclusion lists** — Draft Heyreach campaigns lack dedup rules

## API Notes
- **ClickUp API v2:** 100 requests/min (Business plan). Scripts use 0.65s delay + 62s pause every 95 requests.
- **Instantly API v2:** SmartState leads use `LinkedIn_personURL` field (not `person_linkedIn`).
- **Heyreach API:** Base URL `https://api.heyreach.io/api/public`. Auth via `X-API-KEY` header. Campaign creation only via browser UI (no API endpoint).
