# Phase 2: Claude as ClickUp Interface

**Status: 🔲 NOT STARTED**
**Dependencies: Phase 1 (complete)**

## Objective
Establish Claude + ClickUp MCP as Isaac's primary interface for managing candidates. All data entry, status updates, and dedup checks go through Claude.

## Capabilities

### 2.1 Create Candidate Tasks
Isaac says: "Add [Name] to [Job], contacted via [Channel], campaign [Name]"
Claude creates a task in the correct job's Candidates list with:
- Task name = candidate name
- Status = outreach sent
- Custom fields populated from provided info

Minimum input: Name + Job
Optional at creation: LinkedIn, email, phone, channel, campaign

### 2.2 Update Candidate Tasks
Isaac says: "Update [Name] — [field]: [value]"
Claude finds the task and updates the specified fields.

Examples:
- "Move Sarah Chen to Interviewed"
- "Add LinkedIn for Marcus: linkedin.com/in/marcus"
- "Update Sarah — notes: [paste Gemini notes], rating: 4, salary: $130k"

### 2.3 LinkedIn Recruiter Screenshot OCR
Isaac drops a screenshot of LinkedIn Recruiter "Sent InMails" page.
Claude extracts:
- Names
- LinkedIn profile URLs (if visible)
- Job titles / companies (if visible)

Claude then bulk-creates tasks in ClickUp for the specified job with:
- Channel: LinkedIn Recruiter (option ID: 38839ea6-f705-4fc6-abe0-e18311be12ae)
- Date Contacted: today
- Status: outreach sent

### 2.4 Dedup Checks
Before any outreach, Isaac can ask Claude to check for existing candidates.

**Single check:** "Is linkedin.com/in/sarahchen already in ClickUp?"
→ Claude searches all Candidates lists across all jobs by LinkedIn URL

**Bulk check:** "Check these 20 LinkedIn URLs against ClickUp before I load them into Instantly"
→ Claude cross-references and returns: clear / already contacted (with channel + job)

**Matching logic:**
- Primary: LinkedIn Profile URL (exact match)
- Secondary: Email address (exact match)
- Fuzzy: Name match flagged as "possible duplicate — verify"

### 2.5 Query Candidates
Isaac says: "Show me all candidates in Screening for Sr Front End Developer"
Claude queries ClickUp and returns a formatted list.

Other queries:
- "Who's been in Replied for more than 2 days?"
- "How many candidates per channel for Senior Product Manager?"
- "Show me all LinkedIn Recruiter contacts this week"

## Implementation Notes
- All 8 ClickUp list IDs are documented in `scripts/config_template.py`
- All 11 custom field IDs and channel option IDs are available
- ClickUp API rate limit: 100 requests/minute (Business plan)
- Use the ClickUp MCP tools or direct API calls

## Dependencies
- ClickUp MCP tools must be functional
- Phase 1 complete (✅)

## Success Criteria
- Claude can create a candidate task with all fields via natural language
- Claude can update any field on an existing task
- Screenshot OCR extracts at least name + LinkedIn from LI Recruiter pages
- Dedup check returns accurate matches across all jobs and channels
