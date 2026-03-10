import os
import requests, time

API_KEY = os.environ.get("INSTANTLY_API_KEY", "YOUR_INSTANTLY_KEY")
HEADERS = {"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"}

CAMPAIGNS = {
    "ff1fb3e5-4af1-433d-8a7f-d396eba5f0dd": "Senior HTML",
    "f241305e-57d5-4812-a278-2fcf68b65f9e": "Mid HTML",
    "d0da5edd-293e-4b21-8e35-ce504377362a": "Senior Front End",
    "b6a30d37-091e-4ab3-ae7b-6e0674c7d764": "Manual QA Postman",
    "0ccefc2b-fa4d-4615-b180-4d17cf27960f": "Senior Back End",
    "05f6e117-9187-421f-ad45-951300d2822f": "Affiliate Manager",
}

for camp_id, name in CAMPAIGNS.items():
    # Count all leads for this campaign by paginating
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
        data = resp.json()
        items = data.get("items", [])
        if not items:
            break
        # Only count leads that match this campaign
        matching = [i for i in items if i.get("campaign") == camp_id]
        leads.extend(matching)
        starting_after = data.get("next_starting_after")
        if not starting_after:
            break
        # If none matched in this page, the API isn't filtering - break to avoid infinite loop
        if len(matching) == 0 and len(items) > 0:
            # Check a few more pages
            pass
        time.sleep(0.2)
        # Safety: stop after fetching too many
        if len(leads) > 10000:
            break

    replied = sum(1 for l in leads if l.get("email_reply_count", 0) > 0)
    has_li = sum(1 for l in leads if l.get("payload", {}).get("person_linkedIn", "") or l.get("payload", {}).get("LinkedIn_personURL", ""))
    print(f"{name:20s} | Leads: {len(leads):5d} | Replied: {replied:4d} | Has LinkedIn: {has_li:4d}")
