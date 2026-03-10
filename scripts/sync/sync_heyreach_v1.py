import os
import requests
import json
import time
from datetime import datetime

# === CONFIG ===
HEYREACH_API_KEY = os.environ.get("HEYREACH_API_KEY", "YOUR_HEYREACH_KEY")
CLICKUP_TOKEN = os.environ.get("CLICKUP_API_TOKEN", "YOUR_CLICKUP_TOKEN")

HEYREACH_HEADERS = {
    "X-API-KEY": HEYREACH_API_KEY,
    "Content-Type": "application/json"
}
CLICKUP_HEADERS = {
    "Authorization": CLICKUP_TOKEN,
    "Content-Type": "application/json"
}

# Custom field IDs
EMAIL_FIELD_ID = "43b5c0f0-5de1-486c-9a5d-4c3c34afd97d"
NOTES_FIELD_ID = "5dc608ba-565f-41e0-8063-ca5c8681ed88"
LINKEDIN_FIELD_ID = "cdc5ce8e-daa9-4279-9f8b-63f325085f62"
CHANNEL_FIELD_ID = "c161752a-3a35-467d-bef6-ab76c245cceb"
CAMPAIGN_FIELD_ID = "549a80b8-22cf-4eba-9df0-d3ce52ad4bd8"
DATE_CONTACTED_FIELD_ID = "23315184-23b5-44b7-b25e-a04ddc6ed9c0"
DATE_REPLIED_FIELD_ID = "8638fc92-086c-455a-8a72-dfc750df7233"
PHONE_FIELD_ID = "a340a4f0-23ae-4678-a722-604d4c81f0ff"

# Channel dropdown IDs
HEYREACH_CHANNEL_ID = "b47a6098-b305-4dad-a20e-f16cb4fdbafb"

# Heyreach campaigns -> ClickUp lists
# Product Manager campaign -> Senior Product Manager list
# Mid Flutter campaign -> Mid-Level Flutter Developer list
HEYREACH_CAMPAIGNS = {
    354909: {"name": "Product Manager", "list_id": "901414414435"},
    349645: {"name": "Mid Flutter", "list_id": "901414414372"},
}

# ClickUp status IDs
STATUS_OUTREACH = "outreach sent"
STATUS_REPLIED = "replied"

# === STEP 1: Fetch all conversations from Heyreach ===
print("=== STEP 1: Fetching Heyreach conversations ===")

all_conversations = {}  # campaign_id -> list of conversations

for camp_id, info in HEYREACH_CAMPAIGNS.items():
    camp_name = info["name"]
    print(f"\nFetching {camp_name} (ID: {camp_id})...")

    conversations = []
    offset = 0
    limit = 50

    while True:
        resp = requests.post(
            "https://api.heyreach.io/api/public/inbox/GetConversationsV2",
            headers=HEYREACH_HEADERS,
            json={"campaignId": camp_id, "offset": offset, "limit": limit}
        )

        if resp.status_code != 200:
            print(f"  ERROR: {resp.status_code} {resp.text[:200]}")
            break

        data = resp.json()
        items = data.get("items", [])
        total = data.get("totalCount", 0)

        if not items:
            break

        conversations.extend(items)
        offset += limit

        if offset % 200 == 0:
            print(f"  Fetched {len(conversations)}/{total} conversations...")

        if offset >= total:
            break

        time.sleep(0.25)

    all_conversations[camp_id] = conversations
    print(f"  {camp_name}: {len(conversations)} conversations fetched (total available: {total})")

# === STEP 2: Process conversations into lead data ===
print("\n=== STEP 2: Processing conversations ===")

# For each campaign, build: linkedin_url -> {notes, first_contact_date, reply_date, email, name, linkedin, phone}
campaign_lead_data = {}

