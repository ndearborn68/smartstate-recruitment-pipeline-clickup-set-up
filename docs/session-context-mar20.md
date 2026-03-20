---
name: smartstate-recruitment-pipeline
description: SmartState recruitment pipeline — Supabase cloud backend fully built, non-responder Clay routing in progress
type: project
---

SmartState is a recruitment pipeline tracking candidates across job roles in ClickUp, sourced from Instantly (email), Heyreach (LinkedIn), LinkedIn Recruiter, and inbound. The automation backend has been migrated from Claude Desktop to Supabase Edge Functions (always-on, no Mac needed).

**Why:** Client needs a centralized pipeline with dedup, sync automation, and eventually AI-assisted workflows.

**How to apply:** Always write new files locally AND commit+push to the GitHub repo. Local clone is at `~/Desktop/smartstate-recruitment-pipeline-clickup-set-up`.

## Key Info
- **Repo:** https://github.com/ndearborn68/smartstate-recruitment-pipeline-clickup-set-up
- **Local clone:** `/Users/isaacmarks/Desktop/smartstate-recruitment-pipeline-clickup-set-up/`
- **Supabase project ID:** `uckcplhvjtxnkyxhccxr`
- **ClickUp hierarchy:** Space → Job Folders → Candidate Lists
- **Pipeline stages:** Outreach Sent → Replied → Screening → Interviewed → Submitted to Client → Client Review → Hired/Rejected/Not Interested
- **Dedup:** LinkedIn URL + Outreach Channel dropdown
- **Config template:** `scripts/config_template.py` (all API keys/IDs)

## Supabase Edge Functions (LIVE)
| Function | What it does |
|---|---|
| sync-heyreach | Polls Heyreach every 15min → DB → Slack → ClickUp |
| sync-instantly | Same for Instantly email campaigns |
| slack-notify | Posts new inbound replies to #smartstate-responses |
| push-to-clickup | Pushes status changes + Date Replied + notes to ClickUp |
| nonresponder | Daily 9am — finds 2-day non-responders → POSTs to Clay |
| weekly-report | Monday 8am → pipeline report to #smartstate-performance |
| sms-reply-handler | Receives Twilio inbound SMS → posts reply to Slack |

## Twilio SMS
- Number: (510) 871-8295
- Inbound webhook set to: `https://uckcplhvjtxnkyxhccxr.supabase.co/functions/v1/sms-reply-handler`
- 10DLC Brand: RecruitCloud (registered)
- 10DLC Campaign: registered + number linked
- **Outbound SMS blocked until carrier approval (1-5 days from ~Mar 20 2026)**

## Non-Responder Pipeline (Clay)
- Clay table: "All Non-Responder"
- Webhook: `https://api.clay.com/v3/sources/webhook/pull-in-data-from-a-webhook-7b4f2b4f-0f90-49de-a964-cb7095581875`
- nonresponder Edge Function POSTs: name, first_name, email, linkedin_url, phone, job_role, original_channel, days_since_contact, has_phone, has_email, has_linkedin
- Clay enrichment: phone waterfall (LeadMagic → others) + personal email
- Routing logic (in Clay, partially built as of Mar 20 2026):
  - Phone found → Twilio SMS
  - No phone + email found → Instantly sequence
  - No phone + no email → Slack alert to #smartstate-responses for manual LinkedIn InMail
- **NEXT:** Finish Route formula column + Slack InMail Alert column in Clay, then run nonresponder on all ~511 real candidates

## LinkedIn Recruiter Sync Gap
- Candidates messaged via LinkedIn Recruiter (not Heyreach) are NOT in Supabase DB
- Scraper via Chrome CDP tested and works (tab: C70DE70A, projects: PM=1661933460, Flutter=1661750948, HTML CSS=1440335625)
- Decision: build local Python script (launchd daily 9am) to scrape "Awaiting Reply" per project → write to Supabase → nonresponder picks up
- **NOT YET BUILT**

## Gmail Candidate Sync
- Not yet built — needed for LinkedIn Recruiter InMail reply detection via Gmail notifications
- **NOT YET BUILT**

## Phase Status
- Phase 1: COMPLETE — 529 candidates, 17 campaigns, 8 jobs in DB
- Phase 2: Supabase cloud backend COMPLETE — Claude Desktop jobs deleted, launchd disabled
- Phase 3+: Gmail sync, LinkedIn Recruiter scraper, Gemini notes, SLA alerts — all pending

## Active Job Roles (ClickUp Lists)
- HTML/Markup Developer
- Mid-Level Flutter Developer
- Senior Flutter Developer
- Senior Product Manager
- (+ 4 others per config_template.py)

## Data Sources
- Instantly: 9 campaigns mapped to job roles
- Heyreach: 8 campaigns mapped to job roles
- LinkedIn Recruiter: manual import (Recruiter projects: PM, Flutter, HTML CSS Lead)
- Inbound: manual/webhook
