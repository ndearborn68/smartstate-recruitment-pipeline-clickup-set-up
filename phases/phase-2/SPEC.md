# Phase 2: Claude as ClickUp Interface

## Objective
Establish Claude + ClickUp MCP as Isaac's primary interface for managing candidates. All data entry, status updates, and dedup checks go through Claude.

## Capabilities

### 2.1 Create Candidate Tasks
Isaac says: "Add [Name] to [Job], contacted via [Channel], campaign [Name]"
Claude creates a task in the correct job's Candidates list with:
- Task name = candidate name
- Status = Outreach Sent
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
- Channel: LI Recruiter
- Date Contacted: today
- Status: Outreach Sent

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
Isaac says: "Show me all candidates in Screening for Sr. Software Engineer"
Claude queries ClickUp and returns a formatted list.

Other queries:
- "Who's been in Replied for more than 2 days?"
- "How many candidates per channel for Sr. Software Engineer?"
- "Show me all LI Recruiter contacts this week"

## Dependencies
- ClickUp MCP tools must be functional (clickup_create_task, clickup_update_task, clickup_search, etc.)
- Phase 1 must be complete (structure exists)

## Success Criteria
- Claude can create a candidate task with all fields via natural language
- Claude can update any field on an existing task
- Screenshot OCR extracts at least name + LinkedIn from LI Recruiter pages
- Dedup check returns accurate matches across all jobs and channels
