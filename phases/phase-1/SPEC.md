# Phase 1: ClickUp Foundation

## Objective
Build the complete ClickUp structure — Space, Folders, Lists, custom fields, and statuses — so Isaac can immediately start adding candidates via Claude MCP.

## Steps

### 1. Create Space: SmartState
- Top-level container for the client

### 2. Create Job Folders
Each open role is a Folder inside the SmartState Space:
- **Sr. Software Engineer**
- **Marketing Manager**
- **Data Analyst**
- Additional folders added as new jobs come in

### 3. Create Candidates List (per Folder)
Inside each Job Folder, one List called **"Candidates"**
- One task = one candidate = one job
- Isaac specifies which job at input time
- No multi-job tagging

### 4. Configure Statuses
Applied to each Candidates list. Two-phase pipeline:

**Outreach Phase:**
| Status | Color | Type |
|--------|-------|------|
| Outreach Sent | #8b5cf6 (purple) | Active |
| Replied | #a855f7 (violet) | Active |

**Recruitment Phase:**
| Status | Color | Type |
|--------|-------|------|
| Screening | #3b82f6 (blue) | Active |
| Interviewed | #f59e0b (amber) | Active |
| Submitted to Client | #22c55e (green) | Active |
| Client Review | #06b6d4 (cyan) | Active |

**Closed:**
| Status | Color | Type |
|--------|-------|------|
| Hired | #10b981 (emerald) | Done |
| Rejected | #ef4444 (red) | Closed |
| Not Interested | #94a3b8 (gray) | Closed |

### 5. Create Custom Fields (Space-level)
Set at Space level so all job folders inherit automatically.

| Field | ClickUp Type | Required? | Notes |
|-------|-------------|-----------|-------|
| Outreach Channel | Dropdown | Yes | Options: Instantly / Heyreach / LI Recruiter / Inbound |
| Campaign / Sequence | Short Text | No | e.g., "SmartState-SWE-Q1" |
| Date Contacted | Date | Yes | When first outreach was sent |
| Date Replied | Date | No | When they responded |
| Email | Email | No | From lead data |
| Phone | Phone | No | Optional |
| LinkedIn Profile | URL | Yes | Primary dedup identifier |
| Interview Notes | Long Text | No | Gemini notes (temporary — moves to comments in Phase 6) |
| Rating | Rating (1-5) | No | Isaac's assessment |
| Interview Date | Date | No | Google Meet date |
| Salary Expectation | Currency | No | From interview |

### 6. Test with Sample Candidate
Create one test candidate in Sr. Software Engineer:
- Name: "Test Candidate — DELETE ME"
- Channel: Instantly
- Campaign: Test-Campaign-v1
- LinkedIn: linkedin.com/in/test
- Email: test@example.com
- Status: Outreach Sent

Verify:
- [ ] All custom fields populate correctly
- [ ] Status changes work (drag between columns)
- [ ] Board view shows correct columns
- [ ] Candidate detail shows all fields
- [ ] Delete test candidate when done

## Success Criteria
- SmartState Space exists with 3 Job Folders
- Each folder has a Candidates list with correct statuses
- All 11 custom fields are available on every list
- Board view shows the full outreach → recruitment pipeline
