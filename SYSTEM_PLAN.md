# SmartState Recruitment Automation System — Master Plan

## Purpose
A fully automated recruiter efficiency system that captures all outreach activity,
notifies in real-time when candidates respond, follows up with non-responders
across multiple channels, manages the ClickUp pipeline automatically, and alerts
when anything breaks.

---

## Architecture Overview

```
Outreach Channels          Notification Layer         Follow-Up Layer
─────────────────          ──────────────────         ───────────────
Heyreach (LinkedIn)   →    Slack #smartstate-         Non-responder
Instantly (Email)     →    responses                  detection →
LinkedIn Recruiter    →    (real-time, full msg)       Clay → SMS / Email
```

---

## Layer 1 — Outreach Activity Capture

| Channel | Method | Status |
|---|---|---|
| Heyreach (LinkedIn campaigns) | Heyreach API | ✅ DONE |
| Instantly (email campaigns) | Instantly v2 API | ✅ DONE |
| LinkedIn Recruiter InMail | Gmail API (hit-reply@linkedin.com) | ✅ DONE |

---

## Layer 2 — Real-Time Reply Notifications

All inbound candidate replies post to Slack `#smartstate-responses` with:
- Candidate name
- Source channel (Heyreach / Instantly / LinkedIn Recruiter)
- Job role / campaign
- Full message body (not a snippet)
- Timestamp

**Scheduler:** macOS launchd, runs every 15 minutes
**Script:** `scripts/notifications/run_all.py`
**Status:** ✅ DONE

---

## Layer 3 — Account Health Monitoring

Checks all Instantly sending accounts for warmup score, deliverability status.
Posts consolidated report to Slack `#smartstate-performance` on Mon/Wed/Fri at 8am.
Sends urgent alert immediately for any Critical account.

**Status:** ✅ DONE

---

## Layer 4 — Non-Responder Follow-Up Pipeline

**Trigger:** Anyone with no reply after 2 days across any channel.

**Daily workflow:**
1. Scrape LinkedIn Recruiter "Awaiting Reply" inbox (Chrome CDP)
2. Check Heyreach conversations for outbound messages with no inbound reply
3. Check Instantly campaigns for leads with no reply
4. Enrich each non-responder via LeadMagic (email + phone by LinkedIn URL)
5. Push to Clay webhook → routed to SMS or email follow-up
6. Track in state.json so no one gets contacted twice

**Routing:**

| Source | No reply after 2 days | Action |
|---|---|---|
| LinkedIn Recruiter | → | Clay SMS table → Twilio SMS |
| Heyreach (LinkedIn) | → | Clay SMS table → Twilio SMS |
| Instantly (email) | → | Clay LinkedIn table → manual InMail queue |

**Clay webhooks:**
- SMS: `pull-in-data-from-a-webhook-3f924fa2-4e23-44ff-89ac-81aafcc84e10`
- LinkedIn InMail: `pull-in-data-from-a-webhook-7b4f2b4f-0f90-49de-a964-cb7095581875`

**Twilio from:** +1 (510) 871-8295
**Enrichment:** LeadMagic — phone by LinkedIn URL (SMS leads), LinkedIn URL by email (InMail leads)

**Still needed:** SMS copy text (use [name] as first name placeholder)

**Status:** ✅ BUILT — awaiting SMS copy to activate Twilio sending

---

## Layer 5 — ClickUp Pipeline Automation

When a candidate replies → automatically move their ClickUp task to the correct stage.

**Pipeline stages:**
Outreach Sent → Replied → Screening → Interviewed → Submitted → Client Review → Hired / Rejected / Not Interested

**Trigger:** Fires when Layers 2 notifiers detect an inbound reply
**Status:** 🔨 TO BUILD

---

## Layer 6 — SLA Alerts

Flag candidates stuck in a stage too long and alert in Slack.

**Example rules:**
- "Replied" for 48h with no action → alert recruiter
- "Screening" for 72h → alert recruiter
- Custom thresholds per stage

**Status:** 🔨 TO BUILD

---

## Layer 7 — Gemini Note Logging

Auto-summarize candidate messages and post as comments on the ClickUp task.
Keeps a full conversation log in ClickUp without manual data entry.

**Status:** 🔨 TO BUILD

---

## Layer 8 — System Health Monitoring

Ensure the entire system is running and alert if anything breaks.

**Monitoring targets:**
- launchd scheduler still running
- Gmail OAuth token valid (not expired)
- Heyreach API reachable
- Instantly API reachable
- Slack webhook responding
- ClickUp API reachable
- State file readable/writable

**Alert channel:** Slack `#smartstate-performance`
**Status:** 🔨 TO BUILD

---

## File Structure

```
scripts/notifications/
├── run_all.py                    # Main orchestrator (runs every 15 min)
├── instantly_notifier.py         # Instantly reply notifier
├── heyreach_notifier.py          # Heyreach reply notifier
├── linkedin_recruiter_notifier.py # LinkedIn InMail notifier (via Gmail)
├── health_monitor.py             # Instantly account health checker
├── performance_report.py         # Mon/Wed/Fri performance report
├── slack_client.py               # Slack formatting + posting
├── state_manager.py              # Dedup + last-checked state
├── config.py                     # API keys + campaign mappings
└── state.json                    # Runtime state (gitignored)

Schedulers (~/Library/LaunchAgents/):
├── com.smartstate.replies.plist       # Every 15 min → run_all.py
└── com.smartstate.performance.plist  # Mon/Wed/Fri 8am → performance_report.py
```

---

## Build Order

| Priority | Layer | Status |
|---|---|---|
| 1 | Non-responder follow-up pipeline (Layer 4) | 🔨 Next |
| 2 | ClickUp pipeline automation (Layer 5) | 🔨 Queued |
| 3 | SLA alerts (Layer 6) | 🔨 Queued |
| 4 | Gemini note logging (Layer 7) | 🔨 Queued |
| 5 | System health monitoring (Layer 8) | 🔨 Queued |

---

## Key Decisions & Constraints

- **No automated LinkedIn Recruiter sending** — LinkedIn has no API and automation risks account flagging
- **Heyreach campaignId filter is broken** — API ignores it, returns all conversations globally; fetch once only
- **Instantly uses v2 API** — Bearer token auth, `/emails` endpoint with `ue_type` 2/3 for inbound replies
- **Gmail OAuth tokens** stored in `~/.gmail-mcp/credentials.json` — auto-refreshed by notifier
- **State dedup** via `state.json` — prevents duplicate Slack messages across restarts
- **Slack block limit** — section blocks max 3000 chars; health report chunks accounts across multiple blocks
