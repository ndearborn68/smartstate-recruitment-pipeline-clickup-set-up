# Phase 6: Gemini Notes Integration

## Objective
Every Google Meet interview note captured by Gemini gets pushed as a timestamped comment on the candidate's ClickUp task. Build a full chronological activity log per candidate.

## Design

### 6.1 Activity Log (Task Comments)
Each candidate task should have a complete chronological history in its comments:

```
[Mar 2, 2026] 📧 Outreach sent via Instantly — Campaign: SmartState-SWE-Q1
[Mar 7, 2026] ↩️ Replied — "Interested, would love to learn more about the role"
[Mar 8, 2026] 📞 Screening call scheduled for Mar 10
[Mar 10, 2026] 📞 Screening call completed — Notes: [summary]
[Mar 12, 2026] 🎥 Interview on Google Meet — Gemini Notes:
    - Strong React/TypeScript skills
    - 5 years experience, Series B startup
    - Led Vue → React migration
    - Salary range $125-135k
    - Available in 2 weeks
    - Recommendation: Submit to client
[Mar 12, 2026] 📤 Submitted to SmartState
[Mar 15, 2026] ✅ SmartState feedback: Moving to final round
```

### 6.2 Gemini Notes Workflow
1. Isaac conducts interview on Google Meet
2. Gemini captures meeting notes automatically
3. After the call, Isaac copies Gemini notes
4. Isaac tells Claude: "Add interview notes for [Name]: [paste notes]"
5. Claude creates a timestamped comment on the task (not a field update)
6. Claude updates status to "Interviewed" and sets Interview Date

### 6.3 Future Automation (Optional)
- Google Meet API / Gemini API integration to auto-push notes
- Would eliminate the manual copy-paste step
- Depends on API availability and permissions

## Implementation
- Use ClickUp's `clickup_create_task_comment` MCP tool
- Format comments with timestamps and activity type icons
- Every interaction gets logged as a comment, not just interview notes

## Dependencies
- Phase 1-2 complete (tasks exist, Claude can update them)
- Google Meet with Gemini note-taking enabled

## Success Criteria
- Every candidate task has a full activity log in comments
- Gemini interview notes appear as formatted, timestamped comments
- Activity log is chronological and easy to scan