for camp_id, conversations in all_conversations.items():
    camp_name = HEYREACH_CAMPAIGNS[camp_id]["name"]
    lead_data = {}

    for conv in conversations:
        profile = conv.get("correspondentProfile", {})
        linkedin_url = profile.get("profileUrl", "")
        if not linkedin_url:
            continue

        first_name = profile.get("firstName", "")
        last_name = profile.get("lastName", "")
        email = profile.get("emailAddress", "") or profile.get("customEmailAddress", "")
        headline = profile.get("headline", "")

        messages = conv.get("messages", [])
        if not messages:
            continue

        # Sort messages by time
        messages.sort(key=lambda m: m.get("createdAt", ""))

        # Build notes: last sent + all replies
        last_sent = None
        replies = []
        first_contact = None

        for msg in messages:
            sender = msg.get("sender", "")
            body = msg.get("body", "")
            created = msg.get("createdAt", "")

            if sender == "ME":
                last_sent = msg
                if not first_contact:
                    first_contact = created
            elif sender == "CORRESPONDENT":
                replies.append(msg)

        parts = []
        if last_sent:
            ts = last_sent["createdAt"][:10] if last_sent.get("createdAt") else "?"
            body = last_sent.get("body", "")
            if len(body) > 500:
                body = body[:500] + "..."
            parts.append(f"--- LAST SENT via LinkedIn ({ts}) ---\n{body}")

        for reply in replies:
            ts = reply["createdAt"][:10] if reply.get("createdAt") else "?"
            body = reply.get("body", "")
            if len(body) > 500:
                body = body[:500] + "..."
            parts.append(f"--- REPLY FROM {first_name} {last_name} ({ts}) ---\n{body}")

        notes = '\n\n'.join(parts) if parts else ""

        # Get earliest reply date
        reply_date = None
        if replies:
            reply_date = replies[0].get("createdAt")

        has_reply = len(replies) > 0

        lead_data[linkedin_url] = {
            "notes": notes,
            "email": email,
            "first_name": first_name,
            "last_name": last_name,
            "linkedin": linkedin_url,
            "first_contact": first_contact,
            "reply_date": reply_date,
            "has_reply": has_reply,
            "headline": headline,
        }

    campaign_lead_data[camp_id] = lead_data
    replied_count = sum(1 for v in lead_data.values() if v["has_reply"])
    with_email = sum(1 for v in lead_data.values() if v["email"])
    print(f"  {camp_name}: {len(lead_data)} leads processed | {replied_count} replied | {with_email} have email")

# === STEP 3: Fetch existing ClickUp tasks and update/create ===
print("\n=== STEP 3: Updating ClickUp tasks ===")

total_new = 0
total_updated = 0
total_skipped = 0
req_count = 0

