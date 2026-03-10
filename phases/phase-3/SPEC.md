# Phase 3: Inbound Automations

**Status: 🟡 PARTIALLY COMPLETE**
**What's Done:** Manual sync scripts exist for Instantly and Heyreach → ClickUp
**What's Left:** Automated/scheduled sync, Gmail integration, resume attachments

## Objective
Automate the detection of candidate replies across all channels and sync status changes to ClickUp. Automate resume attachment from email.

## Current State

### What Already Works (manual scripts)
- **Instantly → ClickUp sync** (`scripts/sync/sync_to_clickup.py`): Pulls leads from Instantly campaigns and creates/updates ClickUp tasks with all fields
- **Instantly messages sync** (`scripts/sync/sync_messages.py`): Pulls email threads from Instantly, extracts last sent + replies, updates ClickUp Notes field and Date Replied
- **Heyreach → ClickUp sync** (`scripts/sync/sync_heyreach_v2.py`): Fetches LinkedIn conversations from Heyreach, updates existing tasks or creates new ones for Heyreach-only leads
- **Deduplication** (`scripts/sync/dedup_clickup.py`): Finds and removes duplicate tasks by email

These scripts run on-demand. They need to be scheduled for automated sync.

## Remaining Work

### 3.1 Scheduled Auto-Sync
Set up cron jobs or a scheduled task runner to execute sync scripts at regular intervals:
- Instantly lead sync: every 30 minutes
- Instantly message sync: every 15 minutes
- Heyreach conversation sync: every 15 minutes
- Dedup check: daily

### 3.2 Reply Detection & Status Updates
Currently, the message sync script populates Notes and Date Replied, but does NOT auto-update task status to "replied." This needs to be added:
- If a reply is detected and task is still in "outreach sent" → move to "replied"
- Post the reply snippet as a ClickUp task comment (not just in the Notes field)

### 3.3 LinkedIn Recruiter Reply → ClickUp (via Gmail)
**Trigger:** LinkedIn sends InMail reply notification to RecruitCloud Gmail
**Action:**
1. Gmail API scan detects LinkedIn notification email with "replied to your InMail" pattern
2. Extract candidate name from notification
3. Find matching task in ClickUp by name + channel "LinkedIn Recruiter"
4. Update task status to "replied"
5. Set "Date Replied" field

**Status:** Not started. Requires Gmail API access.

### 3.4 Resume Attachment from Email
**Trigger:** Email arrives with PDF/DOC attachment (resume)
**Action:**
1. Scan incoming email for resume-like attachments
2. Match sender email to existing ClickUp task
3. Attach resume file to the matching task
4. If no matching task exists, create a new "Inbound" task

**Status:** Not started. Requires Gmail API or Zapier/Make integration.

## API Access Confirmed
- **Instantly API:** ✅ Working (v2, base64 auth)
- **Heyreach API:** ✅ Working (X-API-KEY header)
- **ClickUp API:** ✅ Working (API token auth, 100 req/min)
- **Gmail API:** ❌ Not yet configured

## Instantly Campaign → ClickUp Mapping
| Instantly Campaign ID | Campaign Name | ClickUp Folder |
|----------------------|---------------|----------------|
| ff1fb3e5-4af1-433d-8a7f-d396eba5f0dd | Senior HTML | Lead HTML/Markup Developer |
| f241305e-57d5-4812-a278-2fcf68b65f9e | Mid HTML | Lead HTML/Markup Developer |
| d0da5edd-293e-4b21-8e35-ce504377362a | Senior Front End | Sr Front End Developer |
| b6a30d37-091e-4ab3-ae7b-6e0674c7d764 | Manual QA Postman | Senior Manual QA Engineer |
| 8b6cb40c-0cb1-41d1-97d1-286b04a01391 | Senior Flutter | Senior Flutter Developer |
| 6284a72c-7927-41fe-b7ec-2e1df22e1903 | Middle Flutter Developer | Mid-Level Flutter Developer |
| 3cc1f7ae-c1df-4f29-afb1-ff5ff1143780 | Product Owner | Senior Product Manager |
| 0ccefc2b-fa4d-4615-b180-4d17cf27960f | Senior Back End | Senior Backend Developer |
| 05f6e117-9187-421f-ad45-951300d2822f | Affiliate Manager | Affiliate Manager |

## Heyreach Campaign → ClickUp Mapping
| Heyreach Campaign ID | Campaign Name | ClickUp Folder |
|---------------------|---------------|----------------|
| 354909 | Product Manager | Senior Product Manager |
| 349645 | Mid Flutter | Mid-Level Flutter Developer |
| 357063 | Senior Flutter Developer | Senior Flutter Developer |
| 357067 | Lead HTML Markup Developer | Lead HTML/Markup Developer |
| 357072 | Sr Front End Developer | Sr Front End Developer |
| 357074 | Senior Backend Developer | Senior Backend Developer |
| 357075 | Senior Manual QA Engineer | Senior Manual QA Engineer |
| 357076 | Affiliate Manager | Affiliate Manager |

## Dependencies
- Phase 1 complete (✅)
- Phase 2 complete (for manual fallback) — not started
- Gmail API access — needed for 3.3 and 3.4

## Success Criteria
- Sync scripts run automatically on a schedule
- Instantly/Heyreach replies auto-update ClickUp status to "replied" within 15 minutes
- LinkedIn Recruiter reply (via Gmail) updates ClickUp within 15 minutes
- Resume attachments auto-attach to correct candidate task
