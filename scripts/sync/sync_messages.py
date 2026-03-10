import os
import requests
import json
import time
import re
from html.parser import HTMLParser

# === CONFIG ===
INSTANTLY_API_KEY = os.environ.get("INSTANTLY_API_KEY", "YOUR_INSTANTLY_KEY")
CLICKUP_TOKEN = os.environ.get("CLICKUP_API_TOKEN", "YOUR_CLICKUP_TOKEN")

INSTANTLY_HEADERS = {
    "Authorization": f"Bearer {INSTANTLY_API_KEY}",
    "Content-Type": "application/json"
}
CLICKUP_HEADERS = {
    "Authorization": CLICKUP_TOKEN,
    "Content-Type": "application/json"
}

NOTES_FIELD_ID = "5dc608ba-565f-41e0-8063-ca5c8681ed88"
EMAIL_FIELD_ID = "43b5c0f0-5de1-486c-9a5d-4c3c34afd97d"
DATE_REPLIED_FIELD_ID = "8638fc92-086c-455a-8a72-dfc750df7233"

# Campaign -> ClickUp list mapping (only synced campaigns)
CAMPAIGN_LISTS = {
    "8b6cb40c-0cb1-41d1-97d1-286b04a01391": {"name": "Senior Flutter", "list_id": "901414417498"},
    "6284a72c-7927-41fe-b7ec-2e1df22e1903": {"name": "Mid-Level Flutter", "list_id": "901414414372"},
    "3cc1f7ae-c1df-4f29-afb1-ff5ff1143780": {"name": "Product Owner", "list_id": "901414414435"},
}

# === HTML STRIPPER ===
class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.skip = False
    def handle_starttag(self, tag, attrs):
        if tag in ('br', 'p', 'div'):
            self.result.append('\n')
        if tag in ('style', 'script'):
            self.skip = True
    def handle_endtag(self, tag):
        if tag in ('style', 'script'):
            self.skip = False
    def handle_data(self, data):
        if not self.skip:
            self.result.append(data)
    def get_text(self):
        return ''.join(self.result)

def strip_html(html):
    s = HTMLStripper()
    s.feed(html)
    text = s.get_text()
    # Clean up multiple newlines
    text = re.sub(r'\n{3,}', '\n\n', text)
    return text.strip()

# === STEP 1: Fetch all emails from Instantly for our campaigns ===
print("=== STEP 1: Fetching emails from Instantly ===")

all_emails = {}  # lead_email -> list of email objects

for camp_id, info in CAMPAIGN_LISTS.items():
    camp_name = info["name"]
    print(f"\nFetching emails for {camp_name}...")

    starting_after = None
    count = 0

    while True:
        params = {"campaign_id": camp_id, "limit": 100}
        if starting_after:
            params["starting_after"] = starting_after

        resp = requests.get(
            "https://api.instantly.ai/api/v2/emails",
            headers=INSTANTLY_HEADERS,
            params=params
        )

        if resp.status_code != 200:
            print(f"  ERROR: {resp.status_code} {resp.text[:200]}")
            break

        data = resp.json()
        items = data.get("items", [])
        if not items:
            break

        for email in items:
            lead_addr = email.get("lead", "").lower().strip()
            if lead_addr:
                if lead_addr not in all_emails:
                    all_emails[lead_addr] = []
                all_emails[lead_addr].append({
                    "timestamp": email.get("timestamp_email", ""),
                    "from": email.get("from_address_email", ""),
                    "to": email.get("to_address_email_list", ""),
                    "subject": email.get("subject", ""),
                    "body_text": email.get("body", {}).get("text", ""),
                    "body_html": email.get("body", {}).get("html", ""),
                    "ue_type": email.get("ue_type"),  # 1=sent, 2=reply, 3=manual
                    "campaign_id": email.get("campaign_id", ""),
                    "content_preview": email.get("content_preview", ""),
                })
                count += 1

        starting_after = data.get("next_starting_after")
        if not starting_after:
            break
        time.sleep(0.2)

    print(f"  {camp_name}: {count} emails fetched")

print(f"\nTotal unique leads with emails: {len(all_emails)}")
total_emails = sum(len(v) for v in all_emails.values())
print(f"Total email messages: {total_emails}")

# === STEP 2: Build notes for each lead ===
print("\n=== STEP 2: Building notes per lead ===")

lead_notes = {}  # email -> formatted notes string
lead_reply_dates = {}  # email -> earliest reply date

