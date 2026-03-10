import os
import requests
import json
import time

API_KEY = os.environ.get("INSTANTLY_API_KEY", "YOUR_INSTANTLY_KEY")
HEADERS = {
    "Authorization": f"Bearer {API_KEY}",
    "Content-Type": "application/json"
}

# All SmartState campaigns
CAMPAIGNS = {
    "ff1fb3e5-4af1-433d-8a7f-d396eba5f0dd": "Senior HTML",
    "f241305e-57d5-4812-a278-2fcf68b65f9e": "Mid HTML",
    "d0da5edd-293e-4b21-8e35-ce504377362a": "Senior Front End",
    "b6a30d37-091e-4ab3-ae7b-6e0674c7d764": "Manual QA Postman",
    "8b6cb40c-0cb1-41d1-97d1-286b04a01391": "Senior Flutter",
    "6284a72c-7927-41fe-b7ec-2e1df22e1903": "Middle Flutter Developer",
    "3cc1f7ae-c1df-4f29-afb1-ff5ff1143780": "Product Owner",
    "0ccefc2b-fa4d-4615-b180-4d17cf27960f": "Senior Back End",
    "05f6e117-9187-421f-ad45-951300d2822f": "Affiliate Manager",
}

all_results = {}

for camp_id, camp_name in CAMPAIGNS.items():
    print(f"\n=== {camp_name} ({camp_id}) ===")
    leads = []
    starting_after = None

    while True:
        payload = {"campaign_id": camp_id, "limit": 100}
        if starting_after:
            payload["starting_after"] = starting_after

        resp = requests.post(
            "https://api.instantly.ai/api/v2/leads/list",
            headers=HEADERS,
            json=payload
        )

        if resp.status_code != 200:
            print(f"  ERROR: {resp.status_code} {resp.text[:200]}")
            break

        data = resp.json()
        items = data.get("items", [])
        if not items:
            break

        leads.extend(items)
        starting_after = data.get("next_starting_after")
        print(f"  Fetched {len(items)} leads (total: {len(leads)}), next: {starting_after}")

        if not starting_after:
            break

        time.sleep(0.3)

    # Count LinkedIn
    has_linkedin = 0
    no_linkedin = 0
    for lead in leads:
        li = lead.get("payload", {}).get("person_linkedIn", "")
        if li and li.strip():
            has_linkedin += 1
        else:
            no_linkedin += 1

    print(f"  TOTAL: {len(leads)} leads | LinkedIn: {has_linkedin} | No LinkedIn: {no_linkedin}")

    all_results[camp_id] = {
        "name": camp_name,
        "leads": leads,
        "total": len(leads),
        "has_linkedin": has_linkedin,
        "no_linkedin": no_linkedin
    }

# Save all leads
with open("/sessions/eloquent-trusting-pasteur/all_leads_refetch.json", "w") as f:
    json.dump(all_results, f)

print("\n\n=== SUMMARY ===")
total_leads = 0
total_linkedin = 0
for camp_id, info in all_results.items():
    print(f"{info['name']:30s} | Total: {info['total']:4d} | LinkedIn: {info['has_linkedin']:4d} | Missing: {info['no_linkedin']:4d}")
    total_leads += info['total']
    total_linkedin += info['has_linkedin']

print(f"{'TOTAL':30s} | Total: {total_leads:4d} | LinkedIn: {total_linkedin:4d} | Missing: {total_leads - total_linkedin:4d}")
print(f"\nSaved to all_leads_refetch.json")
