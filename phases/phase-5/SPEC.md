# Phase 5: SLAs, Alerts, and Reporting

## Objective
Prevent leads from going cold with time-based alerts. Build a metrics dashboard for internal tracking and client reporting.

## SLA Alerts

### 5.1 Stale Lead Alerts
| Trigger | Alert |
|---------|-------|
| Task in "Replied" > 48 hours | "⚠️ [Name] replied 2 days ago — no action taken" |
| Task in "Screening" > 5 days | "⚠️ [Name] has been in Screening for 5 days" |
| Task in "Submitted to Client" > 7 days | "⚠️ Waiting on SmartState feedback for [Name] — 7 days" |
| Task in "Client Review" > 10 days | "⚠️ [Name] in Client Review for 10 days — follow up" |

### 5.2 Alert Delivery
- ClickUp notification to Isaac
- Slack message to #smartstate-replies (or dedicated #smartstate-alerts channel)

## Reporting Dashboard

### 5.3 Metrics to Track
**Outreach Metrics:**
- Total leads contacted per channel (Instantly / Heyreach / LI Recruiter)
- Response rate per channel (replies / outreach sent)
- Response rate per campaign/sequence

**Pipeline Metrics:**
- Candidates per stage (funnel visualization)
- Conversion rate: Replied → Screening → Interviewed → Submitted → Hired
- Average time-in-stage per step
- Time-to-fill per job (first outreach → hired)

**Channel Attribution:**
- Which channel produces the most replies?
- Which channel produces the most hires?
- Cost-per-hire per channel (if cost data available)

### 5.4 Client-Facing Report
Weekly or on-demand summary for SmartState:
- Total candidates contacted this period
- Response / interview / submission counts
- Current pipeline snapshot per job
- Key candidates in play

### 5.5 Implementation
- **ClickUp Dashboard:** Native dashboard with widgets (counts, charts, time tracking)
- **Custom HTML Dashboard:** If ClickUp dashboards are too limited, build a standalone dashboard that queries ClickUp data
- **Scheduled Claude Report:** Weekly scheduled task that pulls ClickUp data and generates a formatted report

## Dependencies
- Phase 1-3 complete (data flowing consistently)
- Consistent use of Date Contacted, Date Replied, and status timestamps

## Success Criteria
- Stale lead alerts fire accurately based on time-in-stage
- Dashboard shows real-time pipeline metrics
- Client report can be generated on demand
