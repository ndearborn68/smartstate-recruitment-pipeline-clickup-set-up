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
HEYREACH_CHANNEL_ID = "b47a6098-b305-4dad-a20e-f16cb4fdbafb"

STATUS_OUTREACH = "outreach sent"
STATUS_REPLIED = "replied"

# Heyreach campaigns
# Both share the same lead list (549463) with 184 users
# Product Manager started 2026-03-06, Mid Flutter started 2026-03-03
HEYREACH_CAMPAIGNS = {
    354909: {"name": "Product Manager", "list_id": "901414414435", "started": "2026-03-06"},
    349645: {"name": "Mid Flutter", "list_id": "901414414372", "started": "2026-03-03"},
}

# === STEP 1: Fetch conversations (shared pool, only fetch once) ===
print("=== STEP 1: Fetching Heyreach conversations (shared list) ===")

# Use Product Manager campaign to fetch all conversations
conversations = []
offset = 0
limit = 50

while True:
    resp = requests.post(
        "https://api.heyreach.io/api/public/inbox/GetConversationsV2",
        headers=HEYREACH_HEADERS,
        json={"campaignId": 354909, "offset": offset, "limit": limit}
    )
    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code}")
        break
    data = resp.json()
    items = data.get("items", [])
    total = data.get("totalCount", 0)
    if not items:
        break
    conversations.extend(items)
    offset += limit
    if offset % 500 == 0:
        print(f"  Fetched {len(conversations)}/{total}...")
    if offset >= total:
        break
    time.sleep(0.2)

print(f"Total conversations: {len(conversations)}")

# === STEP 2: Process into lookup by LinkedIn URL ===
print("\n=== STEP 2: Processing conversations ===")

conv_by_linkedin = {}
for conv in conversations:
    profile = conv.get("correspondentProfile", {})
    linkedin_url = profile.get("profileUrl", "")
    if not linkedin_url:
        continue

    messages = conv.get("messages", [])
    if not messages:
        continue

    messages.sort(key=lambda m: m.get("createdAt", ""))

    last_sent = None
    replies = []
    first_contact = None

    for msg in messages:
        if msg.get("sender") == "ME":
            last_sent = msg
            if not first_contact:
                first_contact = msg.get("createdAt")
        elif msg.get("sender") == "CORRESPONDENT":
            replies.append(msg)

    parts = []
    if last_sent:
        ts = last_sent.get("createdAt", "?")[:10]
        body = last_sent.get("body", "")[:500]
        parts.append(f"--- LAST SENT via LinkedIn ({ts}) ---\n{body}")

    for reply in replies:
        ts = reply.get("createdAt", "?")[:10]
        fname = profile.get("firstName", "")
        lname = profile.get("lastName", "")
        body = reply.get("body", "")[:500]
        parts.append(f"--- REPLY FROM {fname} {lname} ({ts}) ---\n{body}")

    conv_by_linkedin[linkedin_url.lower().strip()] = {
        "notes": "\n\n".join(parts),
        "email": (profile.get("emailAddress") or profile.get("customEmailAddress") or "").lower().strip(),
        "first_name": profile.get("firstName", ""),
        "last_name": profile.get("lastName", ""),
        "linkedin": linkedin_url,
        "first_contact": first_contact,
        "reply_date": replies[0].get("createdAt") if replies else None,
        "has_reply": len(replies) > 0,
        "has_messages": last_sent is not None,
    }

# Also build email lookup
conv_by_email = {}
for li, data in conv_by_linkedin.items():
    if data["email"]:
        conv_by_email[data["email"]] = data

print(f"Conversations indexed: {len(conv_by_linkedin)} by LinkedIn, {len(conv_by_email)} by email")
print(f"With messages sent: {sum(1 for v in conv_by_linkedin.values() if v['has_messages'])}")
print(f"With replies: {sum(1 for v in conv_by_linkedin.values() if v['has_reply'])}")

# === STEP 3: For each ClickUp list, update existing tasks + create new Heyreach-only leads ===
print("\n=== STEP 3: Updating ClickUp tasks ===")

total_updated = 0
total_new = 0
req_count = 0