for camp_id, info in HEYREACH_CAMPAIGNS.items():
    list_id = info["list_id"]
    camp_name = info["name"]
    lead_data = campaign_lead_data.get(camp_id, {})

    if not lead_data:
        print(f"\n--- {camp_name}: No lead data, skipping ---")
        continue

    print(f"\n--- {camp_name} (List {list_id}): {len(lead_data)} leads to process ---")

    # Fetch existing tasks
    all_tasks = []
    page = 0
    while True:
        url = f"https://api.clickup.com/api/v2/list/{list_id}/task?page={page}&include_closed=true"
        resp = requests.get(url, headers=CLICKUP_HEADERS)
        tasks = resp.json().get("tasks", [])
        if not tasks:
            break
        all_tasks.extend(tasks)
        page += 1
        time.sleep(0.7)

    print(f"  Fetched {len(all_tasks)} existing tasks")

    # Build lookup by email and linkedin
    task_by_email = {}
    task_by_linkedin = {}
    for task in all_tasks:
        for cf in task.get("custom_fields", []):
            if cf["id"] == EMAIL_FIELD_ID and cf.get("value"):
                task_by_email[cf["value"].lower().strip()] = task
            if cf["id"] == LINKEDIN_FIELD_ID and cf.get("value"):
                task_by_linkedin[cf["value"].lower().strip()] = task

    new_count = 0
    updated_count = 0
    skipped_count = 0

    for linkedin_url, data in lead_data.items():
        email = data["email"].lower().strip() if data["email"] else ""
        linkedin_lower = linkedin_url.lower().strip()

        # Try to find existing task by email or linkedin
        existing_task = None
        if email:
            existing_task = task_by_email.get(email)
        if not existing_task:
            existing_task = task_by_linkedin.get(linkedin_lower)

        if existing_task:
            # Update existing task: append Heyreach notes, update fields
            task_id = existing_task["id"]

            # Get current notes
            current_notes = ""
            for cf in existing_task.get("custom_fields", []):
                if cf["id"] == NOTES_FIELD_ID:
                    current_notes = cf.get("value", "") or ""

            # Append Heyreach notes
            if data["notes"]:
                if current_notes:
                    new_notes = current_notes + "\n\n=== HEYREACH MESSAGES ===\n\n" + data["notes"]
                else:
                    new_notes = data["notes"]

                resp = requests.post(
                    f"https://api.clickup.com/api/v2/task/{task_id}/field/{NOTES_FIELD_ID}",
                    headers=CLICKUP_HEADERS,
                    json={"value": new_notes}
                )
                req_count += 1
                time.sleep(0.65)

            # Update Date Replied if we have a reply
            if data["reply_date"]:
                try:
                    dt = datetime.fromisoformat(data["reply_date"].replace('Z', '+00:00'))
                    epoch_ms = int(dt.timestamp() * 1000)
                    resp = requests.post(
                        f"https://api.clickup.com/api/v2/task/{task_id}/field/{DATE_REPLIED_FIELD_ID}",
                        headers=CLICKUP_HEADERS,
                        json={"value": epoch_ms}
                    )
                    req_count += 1
                    time.sleep(0.65)
                except:
                    pass

            updated_count += 1

        else:
            # Create new task for Heyreach-only lead
            task_name = f"{data['first_name']} {data['last_name']}".strip() or "Unknown"
            status = STATUS_REPLIED if data["has_reply"] else STATUS_OUTREACH

            custom_fields = [
                {"id": CHANNEL_FIELD_ID, "value": HEYREACH_CHANNEL_ID},
                {"id": CAMPAIGN_FIELD_ID, "value": f"Heyreach: {camp_name}"},
                {"id": LINKEDIN_FIELD_ID, "value": linkedin_url},
            ]

            if data["email"]:
                custom_fields.append({"id": EMAIL_FIELD_ID, "value": data["email"]})

            if data["notes"]:
                custom_fields.append({"id": NOTES_FIELD_ID, "value": data["notes"]})

            if data["first_contact"]:
                try:
                    dt = datetime.fromisoformat(data["first_contact"].replace('Z', '+00:00'))
                    epoch_ms = int(dt.timestamp() * 1000)
                    custom_fields.append({"id": DATE_CONTACTED_FIELD_ID, "value": epoch_ms})
                except:
                    pass

            if data["reply_date"]:
                try:
                    dt = datetime.fromisoformat(data["reply_date"].replace('Z', '+00:00'))
                    epoch_ms = int(dt.timestamp() * 1000)
                    custom_fields.append({"id": DATE_REPLIED_FIELD_ID, "value": epoch_ms})
                except:
                    pass

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
                new_count += 1
            else:
                print(f"  FAILED creating {task_name}: {resp.status_code} {resp.text[:100]}")

            time.sleep(0.65)

        if req_count % 95 == 0 and req_count > 0:
            print(f"  Rate limit pause... (new={new_count}, updated={updated_count})")
            time.sleep(62)

    print(f"  {camp_name}: New={new_count}, Updated={updated_count}, Skipped={skipped_count}")
    total_new += new_count
    total_updated += updated_count
    total_skipped += skipped_count

print(f"\n=== FINAL SUMMARY ===")
print(f"New tasks created: {total_new}")
print(f"Existing tasks updated: {total_updated}")
print(f"Total API requests: {req_count}")