for lead_email, emails in all_emails.items():
    # Sort by timestamp
    emails.sort(key=lambda x: x["timestamp"])

    # Find last sent and all replies
    last_sent = None
    replies = []

    for em in emails:
        if em["ue_type"] == 1:  # outbound sent
            last_sent = em
        elif em["ue_type"] in (2, 3):  # reply or manual reply
            replies.append(em)

    if not last_sent and not replies:
        continue

    parts = []

    # Last outbound message
    if last_sent:
        body = last_sent["body_text"] or strip_html(last_sent["body_html"])
        # Truncate long bodies - just get the main message, not quoted replies
        lines = body.split('\n')
        clean_lines = []
        for line in lines:
            if line.strip().startswith('On ') and ('wrote:' in line or 'wrote:' in line):
                break
            if line.strip().startswith('>'):
                break
            clean_lines.append(line)
        body = '\n'.join(clean_lines).strip()
        if len(body) > 500:
            body = body[:500] + "..."

        ts = last_sent["timestamp"][:10] if last_sent["timestamp"] else "?"
        parts.append(f"--- LAST SENT ({ts}) ---\nSubject: {last_sent['subject']}\n{body}")

    # All replies
    for reply in replies:
        body = reply["body_text"] or strip_html(reply["body_html"])
        # Clean up quoted text
        lines = body.split('\n')
        clean_lines = []
        for line in lines:
            if line.strip().startswith('On ') and ('wrote:' in line or 'wrote:' in line):
                break
            if line.strip().startswith('>'):
                break
            clean_lines.append(line)
        body = '\n'.join(clean_lines).strip()
        if len(body) > 500:
            body = body[:500] + "..."

        ts = reply["timestamp"][:10] if reply["timestamp"] else "?"
        from_addr = reply["from"]
        parts.append(f"--- REPLY FROM {from_addr} ({ts}) ---\n{body}")

        # Track earliest reply date
        if reply["timestamp"]:
            if lead_email not in lead_reply_dates or reply["timestamp"] < lead_reply_dates[lead_email]:
                lead_reply_dates[lead_email] = reply["timestamp"]

    if parts:
        lead_notes[lead_email] = '\n\n'.join(parts)

print(f"Notes built for {len(lead_notes)} leads")
print(f"Leads with replies: {len(lead_reply_dates)}")

# === STEP 3: Update ClickUp tasks ===
print("\n=== STEP 3: Updating ClickUp tasks ===")

total_updated = 0
total_skipped = 0
req_count = 0

for camp_id, info in CAMPAIGN_LISTS.items():
    list_id = info["list_id"]
    camp_name = info["name"]

    print(f"\n--- {camp_name} (List {list_id}) ---")

    # Fetch all tasks
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

    print(f"  Fetched {len(all_tasks)} tasks")

    updated = 0
    skipped = 0

    for task in all_tasks:
        # Get email
        email = None
        for cf in task.get("custom_fields", []):
            if cf["id"] == EMAIL_FIELD_ID:
                email = cf.get("value")

        if not email:
            skipped += 1
            continue

        email_lower = email.lower().strip()
        notes = lead_notes.get(email_lower)

        if not notes:
            skipped += 1
            continue

        task_id = task["id"]

        # Update Notes field
        update_url = f"https://api.clickup.com/api/v2/task/{task_id}/field/{NOTES_FIELD_ID}"
        resp = requests.post(update_url, headers=CLICKUP_HEADERS, json={"value": notes})
        req_count += 1

        if resp.status_code != 200:
            print(f"  FAILED notes for {email}: {resp.status_code}")

        # Update Date Replied if we have it
        reply_date = lead_reply_dates.get(email_lower)
        if reply_date:
            # Convert to epoch ms
            from datetime import datetime
            try:
                dt = datetime.fromisoformat(reply_date.replace('Z', '+00:00'))
                epoch_ms = int(dt.timestamp() * 1000)
                reply_url = f"https://api.clickup.com/api/v2/task/{task_id}/field/{DATE_REPLIED_FIELD_ID}"
                resp2 = requests.post(reply_url, headers=CLICKUP_HEADERS, json={"value": epoch_ms})
                req_count += 1
                if resp2.status_code != 200:
                    print(f"  FAILED date_replied for {email}: {resp2.status_code}")
            except Exception as e:
                print(f"  Date parse error for {email}: {e}")

        updated += 1

        # Rate limiting
        time.sleep(0.65)
        if req_count % 95 == 0:
            print(f"  Rate limit pause... ({updated} updated so far)")
            time.sleep(62)

    print(f"  {camp_name}: Updated={updated}, Skipped={skipped}")
    total_updated += updated
    total_skipped += skipped

print(f"\n=== FINAL SUMMARY ===")
print(f"Total tasks updated with notes: {total_updated}")
print(f"Total skipped (no email match): {total_skipped}")
print(f"Total API requests: {req_count}")
