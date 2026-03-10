import os
import json, subprocess, time, sys
from concurrent.futures import ThreadPoolExecutor, as_completed

CLICKUP_TOKEN = os.environ.get("CLICKUP_API_TOKEN", "YOUR_CLICKUP_TOKEN")

CAMPAIGN_TO_LIST = {
    '8b6cb40c-0cb1-41d1-97d1-286b04a01391': '901414417498',
    '6284a72c-7927-41fe-b7ec-2e1df22e1903': '901414414372',
    '3cc1f7ae-c1df-4f29-afb1-ff5ff1143780': '901414414435',
}

CAMPAIGN_NAMES = {
    '8b6cb40c-0cb1-41d1-97d1-286b04a01391': 'Senior Flutter',
    '6284a72c-7927-41fe-b7ec-2e1df22e1903': 'Middle Flutter Developer',
    '3cc1f7ae-c1df-4f29-afb1-ff5ff1143780': 'Product Owner',
}

FIELD_IDS = {
    'email': '43b5c0f0-5de1-486c-9a5d-4c3c34afd97d',
    'linkedin': 'cdc5ce8e-daa9-4279-9f8b-63f325085f62',
    'channel': 'c161752a-3a35-467d-bef6-ab76c245cceb',
    'campaign_sequence': '549a80b8-22cf-4eba-9df0-d3ce52ad4bd8',
    'date_contacted': '23315184-23b5-44b7-b25e-a04ddc6ed9c0',
}

CHANNEL_INSTANTLY_ID = 'f88806c4-396c-4890-a7ff-f93bac1ea00f'

def create_task(list_id, lead):
    first = lead.get('first_name', '') or ''
    last = lead.get('last_name', '') or ''
    name = f"{first} {last}".strip()
    if not name:
        name = lead.get('email', 'Unknown').split('@')[0]
    
    email = lead.get('email', '')
    linkedin = lead.get('payload', {}).get('person_linkedIn', '')
    campaign_name = CAMPAIGN_NAMES.get(lead['campaign'], '')
    replied = lead.get('email_reply_count', 0) > 0
    status = 'replied' if replied else 'outreach sent'
    
    date_contacted_str = lead.get('timestamp_last_contact', lead.get('timestamp_created', ''))
    date_contacted_ms = None
    if date_contacted_str:
        try:
            from datetime import datetime
            dt = datetime.fromisoformat(date_contacted_str.replace('Z', '+00:00'))
            date_contacted_ms = int(dt.timestamp() * 1000)
        except:
            pass
    
    custom_fields = [
        {"id": FIELD_IDS['email'], "value": email},
        {"id": FIELD_IDS['channel'], "value": CHANNEL_INSTANTLY_ID},
        {"id": FIELD_IDS['campaign_sequence'], "value": campaign_name},
    ]
    
    if linkedin:
        custom_fields.append({"id": FIELD_IDS['linkedin'], "value": linkedin})
    if date_contacted_ms:
        custom_fields.append({"id": FIELD_IDS['date_contacted'], "value": date_contacted_ms})
    
    payload = json.dumps({"name": name, "status": status, "custom_fields": custom_fields})
    
    result = subprocess.run([
        'curl', '-s', '-X', 'POST',
        f'https://api.clickup.com/api/v2/list/{list_id}/task',
        '-H', f'Authorization: {CLICKUP_TOKEN}',
        '-H', 'Content-Type: application/json',
        '-d', payload
    ], capture_output=True, text=True, timeout=30)
    
    try:
        resp = json.loads(result.stdout)
        return 'id' in resp, resp.get('id', resp.get('err', ''))
    except:
        return False, result.stdout[:100]

with open('/sessions/eloquent-trusting-pasteur/instantly_leads.json') as f:
    all_leads = json.load(f)

smartstate_leads = [l for l in all_leads if l['campaign'] in CAMPAIGN_TO_LIST]
print(f"Total: {len(smartstate_leads)} leads", flush=True)

by_campaign = {}
for lead in smartstate_leads:
    by_campaign.setdefault(lead['campaign'], []).append(lead)

total_success = 0
total_failed = 0

for camp_id, leads in by_campaign.items():
    list_id = CAMPAIGN_TO_LIST[camp_id]
    camp_name = CAMPAIGN_NAMES[camp_id]
    print(f"\n{camp_name}: {len(leads)} leads -> List {list_id}", flush=True)
    
    success = 0
    failed = 0
    batch_count = 0
    
    for i, lead in enumerate(leads):
        ok, res = create_task(list_id, lead)
        if ok:
            success += 1
        else:
            failed += 1
            if failed <= 2:
                print(f"  ERR: {res}", flush=True)
        
        batch_count += 1
        
        if (i + 1) % 50 == 0:
            print(f"  {i+1}/{len(leads)} done ({success} ok, {failed} fail)", flush=True)
        
        # ClickUp rate limit: 100/min for Business plan
        if batch_count >= 95:
            print(f"  Rate limit pause...", flush=True)
            time.sleep(62)
            batch_count = 0
        else:
            time.sleep(0.65)
    
    total_success += success
    total_failed += failed
    print(f"  Complete: {success} created, {failed} failed", flush=True)

print(f"\n=== DONE: {total_success} created, {total_failed} failed ===", flush=True)