for camp_id, info in HEYREACH_CAMPAIGNS.items():
    list_id = info["list_id"]
    camp_name = info["name"]
    camp_started = info["started"]

    print(f"\n--- {camp_name} (List {list_id}) ---")

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

    print(f"  Existing tasks: {len(all_tasks)}")

    # Build lookups
    existing_emails = set()
    existing_linkedins = set()
    updated = 0

    for task in all_tasks:
        task_email = None
        task_linkedin = None
        current_notes = ""
        for cf in task.get("custom_fields", []):
            if cf["id"] == EMAIL_FIELD_ID and cf.get("value"):
                task_email = cf["value"].lower().strip()
            if cf["id"] == LINKEDIN_FIELD_ID and cf.get("value"):
                task_linkedin = cf["value"].lower().strip()
            if cf["id"] == NOTES_FIELD_ID:
                current_notes = cf.get("value", "") or ""

        if task_email:
            existing_emails.add(task_email)
        if task_linkedin:
            existing_linkedins.add(task_linkedin)

        # Try to match to Heyreach conversation
        hr_data = None
        if task_email:
            hr_data = conv_by_email.get(task_email)
        if not hr_data and task_linkedin:
            hr_data = conv_by_linkedin.get(task_linkedin)

        if hr_data and hr_data["notes"]:
            task_id = task["id"]

            # Append Heyreach notes
            if current_notes:
                new_notes = current_notes + "\n\n=== HEYREACH (LinkedIn) ===\n\n" + hr_data["notes"]
            else:
                new_notes = hr_data["notes"]

            resp = requests.post(
                f"https://api.clickup.com/api/v2/task/{task_id}/field/{NOTES_FIELD_ID}",
                headers=CLICKUP_HEADERS,
                json={"value": new_notes}
            )
            req_count += 1

            # Update LinkedIn if not set
            if not task_linkedin and hr_data["linkedin"]:
                resp2 = requests.post(
                    f"https://api.clickup.com/api/v2/task/{task_id}/field/{LINKEDIN_FIELD_ID}",
                    headers=CLICKUP_HEADERS,
                    json={"value": hr_data["linkedin"]}
                )
                req_count += 1
                time.sleep(0.65)

            # Update reply date if applicable
            if hr_data["reply_date"]:
                try:
                    dt = datetime.fromisoformat(hr_data["reply_date"].replace('Z', '+00:00'))
                    epoch_ms = int(dt.timestamp() * 1000)
                    requests.post(
                        f"https://api.clickup.com/api/v2/task/{task_id}/field/{DATE_REPLIED_FIELD_ID}",
                        headers=CLICKUP_HEADERS,
                        json={"value": epoch_ms}
                    )
                    req_count += 1
                except:
                    pass

            updated += 1
            time.sleep(0.65)

            if req_count % 95 == 0:
                print(f"  Rate limit pause... ({updated} updated)")
                time.sleep(62)

    print(f"  Updated existing tasks: {updated}")
    total_updated += updated

    # Now create new tasks for Heyreach-only leads
    # Only create for leads that had messages sent AND started after campaign start date
    new_count = 0
    for li_url, data in conv_by_linkedin.items():
        # Skip if already exists
        if data["email"] and data["email"] in existing_emails:
            continue
        if li_url in existing_linkedins:
            continue

        # Only create if messages were actually sent and first contact is after campaign start
        if not data["has_messages"]:
            continue
        if data["first_contact"] and data["first_contact"][:10] < camp_started:
            continue

        # Create new task
        task_name = f"{data['first_name']} {data['last_name']}".strip() or "Unknown"
        status = STATUS_REPLIED if data["has_reply"] else STATUS_OUTREACH

        custom_fields = [
            {"id": CHANNEL_FIELD_ID, "value": HEYREACH_CHANNEL_ID},
            {"id": CAMPAIGN_FIELD_ID, "value": f"Heyreach: {camp_name}"},
            {"id": LINKEDIN_FIELD_ID, "value": data["linkedin"]},
        ]

        if data["email"]:
            custom_fields.append({"id": EMAIL_FIELD_ID, "value": data["email"]})
        if data["notes"]:
            custom_fields.append({"id": NOTES_FIELD_ID, "value": data["notes"]})
        if data["first_contact"]:
            try:
                dt = datetime.fromisoformat(data["first_contact"].replace('Z', '+00:00'))
                custom_fields.append({"id": DATE_CONTACTED_FIELD_ID, "value": int(dt.timestamp() * 1000)})
            except:
                pass
        if data["reply_date"]:
            try:
                dt = datetime.fromisoformat(data["reply_date"].replace('Z', '+00:00'))
                custom_fields.append({"id": DATE_REPLIED_FIELD_ID, "value": int(dt.timestamp() * 1000)})
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
            # Track to avoid duplicates in next campaign
            if data["email"]:
                existing_emails.add(data["email"])
            existing_linkedins.add(li_url)
        else:
            print(f"  FAILED {task_name}: {resp.status_code}")

        time.sleep(0.65)
        if req_count % 95 == 0:
            print(f"  Rate limit pause... ({new_count} new)")
            time.sleep(62)

    print(f"  New tasks created: {new_count}")
    total_new += new_count

print(f"\n=== FINAL SUMMARY ===")
print(f"Existing tasks updated with Heyreach notes: {total_updated}")
print(f"New Heyreach-only tasks created: {total_new}")
print(f"Total API requests: {req_count}")
