import os
import json
import requests
import time

API_TOKEN = os.environ.get("CLICKUP_API_TOKEN", "YOUR_CLICKUP_TOKEN")
HEADERS = {"Authorization": API_TOKEN, "Content-Type": "application/json"}

# Product Owner list = Senior Product Manager Candidates
LIST_ID = "901414414435"
EMAIL_FIELD_ID = "43b5c0f0-5de1-486c-9a5d-4c3c34afd97d"
LINKEDIN_FIELD_ID = "cdc5ce8e-daa9-4279-9f8b-63f325085f62"

# Load LinkedIn mapping
with open("/sessions/eloquent-trusting-pasteur/po_linkedin_map.json") as f:
    linkedin_map = json.load(f)

print(f"Loaded {len(linkedin_map)} LinkedIn mappings")

# Fetch all tasks from the list (paginated)
all_tasks = []
page = 0
while True:
    url = f"https://api.clickup.com/api/v2/list/{LIST_ID}/task?page={page}&include_closed=true"
    resp = requests.get(url, headers=HEADERS)
    data = resp.json()
    tasks = data.get("tasks", [])
    if not tasks:
        break
    all_tasks.extend(tasks)
    print(f"Fetched page {page}: {len(tasks)} tasks")
    page += 1
    time.sleep(0.7)

print(f"Total tasks: {len(all_tasks)}")

# Build email -> task_id mapping
updated = 0
skipped = 0
not_found = 0
already_set = 0
req_count = 0

for task in all_tasks:
    # Get email from custom fields
    email = None
    current_linkedin = None
    for cf in task.get("custom_fields", []):
        if cf["id"] == EMAIL_FIELD_ID:
            email = cf.get("value")
        if cf["id"] == LINKEDIN_FIELD_ID:
            current_linkedin = cf.get("value")

    if not email:
        skipped += 1
        continue

    email_lower = email.lower().strip()

    # Check if we have LinkedIn for this email
    linkedin_entry = linkedin_map.get(email_lower) or linkedin_map.get(email)
    if not linkedin_entry:
        not_found += 1
        continue

    linkedin_url = linkedin_entry["linkedin"]

    # Skip if already set
    if current_linkedin and current_linkedin.strip():
        already_set += 1
        continue

    # Update the task
    task_id = task["id"]
    update_url = f"https://api.clickup.com/api/v2/task/{task_id}/field/{LINKEDIN_FIELD_ID}"
    payload = {"value": linkedin_url}

    resp = requests.post(update_url, headers=HEADERS, json=payload)
    req_count += 1

    if resp.status_code == 200:
        updated += 1
        print(f"✓ Updated {email} -> {linkedin_url}")
    else:
        print(f"✗ Failed {email}: {resp.status_code} {resp.text}")

    # Rate limiting
    time.sleep(0.65)
    if req_count % 95 == 0:
        print("Rate limit pause (62s)...")
        time.sleep(62)

print(f"\n=== RESULTS ===")
print(f"Updated: {updated}")
print(f"Already set: {already_set}")
print(f"No LinkedIn match: {not_found}")
print(f"No email on task: {skipped}")
print(f"Total tasks: {len(all_tasks)}")
