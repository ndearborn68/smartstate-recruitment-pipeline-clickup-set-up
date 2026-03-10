#!/usr/bin/env python3
"""
Bulk sync remaining Instantly campaigns to ClickUp.
Fetches all leads from campaigns that have 0 tasks in ClickUp and creates tasks.
"""
import requests
import json
import time
from datetime import datetime

INSTANTLY_KEY = "ZmUxYmNiMjQtNjFmOC00Y2NhLWE1NDktZWY5Y2RjYzQ0MGY5OkJzdUxwS3BrQWtpeA=="
CLICKUP_TOKEN = "pk_26113592_F5KRETBMSVF27NK19MNRRV2Y89ATXUE9"

INSTANTLY_HEADERS = {
    "Authorization": f"Bearer {INSTANTLY_KEY}",
    "Content-Type": "application/json"
}
CLICKUP_HEADERS = {
    "Authorization": CLICKUP_TOKEN,
    "Content-Type": "application/json"
}

# Custom field IDs
EMAIL_FIELD = "43b5c0f0-5de1-486c-9a5d-4c3c34afd97d"
LINKEDIN_FIELD = "cdc5ce8e-daa9-4279-9f8b-63f325085f62"
NOTES_FIELD = "5dc608ba-565f-41e0-8063-ca5c8681ed88"
CHANNEL_FIELD = "c161752a-3a35-467d-bef6-ab76c245cceb"
CAMPAIGN_FIELD = "549a80b8-22cf-4eba-9df0-d3ce52ad4bd8"
DATE_CONTACTED_FIELD = "23315184-23b5-44b7-b25e-a04ddc6ed9c0"
DATE_REPLIED_FIELD = "8638fc92-086c-455a-8a72-dfc750df7233"
INSTANTLY_CHANNEL_ID = "f88806c4-396c-4890-a7ff-f93bac1ea00f"

# Campaigns to sync: (instantly_id, campaign_name, clickup_list_id)
CAMPAIGNS = [
    ("ff1fb3e5-4af1-433d-8a7f-d396eba5f0dd", "Senior HTML", "901414414348"),
    ("f241305e-57d5-4812-a278-2fcf68b65f9e", "Mid HTML", "901414414348"),
    ("d0da5edd-293e-4b21-8e35-ce504377362a", "Senior Front End", "901414414393"),
    ("b6a30d37-091e-4ab3-ae7b-6e0674c7d764", "Manual QA Postman", "901414414415"),
    ("0ccefc2b-fa4d-4615-b180-4d17cf27960f", "Senior Back End", "901414414404"),
    ("05f6e117-9187-421f-ad45-951300d2822f", "Affiliate Manager", "901414417420"),
]

total_created = 0
total_skipped = 0
req_count = 0

