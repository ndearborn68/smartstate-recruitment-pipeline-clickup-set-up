# SmartState Recruitment Pipeline

Multi-channel recruitment automation system built on ClickUp for RecruitCloud.

## Client
**SmartState** — managed by RecruitCloud (isaac@recruitcloud.io)

## Overview
A centralized ClickUp-based pipeline that tracks candidates across four outreach channels (Instantly, Heyreach, LinkedIn Recruiter, Inbound) with built-in deduplication, Slack notifications, and reporting.

## Architecture
```
ClickUp (Source of Truth)
├── Instantly (Email Campaigns) ──→ ClickUp via MCP
├── Heyreach (LinkedIn Outreach) ──→ ClickUp via API
├── LinkedIn Recruiter (Manual) ──→ ClickUp via Claude OCR
├── Inbound (Email Resume Scan) ──→ ClickUp via automation
│
├── Claude (MCP Interface) ──→ Create/update tasks, dedup checks
├── Slack (Notifications) ──→ Candidate reply alerts
└── Dashboard (Reporting) ──→ Client-facing metrics
```

## Build Phases

| Phase | Description | Status |
|-------|-------------|--------|
| 1 | ClickUp Foundation (Space, Folders, Fields, Statuses) | Ready to build |
| 2 | Claude as Interface (MCP task management, OCR, dedup) | Pending |
| 3 | Inbound Automations (reply detection, resume scanning) | Pending |
| 4 | Slack Notifications (reply alerts to recruiter channel) | Pending |
| 5 | SLAs, Alerts, Reporting Dashboard | Pending |
| 6 | Gemini Notes Integration (interview notes as comments) | Pending |

## Key Files
- `docs/smartstate-build-plan.md` — Master build plan with all decisions
- `mockups/smartstate-clickup-mockup.html` — Interactive visual mockup
- `phases/` — Detailed specs per phase

## Outreach Channels
1. **Instantly** — Email campaigns with API
2. **Heyreach** — LinkedIn outreach with API
3. **LinkedIn Recruiter** — Manual InMails, no API (solved via Claude screenshot OCR)
4. **Inbound** — Email resume scanning

## Dedup Strategy
- Primary key: LinkedIn Profile URL
- Secondary key: Email address
- ClickUp is the single source of truth
- Pre-campaign dedup checks via Claude before any outreach
