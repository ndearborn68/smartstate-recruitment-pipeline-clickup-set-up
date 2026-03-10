import os
import requests
import json
import time

API_KEY = os.environ.get("INSTANTLY_API_KEY", "YOUR_INSTANTLY_KEY")
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# Load our original leads data
with open("/sessions/eloquent-trusting-pasteur/instantly_leads.json") as f:
    all_leads = json.load(f)

print(f"Loaded {len(all_leads)} leads from cache")

# SmartState campaigns we synced to ClickUp
SYNCED_CAMPAIGNS = {
    "8b6cb40c-0cb1-41d1-97d1-286b04a01391": {"name": "Senior Flutter", "list_id": "901414417498"},
    "6284a72c-7927-41fe-b7ec-2e1df22e1903": {"name": "Middle Flutter Developer", "list_id": "901414414372"},
    "3cc1f7ae-c1df-4f29-afb1-ff5ff1143780": {"name": "Product Owner", "list_id": "901414414435"},
}

# Filter to just our synced campaigns
campaign_leads = {}
for lead in all_leads:
    camp_id = lead.get("campaign", "")
    if camp_id in SYNCED_CAMPAIGNS:
        if camp_id not in campaign_leads:
            campaign_leads[camp_id] = []
        campaign_leads[camp_id].append(lead)

for camp_id, leads in campaign_leads.items():
    print(f"{SYNCED_CAMPAIGNS[camp_id]['name']}: {len(leads)} leads")

# Now fetch each lead individually to get LinkedIn_personURL
# This is the only way since the list endpoint uses different field naming
linkedin_maps = {}
total_fetched = 0
total_found = 0
req_count = 0

for camp_id, leads in campaign_leads.items():
    camp_name = SYNCED_CAMPAIGNS[camp_id]["name"]
    list_id = SYNCED_CAMPAIGNS[camp_id]["list_id"]
    camp_map = {}
    found = 0

    print(f"\n=== Fetching LinkedIn for {camp_name} ({len(leads)} leads) ===")

    for i, lead in enumerate(leads):
        lead_id = lead["id"]
        email = lead.get("email", "").lower().strip()

        if not email:
            continue

        # Fetch individual lead
        resp = requests.get(
            f"https://api.instantly.ai/api/v2/leads/{lead_id}",
            headers=HEADERS
        )
        req_count += 1

        if resp.status_code == 200:
            data = resp.json()
            payload = data.get("payload", {})
            # Check BOTH field names
            linkedin = (payload.get("LinkedIn_personURL", "") or
                       payload.get("person_linkedIn", "") or
                       payload.get("linkedin", "") or
                       payload.get("LinkedIn", ""))

            if linkedin and linkedin.strip():
                camp_map[email] = linkedin.strip()
                found += 1
        else:
            print(f"  ERROR fetching {lead_id}: {resp.status_code}")

        total_fetched += 1

        if (i + 1) % 25 == 0:
            print(f"  {camp_name}: {i+1}/{len(leads)} fetched, {found} LinkedIn found")

        # Rate limiting - Instantly has rate limits too
        time.sleep(0.15)

    linkedin_maps[camp_id] = {
        "name": camp_name,
        "list_id": list_id,
        "email_linkedin": camp_map,
        "total_leads": len(leads),
        "linkedin_found": found,
        "linkedin_missing": len(leads) - found
    }
    print(f"  {camp_name} DONE: {found}/{len(leads)} have LinkedIn")

# Save
with open("/sessions/eloquent-trusting-pasteur/linkedin_maps_all.json", "w") as f:
    json.dump(linkedin_maps, f)

print(f"\n=== FINAL SUMMARY ===")
total_li = 0
total_leads_count = 0
for camp_id, info in linkedin_maps.items():
    print(f"{info['name']:30s} | Total: {info['total_leads']:4d} | LinkedIn: {info['linkedin_found']:4d} | Missing: {info['linkedin_missing']:4d}")
    total_li += info['linkedin_found']
    total_leads_count += info['total_leads']
print(f"{'TOTAL':30s} | Total: {total_leads_count:4d} | LinkedIn: {total_li:4d} | Missing: {total_leads_count - total_li:4d}")
print(f"\nTotal API requests: {req_count}")
print(f"Saved to linkedin_maps_all.json")
