# Phase 3: Inbound Automations

## Objective
Automate the detection of candidate replies across all channels and sync status changes to ClickUp. Automate resume attachment from email.

## Automations

### 3.1 Instantly Reply → ClickUp
**Trigger:** Candidate replies to an Instantly email campaign
**Action:**
1. Instantly auto-stops the sequence (already configured)
2. Webhook or Zapier/Make detects the reply event
3. Find matching task in ClickUp by email address
4. Update task status to "Replied"
5. Set "Date Replied" field to today
6. Add reply snippet as a task comment

**Tool options:** Instantly webhook → Zapier → ClickUp API, or Instantly → Make → ClickUp

### 3.2 Heyreach Reply → ClickUp
**Trigger:** Candidate replies to a Heyreach LinkedIn message
**Action:**
1. Heyreach API detects reply
2. Find matching task in ClickUp by LinkedIn URL
3. Update task status to "Replied"
4. Set "Date Replied" field
5. Add reply context as task comment

**Tool options:** Heyreach webhook/API → Zapier/Make → ClickUp API

### 3.3 LinkedIn Recruiter Reply → ClickUp (via Gmail)
**Trigger:** LinkedIn sends InMail reply notification to RecruitCloud Gmail
**Action:**
1. Gmail scan detects LinkedIn notification email with "replied to your InMail" pattern
2. Extract candidate name from notification
3. Find matching task in ClickUp by name + channel "LI Recruiter"
4. Update task status to "Replied"
5. Set "Date Replied" field

**Tool options:** Gmail API / Zapier Gmail trigger → parse notification → ClickUp API
**Note:** This is the workaround for LinkedIn Recruiter having no API

### 3.4 Resume Attachment from Email
**Trigger:** Email arrives with PDF/DOC attachment (resume)
**Action:**
1. Scan incoming email for resume-like attachments
2. Match sender email to existing ClickUp task
3. Attach resume file to the matching task
4. If no matching task exists, create a new "Inbound" task

**Tool options:** Zapier/Make email trigger → attachment extraction → ClickUp file attachment API

## Open Questions
- Which automation platform? Zapier vs Make vs n8n vs custom
- Gmail API access for RecruitCloud inbox — does Isaac have this?
- Instantly webhook setup — is this on a paid plan?
- Heyreach API access — what tier?

## Dependencies
- Phase 1 complete (ClickUp structure)
- Phase 2 complete (Claude interface working for manual fallback)
- API access to Instantly, Heyreach, Gmail

## Success Criteria
- Instantly reply automatically updates ClickUp within 5 minutes
- Heyreach reply automatically updates ClickUp within 5 minutes
- LinkedIn Recruiter reply (via Gmail) updates ClickUp within 15 minutes
- Resume attachments auto-attach to correct candidate task
