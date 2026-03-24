"""
Fix username-style candidate names using LeadMagic.
- Candidates with linkedin_url → LinkedIn profile lookup → real name
- Candidates with email only → email person lookup → real name
Updates candidates table in Supabase with real first_name + last_name.
"""
import os
import time
import json
import requests
from supabase import create_client

# ── Config ────────────────────────────────────────────────────────────────────
SUPABASE_URL = os.environ["SUPABASE_URL"]
SUPABASE_KEY = os.environ["SUPABASE_SERVICE_ROLE_KEY"]
LEADMAGIC_KEY = "13e0ebd117f63815562eacbd9492fb51"
LEADMAGIC_BASE = "https://api.leadmagic.io"

# ── Init ──────────────────────────────────────────────────────────────────────
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# ── LeadMagic helpers ─────────────────────────────────────────────────────────

def leadmagic_post(endpoint: str, payload: dict) -> dict:
    try:
        resp = requests.post(
            f"{LEADMAGIC_BASE}{endpoint}",
            headers={
                "Content-Type": "application/json",
                "X-LEADMAGIC-API-KEY": LEADMAGIC_KEY,
            },
            json=payload,
            timeout=20,
        )
        if resp.status_code == 200:
            return resp.json()
        print(f"  [LeadMagic] {endpoint} → {resp.status_code}: {resp.text[:200]}")
        return {}
    except Exception as e:
        print(f"  [LeadMagic] {endpoint} error: {e}")
        return {}


def enrich_by_linkedin(linkedin_url: str) -> tuple[str, str] | None:
    """Returns (first_name, last_name) or None."""
    data = leadmagic_post("/profile-finder", {"linkedin_url": linkedin_url})
    first = (data.get("first_name") or "").strip()
    last = (data.get("last_name") or "").strip()
    if first or last:
        return first, last
    return None


def enrich_by_email(email: str) -> tuple[str, str] | None:
    """Returns (first_name, last_name) or None."""
    data = leadmagic_post("/email-finder", {"email": email})
    first = (data.get("first_name") or "").strip()
    last = (data.get("last_name") or "").strip()
    if first or last:
        return first, last
    return None

# ── Fetch bad-name candidates ─────────────────────────────────────────────────

print("Fetching username-style candidates from Supabase...")
# Fetch in batches (Supabase default limit 1000)
response = supabase.rpc("get_username_candidates").execute()

# Fallback: direct query via REST won't easily do regex — use a large fetch + filter
all_candidates = []
offset = 0
while True:
    batch = supabase.table("candidates").select("id, name, email, linkedin_url").range(offset, offset + 999).execute()
    rows = batch.data or []
    all_candidates.extend(rows)
    if len(rows) < 1000:
        break
    offset += 1000

# Filter to username-style: no space, all lowercase alphanumeric
import re
username_pattern = re.compile(r'^[a-z0-9]+$')
bad_names = [
    c for c in all_candidates
    if c.get("name") and " " not in c["name"] and username_pattern.match(c["name"])
]

print(f"Found {len(bad_names)} candidates with username-style names")

# Split by enrichment method
has_linkedin = [c for c in bad_names if c.get("linkedin_url")]
email_only   = [c for c in bad_names if not c.get("linkedin_url") and c.get("email")]
print(f"  {len(has_linkedin)} with LinkedIn URL  →  LeadMagic profile lookup")
print(f"  {len(email_only)} email-only           →  LeadMagic email lookup")

# ── Enrich ────────────────────────────────────────────────────────────────────

results = {"updated": 0, "not_found": 0, "errors": 0}
log = []

def update_candidate(cid: str, first: str, last: str, old_name: str):
    full_name = f"{first} {last}".strip()
    supabase.table("candidates").update({"name": full_name}).eq("id", cid).execute()
    print(f"  ✓ {old_name!r} → {full_name!r}")
    results["updated"] += 1
    log.append({"id": cid, "old": old_name, "new": full_name, "method": "linkedin"})


# Pass 1: LinkedIn enrichment
print(f"\n── Pass 1: LinkedIn enrichment ({len(has_linkedin)} candidates) ──")
for i, c in enumerate(has_linkedin, 1):
    print(f"[{i}/{len(has_linkedin)}] {c['name']} ({c['linkedin_url']})")
    result = enrich_by_linkedin(c["linkedin_url"])
    if result:
        first, last = result
        update_candidate(c["id"], first, last, c["name"])
        log[-1]["method"] = "linkedin"
    else:
        print(f"  ✗ not found")
        results["not_found"] += 1
        log.append({"id": c["id"], "old": c["name"], "new": None, "method": "linkedin_fail"})
    time.sleep(0.5)

# Pass 2: Email enrichment
print(f"\n── Pass 2: Email enrichment ({len(email_only)} candidates) ──")
for i, c in enumerate(email_only, 1):
    print(f"[{i}/{len(email_only)}] {c['name']} ({c['email']})")
    result = enrich_by_email(c["email"])
    if result:
        first, last = result
        update_candidate(c["id"], first, last, c["name"])
        log[-1]["method"] = "email"
    else:
        print(f"  ✗ not found")
        results["not_found"] += 1
        log.append({"id": c["id"], "old": c["name"], "new": None, "method": "email_fail"})
    time.sleep(0.5)

# ── Summary ───────────────────────────────────────────────────────────────────
print(f"\n── Done ──")
print(f"  Updated:    {results['updated']}")
print(f"  Not found:  {results['not_found']}")
print(f"  Errors:     {results['errors']}")

with open("/tmp/name_enrichment_log.json", "w") as f:
    json.dump(log, f, indent=2)
print(f"\nLog saved to /tmp/name_enrichment_log.json")
