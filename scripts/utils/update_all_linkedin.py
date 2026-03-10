import os
import json
import requests
import time

API_TOKEN = os.environ.get("CLICKUP_API_TOKEN", "YOUR_CLICKUP_TOKEN")
HEADERS = {"Authorization": API_TOKEN, "Content-Type": "application/json"}

EMAIL_FIELD_ID = "43b5c0f0-5de1-486c-9a5d-4c3c34afd97d"
LINKEDIN_FIELD_ID = "cdc5ce8e-daa9-4279-9f8b-63f325085f62"

# Load LinkedIn mappings
with open("/sessions/eloquent-trusting-pasteur/linkedin_maps_all.json") as f:
    linkedin_maps = json.load(f)

# Process each campaign's ClickUp list
for camp_id, info in linkedin_maps.items():
    list_id = info["list_id"]
    email_linkedin = info["email_linkedin"]
    camp_name = info["name"]

    if not email_linkedin:
        print(f"\n=== {camp_name}: No LinkedIn data to update, skipping ===")
        continue

    print(f"\n=== {camp_name} (List {list_id}): {len(email_linkedin)} LinkedIn URLs to apply ===")

    # Fetch all tasks from ClickUp list
    all_tasks = []
    page = 0
    while True:
        url = f"https://api.clickup.com/api/v2/list/{list_id}/task?page={page}&include_closed=true"
        resp = requests.get(url, headers=HEADERS)
        data = resp.json()
        tasks = data.get("tasks", [])
        if not tasks:
            break
        all_tasks.extend(tasks)
        page += 1
        time.sleep(0.7)

    print(f"  Fetched {len(all_tasks)} tasks from ClickUp")

    updated = 0
    already_set = 0
    no_match = 0
    req_count = 0

    for task in all_tasks:
        email = None
        current_linkedin = None
        for cf in task.get("custom_fields", []):
            if cf["id"] == EMAIL_FIELD_ID:
                email = cf.get("value")
            if cf["id"] == LINKEDIN_FIELD_ID:
                current_linkedin = cf.get("value")

        if not email:
            continue

        email_lower = email.lower().strip()
        linkedin_url = email_linkedin.get(email_lower)

        if not linkedin_url:
            no_match += 1
            continue

        if current_linkedin and current_linkedin.strip():
            already_set += 1
            continue

        # Update
        task_id = task["id"]
        update_url = f"https://api.clickup.com/api/v2/task/{task_id}/field/{LINKEDIN_FIELD_ID}"
        resp = requests.post(update_url, headers=HEADERS, json={"value": linkedin_url})
        req_count += 1

        if resp.status_code == 200:
            updated += 1
        else:
            print(f"  FAILED {email}: {resp.status_code}")

        time.sleep(0.65)
        if req_count % 95 == 0:
            print(f"  Rate limit pause... ({updated} updated so far)")
            time.sleep(62)

    print(f"  RESULTS: Updated={updated}, Already set={already_set}, No match={no_match}")

print("\n=== ALL DONE ===")
