# SmartState Recruitment Pipeline — TODO

Last updated: 2026-03-22

## Completed ✅
- [x] Database schema (candidates, jobs, campaigns, messages, candidate_sources)
- [x] 557 candidates imported across 17 campaigns / 8 job roles
- [x] sync-heyreach Edge Function (LinkedIn replies → DB → Slack → ClickUp)
- [x] sync-instantly Edge Function (email replies → DB → Slack → ClickUp)
- [x] slack-notify Edge Function (reply notifications → #smartstate-responses)
- [x] push-to-clickup Edge Function (status sync → ClickUp tasks)
- [x] weekly-report Edge Function (Monday 8am → #smartstate-performance)
- [x] sms-reply-handler Edge Function (Twilio inbound SMS → Slack)
- [x] nonresponder Edge Function (daily 9am → 2-day non-responders → Clay)
- [x] Clay "All Non-Responders" table — routing logic complete (SMS / Instantly / InMail)
- [x] Calendly booking check in nonresponder (skip Clay if already booked)
- [x] Twilio 10DLC Brand + Campaign registered (outbound pending carrier approval ~Mar 25)
- [x] Fixed 146/175 bad candidate names via LeadMagic + LinkedIn URL slug parsing
- [x] 29 unresolvable usernames held back from Clay (nonresponder_flagged_at set)

---

## In Progress 🔄
- [ ] **Twilio outbound SMS** — carrier approval pending (~Mar 25 2026). Once approved, Clay SMS route will activate automatically.
- [ ] **LinkedIn Recruiter scraper first live run** — `scripts/sync/sync_linkedin_recruiter.py` added; pending `.env` service role key + launchd install + first successful write.
- [ ] **29 unresolvable names** — need LeadMagic retry (after rate limit resets) or manual lookup:
  `admin, amadogon49, aytunch, billandstacey, bwkim10, cfvalencia9277, cpow85, czerintonkr, djcrazed06, dugda, esteakshapin, gilneas12144, hitcklife, hnzwllms, ichaelm1, jandjincarmel, kcha303, keithythefrog, koshkafilmscompany, mazara27, meeby1030, mgbvox, ranran123, redhedsrrare06, satoshidg3104, showpony64, sta26, tulaneadam21, xtrordinary`

---

## Not Built Yet ❌

### LinkedIn Recruiter Scraper
- Candidates messaged via LinkedIn Recruiter (not HeyReach) are NOT in the DB
- Code added: `scripts/sync/sync_linkedin_recruiter.py`
- Planned schedule: launchd daily at 8:45am, ahead of the 9:00am cloud nonresponder run
- Pulls project candidates from Recruiter via Chrome CDP, fetches public LinkedIn URLs + InMail timestamps, writes to Supabase, and lets nonresponder pick them up
- Recruiter projects: PM (1661933460), Flutter (1661750948), HTML CSS (1440335625)
- Chrome CDP tab tested and works

### Gmail Sync
- Needed for detecting LinkedIn Recruiter InMail replies via Gmail notifications
- Depends on LinkedIn Recruiter scraper being built first

### Gemini Note Logging
- AI-generated call/screening notes logged back to candidate record in DB + ClickUp
- Phase 6 — not yet scoped

### SLA Alerts
- Flag candidates stuck in a stage too long (e.g. no status change in 5+ days)
- Post alert to Slack
- Phase 5 — not yet scoped
