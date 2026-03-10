# Phase 6: Gemini Notes Integration

**Status: ✅ COMPLETE**
**Completed: March 2026**

## Objective
Automatically sync Google Meet interview notes from Gemini into the corresponding ClickUp candidate task. Build a full chronological activity log per candidate.

## How It Works

### Detection
A scheduled Claude task (`gemini-notes-to-clickup`) runs every 30 minutes on weekdays 9am-6pm. It:
1. Searches Google Calendar for events containing "iGaming" in the last 24 hours
2. Filters for events that have ended AND have a "Notes by Gemini" attachment
3. Identifies the candidate from the attendee list (non-Isaac, non-Nata email)

### Matching
The automation matches the candidate to a ClickUp task using:
- **Primary:** Candidate's calendar email → exact match across all 8 ClickUp lists
- **Fallback:** Candidate's name from the event title → name search across all lists
- **Priority:** Prefers tasks in "replied" status (most likely to be interview candidates)

### Note Extraction
Gemini notes are stored as a Google Doc attached to the calendar event. The automation:
- Fetches the doc via Google Drive API
- Extracts the Summary and Details sections (skips the full transcript to keep it concise)
- Formats as a timestamped comment with icons

### ClickUp Update
For each matched task:
1. Adds a formatted comment with Gemini notes summary, details, attendees, and doc link
2. Sets the Interview Date field to the calendar event date
3. Moves status to "interviewed" (if currently in "replied" or "outreach sent")

## Calendar Event Convention

### Naming
- **Isaac's interviews:** Event description contains "Isaac iGaming"
- **Nata's interviews:** Event description contains "NATA iGaming"
- Event titles are set by Calendly: "[Candidate Name] and Isaac Marks"

### Structure
Events are created via Calendly with Google Meet. After the call:
- Gemini auto-generates notes and attaches them to the calendar event
- The attachment appears as a Google Doc with title: "[Names] - [date] - Notes by Gemini"
- The doc contains: Summary, Details (bullet points), and full Transcript

## Comment Format in ClickUp
```
🎥 Interview on Google Meet — Mar 9, 2026, 2:30 PM EDT

📝 Gemini Notes Summary:
[AI-generated summary of the interview]

📋 Details:
[Bullet-point details from Gemini]

📅 Calendar Event: [event title]
👤 Attendees: [email list]
🔗 Notes Doc: [link to Google Doc]
```

## Test Results
Successfully tested with the Regis Kian interview (Mar 9, 2026):
- ✅ Found "iGaming" event on Google Calendar with Gemini notes attachment
- ✅ Fetched Gemini doc (4,974 chars including summary, details, transcript)
- ✅ Matched regisksc@gmail.com to ClickUp task in Senior Flutter Developer list
- ✅ Added formatted comment with interview summary and details
- ✅ Updated Interview Date to 2026-03-09
- ✅ Moved status from "replied" → "interviewed"
- ✅ Verified task at https://app.clickup.com/t/86b8tqye4

## Scheduled Task
- **Task ID:** gemini-notes-to-clickup
- **Schedule:** Every 30 minutes, weekdays 9am-6pm ET
- **Location:** ~/Documents/Claude/Scheduled/gemini-notes-to-clickup/SKILL.md

## Known Considerations
- **Email mismatch:** Some candidates use different emails for calendar vs. their ClickUp profile (e.g., Tony Kakai: clynton.kakai@gmail.com on Calendar vs. ckakai17@gsb.columbia.edu in ClickUp). Name fallback handles this.
- **Multiple matches:** When a candidate appears in multiple job lists, the automation prefers the "replied" status task.
- **Duplicate prevention:** The scheduled task checks if "Gemini Notes Summary" comment already exists before re-processing.
- **Candidate Rating:** The rating field is an emoji star (max 3), not 1-5. Isaac rates manually after reviewing notes.

## Dependencies
- Phase 1 complete (✅ — ClickUp tasks exist)
- Google Calendar connector (✅ — connected)
- Google Drive connector (✅ — connected for Gemini doc fetching)
- Gemini note-taking enabled on Google Meet (✅ — confirmed working)
