import os
import requests
import json
import time

API_KEY = os.environ.get("INSTANTLY_API_KEY", "YOUR_INSTANTLY_KEY")
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Fetch ALL leads (no campaign filter) - they all come back anyway
leads = []
starting_after = None
page = 0

while True:
    payload = {"limit": 100}
    if starting_after:
        payload["starting_after"] = starting_after

    resp = requests.post(
        "https://api.instantly.ai/api/v2/leads/list",
        headers=HEADERS,
        json=payload
    )

    if resp.status_code != 200:
        print(f"ERROR: {resp.status_code} {resp.text[:200]}")
        break

    data = resp.json()
    items = data.get("items", [])
    if not items:
        break

    leads.extend(items)
    starting_after = data.get("next_starting_after")
    page += 1

    if page % 10 == 0:
        print(f"  Page {page}: {len(leads)} leads fetched...")

    if not starting_after:
        break

    time.sleep(0.2)

print(f"\nTotal leads fetched: {len(leads)}")

# SmartState campaign IDs -> ClickUp list IDs
CAMPAIGN_MAP = {
    "ff1fb3e5-4af1-433d-8a7f-d396eba5f0dd": {"name": "Senior HTML", "list_id": "901414414348"},
    "f241305e-57d5-4812-a278-2fcf68b65f9e": {"name": "Mid HTML", "list_id": "901414414348"},  # same list
    "d0da5edd-293e-4b21-8e35-ce504377362a": {"name": "Senior Front End", "list_id": "901414414393"},
    "b6a30d37-091e-4ab3-ae7b-6e0674c7d764": {"name": "Manual QA Postman", "list_id": "901414414415"},
    "8b6cb40c-0cb1-41d1-97d1-286b04a01391": {"name": "Senior Flutter", "list_id": "901414417498"},
    "6284a72c-7927-41fe-b7ec-2e1df22e1903": {"name": "Middle Flutter Developer", "list_id": "901414414372"},
    "3cc1f7ae-c1df-4f29-afb1-ff5ff1143780": {"name": "Product Owner", "list_id": "901414414435"},
    "0ccefc2b-fa4d-4615-b180-4d17cf27960f": {"name": "Senior Back End", "list_id": "901414414404"},
    "05f6e117-9187-421f-ad45-951300d2822f": {"name": "Affiliate Manager", "list_id": "901414417420"},
}

# Group leads by campaign and extract LinkedIn
campaign_linkedin = {}
for lead in leads:
    camp_id = lead.get("campaign", "")
    if camp_id not in CAMPAIGN_MAP:
        continue

    email = lead.get("email", "").lower().strip()
    linkedin = lead.get("payload", {}).get("person_linkedIn", "")

    if not email:
        continue

    if camp_id not in campaign_linkedin:
        campaign_linkedin[camp_id] = {"leads": {}, "has_li": 0, "no_li": 0, "total": 0}

    campaign_linkedin[camp_id]["total"] += 1
    if linkedin and linkedin.strip():
        campaign_linkedin[camp_id]["leads"][email] = linkedin.strip()
        campaign_linkedin[camp_id]["has_li"] += 1
    else:
        campaign_linkedin[camp_id]["no_li"] += 1

# Save per-campaign LinkedIn mappings
print("\n=== CAMPAIGN LINKEDIN SUMMARY ===")
all_mappings = {}
for camp_id, info in campaign_linkedin.items():
    camp_name = CAMPAIGN_MAP[camp_id]["name"]
    list_id = CAMPAIGN_MAP[camp_id]["list_id"]
    print(f"{camp_name:30s} | Total: {info['total']:4d} | LinkedIn: {info['has_li']:4d} | Missing: {info['no_li']:4d} | List: {list_id}")
    all_mappings[camp_id] = {
        "name": camp_name,
        "list_id": list_id,
        "email_linkedin": info["leads"],
        "stats": {"total": info["total"], "has_linkedin": info["has_li"], "no_linkedin": info["no_li"]}
    }

with open("/sessions/eloquent-trusting-pasteur/campaign_linkedin_maps.json", "w") as f:
    json.dump(all_mappings, f)

total_li = sum(v["has_li"] for v in campaign_linkedin.values())
total_leads_sm = sum(v["total"] for v in campaign_linkedin.values())
print(f"\n{'SMARTSTATE TOTAL':30s} | Total: {total_leads_sm:4d} | LinkedIn: {total_li:4d} | Missing: {total_leads_sm - total_li:4d}")
print(f"\nSaved to campaign_linkedin_maps.json")
