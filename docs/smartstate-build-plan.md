# SmartState ClickUp Build Plan — Phase 1

## Context
Isaac (isaac@recruitcloud.io) is building a multi-channel recruitment pipeline in ClickUp for his client SmartState. ClickUp is the single source of truth and dedup hub for all outreach and candidate management.

---

## PHASE 1: Foundation (Build Now)

### Step 1: Create Space
- **Space Name:** SmartState
- This is the client-level container

### Step 2: Create Job Folders
Create one Folder per open role inside the SmartState Space:
- Sr. Software Engineer
- Marketing Manager
- Data Analyst
- (More will be added as jobs come in)

### Step 3: Create Candidates List
Inside each Job Folder, create one List called **"Candidates"**
- Each candidate is a Task inside this List
- One candidate = one task = one job (no multi-job tagging)
- Isaac specifies which job a candidate belongs to at input time

### Step 4: Configure Statuses (on each Candidates list)
Pipeline has two phases — Outreach then Recruitment:

**Outreach Phase:**
1. Outreach Sent (purple #8b5cf6)
2. Replied (violet #a855f7)

**Recruitment Phase:**
3. Screening (blue #3b82f6)
4. Interviewed (amber #f59e0b)
5. Submitted to Client (green #22c55e)
6. Client Review (cyan #06b6d4)

**Closed:**
7. Hired (emerald #10b981) — DONE status
8. Rejected (red #ef4444) — CLOSED status
9. Not Interested (gray #94a3b8) — CLOSED status (they replied but declined)

### Step 5: Create Custom Fields (at Space level so all jobs inherit)

| Field Name | Type | Notes |
|---|---|---|
| Outreach Channel | Dropdown: Instantly / Heyreach / LI Recruiter / Inbound | CRITICAL for dedup |
| Campaign / Sequence | Short Text | e.g., "SmartState-SWE-Q1" |
| Date Contacted | Date | When first outreach was sent |
| Date Replied | Date | When they responded |
| Email | Email | From lead data |
| Phone | Phone | Optional |
| LinkedIn Profile | URL | Primary dedup identifier |
| Resume | (use task attachments) | Auto-attached from email scan later |
| Interview Notes | Long Text | Gemini notes pushed via Claude |
| Rating | Rating (1-5) | Isaac's assessment |
| Interview Date | Date | Google Meet date |
| Salary Expectation | Currency | From interview |

### Step 6: Test with a Sample Candidate
Create one test candidate in Sr. Software Engineer to verify:
- All fields populate correctly
- Status changes work
- The board view looks right

---

## FUTURE PHASES (Don't Build Yet)

### Phase 2: Claude as Interface
- Isaac tells Claude candidate info → Claude creates/updates ClickUp tasks via MCP
- Screenshot OCR for LinkedIn Recruiter contacts
- Dedup checks before outreach (search by LinkedIn URL or email)

### Phase 3: Inbound Automations
- Instantly replies → ClickUp status update to "Replied"
- Heyreach replies → ClickUp status update to "Replied"
- RecruitCloud Gmail scan for LinkedIn Recruiter InMail reply notifications → ClickUp update
- Email resume attachment scanning → attach to matching task

### Phase 4: Slack Notifications
- New Slack channel for candidate replies
- When any task moves to "Replied" → post to Slack with candidate name, job, channel, link
- All RecruitCloud recruiters are channel members

### Phase 5: SLAs, Alerts, Reporting
- ClickUp automations: "Replied > 48 hours with no action" → notification
- Dashboard: response rate by channel, conversion by stage, time-to-fill
- Client-facing metrics view

### Phase 6: Gemini Notes Integration
- Every Google Meet interview note → timestamped comment on candidate task
- Full chronological activity log per candidate (not just a single notes field)

---

## KEY DESIGN DECISIONS (Already Made)
- One candidate = one task = one job (Isaac assigns job at input time)
- Dedup by LinkedIn URL (primary) or email (secondary)
- LinkedIn Recruiter has no API — Isaac screenshots InMail sent page, Claude OCRs and creates tasks
- LinkedIn Recruiter replies go to RecruitCloud Gmail — scannable for reply detection
- Instantly already auto-stops sequences on reply
- All communication history goes in task COMMENTS, not a single notes field
- DNC already accounted for
- Compliance/GDPR already accounted for
- Placement tracking/invoicing already accounted for
- Multi-client scaling not needed yet (SmartState only)

---

## OUTREACH CHANNELS
1. **Instantly** — Email campaigns. Has API. Leads pushed with name, email, LinkedIn, phone.
2. **Heyreach** — LinkedIn outreach. Has API. Sequences auto-created.
3. **LinkedIn Recruiter** — Manual InMails. NO API. Logged via Claude screenshot OCR or batch paste.
4. **Inbound** — Candidates email in with resume. Scanned from email.

---

## HOW ISAAC WILL USE CLAUDE (Phase 2+)
- "Add [Name] to [Job], contacted via [Channel], campaign [Name]"
- "Move [Name] to Replied / Screening / Interviewed / etc."
- "[paste Gemini notes] — add to [Name]'s task as a comment"
- "Check if [LinkedIn URL or email] is already in ClickUp"
- [drops screenshot] "Log these LinkedIn Recruiter InMails for [Job]"
- "Show me all candidates in Screening for Sr. Software Engineer"