for camp_id, camp_name, list_id in CAMPAIGNS:
    print(f"\n{'='*60}")
    print(f"CAMPAIGN: {camp_name} ({camp_id[:8]}...) -> List {list_id}")
    print(f"{'='*60}")

    # Step 1: Fetch existing ClickUp tasks for this list (to avoid duplicates)
    existing_emails = set()
    page = 0
    while True:
        resp = requests.get(
            f"https://api.clickup.com/api/v2/list/{list_id}/task?page={page}&include_closed=true",
            headers=CLICKUP_HEADERS
        )
        tasks = resp.json().get("tasks", [])
        if not tasks:
            break
        for t in tasks:
            for cf in t.get("custom_fields", []):
                if cf["id"] == EMAIL_FIELD and cf.get("value"):
                    existing_emails.add(cf["value"].lower().strip())
        page += 1
        req_count += 1
        time.sleep(0.7)

    print(f"  Existing tasks: {len(existing_emails)} emails indexed")

    # Step 2: Fetch all leads from Instantly campaign
    leads = []
    starting_after = None
    while True:
        payload = {"campaign_id": camp_id, "limit": 100}
        if starting_after:
            payload["starting_after"] = starting_after

        resp = requests.post(
            "https://api.instantly.ai/api/v2/leads/list",
            headers=INSTANTLY_HEADERS,
            json=payload
        )
        data = resp.json()
        items = data.get("items", [])
        if not items:
            break
        leads.extend(items)

        # Check if there's a next page
        if len(items) < 100:
            break
        starting_after = items[-1]["id"]
        time.sleep(0.3)

    print(f"  Instantly leads fetched: {len(leads)}")

    # Step 3: Also fetch replies for this campaign
    replies_by_email = {}
    try:
        reply_starting_after = None
        while True:
            url = f"https://api.instantly.ai/api/v2/emails?limit=50&email_type=received&campaign_id={camp_id}"
            if reply_starting_after:
                url += f"&starting_after={reply_starting_after}"
            resp = requests.get(url, headers=INSTANTLY_HEADERS)
            data = resp.json()
            items = data.get("items", [])
            if not items:
                break
            for e in items:
                lead_email = (e.get("lead") or "").lower().strip()
                if lead_email and lead_email not in replies_by_email:
                    name = (e.get("from_address_json") or [{}])[0].get("name", "")
                    body_text = (e.get("body", {}).get("text") or "")[:500]
                    ts = e.get("timestamp_email", "")[:10]
                    interest = e.get("ai_interest_value", "")
                    replies_by_email[lead_email] = {
                        "name": name,
                        "body": body_text,
                        "date": ts,
                        "interest": interest
                    }
                elif lead_email and lead_email in replies_by_email:
                    # Append additional replies
                    body_text = (e.get("body", {}).get("text") or "")[:500]
                    ts = e.get("timestamp_email", "")[:10]
                    replies_by_email[lead_email]["body"] += f"\n\n--- ADDITIONAL REPLY ({ts}) ---\n{body_text}"
            if len(items) < 50:
                break
            reply_starting_after = items[-1]["id"]
            time.sleep(0.3)
    except Exception as ex:
        print(f"  Warning: Could not fetch replies: {ex}")

    print(f"  Replies found: {len(replies_by_email)}")

    # Step 4: Create ClickUp tasks for new leads
    created = 0
    skipped = 0

    for lead in leads:
        email = (lead.get("email") or "").lower().strip()
        if not email:
            continue
        if email in existing_emails:
            skipped += 1
            continue

        first_name = lead.get("first_name") or lead.get("payload", {}).get("firstName", "")
        last_name = lead.get("last_name") or lead.get("payload", {}).get("lastName", "")
        task_name = f"{first_name} {last_name}".strip() or email
        linkedin = (lead.get("payload") or {}).get("person_linkedIn", "")

        # Determine status
        has_reply = email in replies_by_email
        status = "replied" if has_reply else "outreach sent"

        # Build custom fields
        custom_fields = [
            {"id": EMAIL_FIELD, "value": email},
            {"id": CHANNEL_FIELD, "value": INSTANTLY_CHANNEL_ID},
            {"id": CAMPAIGN_FIELD, "value": f"Instantly: {camp_name}"},
        ]

        if linkedin:
            custom_fields.append({"id": LINKEDIN_FIELD, "value": linkedin})

        # Date contacted
        ts_contact = lead.get("timestamp_last_contact") or lead.get("timestamp_created")
        if ts_contact:
            try:
                dt = datetime.fromisoformat(ts_contact.replace('Z', '+00:00'))
                custom_fields.append({"id": DATE_CONTACTED_FIELD, "value": int(dt.timestamp() * 1000)})
            except:
                pass

        # Notes
        notes_parts = []
        if has_reply:
            r = replies_by_email[email]
            interest_label = {1: "Positive", 0: "Neutral", -1: "Not Interested"}.get(r["interest"], str(r["interest"]))
            notes_parts.append(f"=== INSTANTLY (Email) ===\n\n--- REPLY FROM {r['name'] or task_name} ({r['date']}) --- [AI Interest: {interest_label}]\n{r['body']}")

            # Set date replied
            try:
                dt = datetime.fromisoformat(r["date"] + "T00:00:00+00:00")
                custom_fields.append({"id": DATE_REPLIED_FIELD, "value": int(dt.timestamp() * 1000)})
            except:
                pass

        if notes_parts:
            custom_fields.append({"id": NOTES_FIELD, "value": "\n\n".join(notes_parts)})

        # Create task
        payload = {
            "name": task_name,
            "status": status,
            "custom_fields": custom_fields,
        }

        resp = requests.post(
            f"https://api.clickup.com/api/v2/list/{list_id}/task",
            headers=CLICKUP_HEADERS,
            json=payload
        )
        req_count += 1

        if resp.status_code == 200:
            created += 1
            existing_emails.add(email)
        else:
            print(f"  FAILED creating {task_name}: {resp.status_code} {resp.text[:100]}")

        time.sleep(0.7)

        if req_count % 90 == 0:
            print(f"  Rate limit pause... ({created} created so far)")
            time.sleep(62)

    print(f"  Created: {created} | Skipped (dupe): {skipped}")
    total_created += created
    total_skipped += skipped

print(f"\n{'='*60}")
print(f"BULK SYNC COMPLETE")
print(f"Total created: {total_created}")
print(f"Total skipped: {total_skipped}")
print(f"Total API requests: {req_count}")
print(f"{'='*60}")
