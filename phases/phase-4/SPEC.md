# Phase 4: Slack Notifications

## Objective
Real-time Slack alerts when any candidate replies on any channel. All RecruitCloud recruiters see it immediately.

## Setup

### 4.1 Slack Channel
- **Channel name:** #smartstate-replies (or similar)
- **Members:** All RecruitCloud recruiters working on SmartState
- **Purpose:** Real-time candidate reply notifications

### 4.2 Notification Trigger
When any candidate task in ClickUp moves to status **"Replied"**, post to Slack.

### 4.3 Slack Message Format
```
🔔 *New Reply — Sr. Software Engineer*
👤 *Sarah Chen* replied via Instantly
📧 Campaign: SmartState-SWE-Q1
📅 Contacted: Mar 2 → Replied: Mar 7
🔗 <ClickUp task link>
```

### 4.4 Channel-Specific Formatting
- Instantly replies: 📧 icon, show campaign name
- Heyreach replies: 💬 icon, show sequence name
- LI Recruiter replies: 🔵 icon, note "via Gmail notification"
- Inbound: 📥 icon, note "new inbound candidate"

## Implementation Options
1. **ClickUp Automation → Slack:** ClickUp native automation triggers on status change → sends Slack message
2. **Zapier/Make:** ClickUp webhook on status change → format message → Slack API
3. **Claude scheduled task:** Periodic check for new "Replied" tasks → post to Slack

## Dependencies
- Phase 1 complete (statuses exist)
- Phase 3 complete (auto-reply detection feeding status changes)
- Slack workspace access
- Slack bot/app or integration token

## Success Criteria
- Every reply across all channels triggers a Slack notification within 5 minutes
- Message includes candidate name, job, channel, and ClickUp link
- All recruiters in the channel see the notification
