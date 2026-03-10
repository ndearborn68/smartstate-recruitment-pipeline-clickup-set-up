# Phase 2: Claude as ClickUp Interface

**Status: ✅ COMPLETE**
**Completed: March 2026**

## Objective
Establish Claude as Isaac's primary interface for managing candidates in ClickUp. All data entry, status updates, dedup checks, and queries go through Claude using the `clickup_manager.py` tool.

## What Was Built

### Tool: `scripts/clickup_manager.py`
A comprehensive Python tool that provides all Phase 2 capabilities via importable functions:

### 2.1 Create Candidate Tasks ✅
**Function:** `create_candidate(job, name, email, linkedin, phone, channel, campaign, status, notes, salary, rating)`

Flexible job name resolution — Isaac can say "PM", "flutter mid", "qa", "backend" etc. and it maps to the correct list.

Example:
```python
create_candidate(job='PM', name='Sarah Chen', email='sarah@example.com',
                 linkedin='https://linkedin.com/in/sarahchen',
                 channel='Instantly', campaign='SmartState-PM-Q1')
```

Automatically sets Date Contacted to now and defaults status to "outreach sent".

### 2.2 Update Candidate Tasks ✅
**Function:** `update_candidate(task_id, status, email, linkedin, phone, channel, campaign, notes, salary, rating, date_replied, interview_date, name)`

Updates any combination of fields on a task. Validates statuses against the 8 valid pipeline statuses.

### 2.3 Find Candidates ✅
**Function:** `find_candidate(name, email, linkedin, job)`

Searches by name (fuzzy), email (exact), or LinkedIn URL (contains match). Searches all 8 lists or a specific job.

### 2.4 Dedup Checks ✅
**Function:** `dedup_check(emails, linkedins, names)`

Bulk-checks lists of identifiers against all 491 tasks across all lists. Returns "clear" or the matching task info for each.

### 2.5 Query Candidates ✅
**Function:** `query_candidates(job, status, channel, limit)`

Filters by job, status, and/or channel. Returns candidate details including all custom fields.

### 2.6 Pipeline Summary ✅
**Function:** `pipeline_summary(job)`

Returns candidate counts per status, overall and broken down by job. Current state:
- 491 total candidates across 3 active campaigns
- 463 in "outreach sent", 28 in "replied"
- Senior Product Manager: 251 (15 replied)
- Mid-Level Flutter Developer: 113 (9 replied)
- Senior Flutter Developer: 127 (4 replied)

### 2.7 Activity Log Comments ✅
**Function:** `add_comment(task_id, comment_text)`

Adds timestamped comments to tasks for the activity log (feeds into Phase 6).

### 2.8 LinkedIn Recruiter Screenshot OCR
**Status:** Ready to use — Claude's native vision handles this. Isaac drops a screenshot, Claude extracts names/URLs, then calls `create_candidate()` in bulk with Channel = "LinkedIn Recruiter".

## Field Type Notes
- **Salary Range:** `short_text` (pass as string like "120k-135k")
- **Candidate Rating:** `emoji` type (star rating, max 3 — not 1-5)
- **Channel:** `dropdown` single-select (use option IDs from CHANNELS dict)
- **Dates:** Pass as ISO string "YYYY-MM-DD" or millisecond timestamp

## Job Name Aliases
The tool supports flexible job name input:
| Input | Resolves To |
|-------|-------------|
| "PM", "product manager", "product owner" | Senior Product Manager |
| "flutter mid", "mid flutter", "middle flutter" | Mid-Level Flutter Developer |
| "senior flutter", "sr flutter" | Senior Flutter Developer |
| "html", "markup", "lead html" | Lead HTML/Markup Developer |
| "frontend", "front end", "sr front end" | Sr Front End Developer |
| "backend", "back end" | Senior Backend Developer |
| "qa", "manual qa" | Senior Manual QA Engineer |
| "affiliate" | Affiliate Manager |

## Test Results
All capabilities verified:
- ✅ Created test candidate with all fields → task appeared in ClickUp
- ✅ Found by name, email, and LinkedIn URL
- ✅ Updated status (outreach sent → screening), rating, salary
- ✅ Added activity log comment
- ✅ Dedup check: found existing by email and LinkedIn, "clear" for non-existent
- ✅ Query by job + status returned filtered results
- ✅ Pipeline summary: 491 total, 28 replied across 3 active campaigns
- ✅ Test candidate deleted after verification

## Dependencies
- Phase 1 complete (✅)
- Python 3 + requests library
- ClickUp API token (set as environment variable or in config)

## Success Criteria — All Met ✅
- ✅ Claude can create a candidate task with all fields via natural language
- ✅ Claude can update any field on an existing task
- ✅ Screenshot OCR ready (Claude vision + create_candidate bulk calls)
- ✅ Dedup check returns accurate matches across all jobs and channels
- ✅ Query and pipeline summary provide real-time reporting
