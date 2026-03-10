#!/usr/bin/env python3
"""
SmartState ClickUp Manager — Phase 2: Claude as ClickUp Interface
Provides: create, update, search, dedup, query operations on candidate tasks.
"""

import os
import requests
import json
import sys
import time
from datetime import datetime, timezone

# ── Configuration ──────────────────────────────────────────
CLICKUP_API_TOKEN = os.environ.get("CLICKUP_API_TOKEN", "YOUR_TOKEN_HERE")
CLICKUP_BASE = "https://api.clickup.com/api/v2"
HEADERS = {
    "Authorization": CLICKUP_API_TOKEN,
    "Content-Type": "application/json"
}

# ClickUp List IDs (Candidates lists)
LISTS = {
    "Lead HTML/Markup Developer":   "901414414348",
    "Mid-Level Flutter Developer":  "901414414372",
    "Sr Front End Developer":       "901414414393",
    "Senior Backend Developer":     "901414414404",
    "Senior Manual QA Engineer":    "901414414415",
    "Senior Product Manager":       "901414414435",
    "Affiliate Manager":            "901414417420",
    "Senior Flutter Developer":     "901414417498",
}

# Aliases for flexible matching
LIST_ALIASES = {
    "html": "Lead HTML/Markup Developer",
    "markup": "Lead HTML/Markup Developer",
    "html developer": "Lead HTML/Markup Developer",
    "lead html": "Lead HTML/Markup Developer",
    "mid flutter": "Mid-Level Flutter Developer",
    "middle flutter": "Mid-Level Flutter Developer",
    "mid-level flutter": "Mid-Level Flutter Developer",
    "flutter mid": "Mid-Level Flutter Developer",
    "front end": "Sr Front End Developer",
    "frontend": "Sr Front End Developer",
    "sr front end": "Sr Front End Developer",
    "senior front end": "Sr Front End Developer",
    "backend": "Senior Backend Developer",
    "back end": "Senior Backend Developer",
    "senior backend": "Senior Backend Developer",
    "qa": "Senior Manual QA Engineer",
    "manual qa": "Senior Manual QA Engineer",
    "qe": "Senior Manual QA Engineer",
    "product manager": "Senior Product Manager",
    "pm": "Senior Product Manager",
    "product owner": "Senior Product Manager",
    "affiliate": "Affiliate Manager",
    "affiliate manager": "Affiliate Manager",
    "senior flutter": "Senior Flutter Developer",
    "sr flutter": "Senior Flutter Developer",
    "flutter senior": "Senior Flutter Developer",
}

# Custom Field IDs
FIELDS = {
    "date_contacted":    "23315184-23b5-44b7-b25e-a04ddc6ed9c0",
    "email":             "43b5c0f0-5de1-486c-9a5d-4c3c34afd97d",
    "campaign":          "549a80b8-22cf-4eba-9df0-d3ce52ad4bd8",
    "notes":             "5dc608ba-565f-41e0-8063-ca5c8681ed88",
    "interview_date":    "64ff798a-7af8-4bdf-b3b4-d762481f7da9",
    "date_replied":      "8638fc92-086c-455a-8a72-dfc750df7233",
    "phone":             "a340a4f0-23ae-4678-a722-604d4c81f0ff",
    "rating":            "abc69253-4279-4e50-a9a1-75f82cc49a79",
    "channel":           "c161752a-3a35-467d-bef6-ab76c245cceb",
    "salary":            "c83313f2-2620-4894-9a3b-2ebc0b0754bf",
    "linkedin":          "cdc5ce8e-daa9-4279-9f8b-63f325085f62",
}

# Channel dropdown option IDs
CHANNELS = {
    "instantly":          "f88806c4-396c-4890-a7ff-f93bac1ea00f",
    "heyreach":           "b47a6098-b305-4dad-a20e-f16cb4fdbafb",
    "linkedin recruiter": "38839ea6-f705-4fc6-abe0-e18311be12ae",
    "li recruiter":       "38839ea6-f705-4fc6-abe0-e18311be12ae",
    "linkedin":           "38839ea6-f705-4fc6-abe0-e18311be12ae",
    "inbound":            "00659e3a-4af7-4f14-9fef-06fb27079860",
}

# Valid statuses
STATUSES = [
    "outreach sent", "replied", "screening", "interviewed",
    "submitted to client", "client review", "hired", "complete"
]

RATE_LIMIT_DELAY = 0.7  # seconds between API calls to stay under 100/min


def resolve_list(job_input):
    """Resolve a flexible job name input to the canonical list name."""
    job_lower = job_input.strip().lower()
    # Direct match
    for name in LISTS:
        if name.lower() == job_lower:
            return name
    # Alias match
    if job_lower in LIST_ALIASES:
        return LIST_ALIASES[job_lower]
    # Partial match
    for name in LISTS:
        if job_lower in name.lower() or name.lower() in job_lower:
            return name
    return None


def api_get(endpoint, params=None):
    """GET request to ClickUp API with rate limiting."""
    time.sleep(RATE_LIMIT_DELAY)
    r = requests.get(f"{CLICKUP_BASE}{endpoint}", headers=HEADERS, params=params)
    r.raise_for_status()
    return r.json()


def api_post(endpoint, data):
    """POST request to ClickUp API with rate limiting."""
    time.sleep(RATE_LIMIT_DELAY)
    r = requests.post(f"{CLICKUP_BASE}{endpoint}", headers=HEADERS, json=data)
    r.raise_for_status()
    return r.json()


def api_put(endpoint, data):
    """PUT request to ClickUp API with rate limiting."""
    time.sleep(RATE_LIMIT_DELAY)
    r = requests.put(f"{CLICKUP_BASE}{endpoint}", headers=HEADERS, json=data)
    r.raise_for_status()
    return r.json()


# ── CREATE ──────────────────────────────────────────────────
def create_candidate(job, name, email=None, linkedin=None, phone=None,
                     channel=None, campaign=None, status="outreach sent",
                     notes=None, salary=None, rating=None):
    """Create a new candidate task in the specified job's Candidates list."""
    list_name = resolve_list(job)
    if not list_name:
        return {"error": f"Could not resolve job '{job}'. Available: {list(LISTS.keys())}"}

    list_id = LISTS[list_name]

    # Build custom fields
    custom_fields = []

    if email:
        custom_fields.append({"id": FIELDS["email"], "value": email})
    if linkedin:
        custom_fields.append({"id": FIELDS["linkedin"], "value": linkedin})
    if phone:
        custom_fields.append({"id": FIELDS["phone"], "value": phone})
    if campaign:
        custom_fields.append({"id": FIELDS["campaign"], "value": campaign})
    if notes:
        custom_fields.append({"id": FIELDS["notes"], "value": notes})
    if salary:
        custom_fields.append({"id": FIELDS["salary"], "value": str(salary)})
    if rating:
        custom_fields.append({"id": FIELDS["rating"], "value": min(int(rating), 3)})

    # Channel
    if channel:
        ch_lower = channel.strip().lower()
        if ch_lower in CHANNELS:
            custom_fields.append({
                "id": FIELDS["channel"],
                "value": CHANNELS[ch_lower]
            })

    # Date Contacted = now
    now_ms = int(datetime.now(timezone.utc).timestamp() * 1000)
    custom_fields.append({"id": FIELDS["date_contacted"], "value": now_ms})

    payload = {
        "name": name.strip(),
        "status": status,
        "custom_fields": custom_fields
    }

    result = api_post(f"/list/{list_id}/task", payload)
    return {
        "success": True,
        "task_id": result["id"],
        "task_name": result["name"],
        "list": list_name,
        "status": result["status"]["status"],
        "url": result["url"]
    }


# ── SEARCH ──────────────────────────────────────────────────
def search_tasks(list_id, page=0):
    """Get all tasks from a list (paginated, 100 per page)."""
    params = {
        "page": page,
        "subtasks": "true",
        "include_closed": "true"
    }
    return api_get(f"/list/{list_id}/task", params)


def find_candidate(name=None, email=None, linkedin=None, job=None):
    """
    Find a candidate across lists. Search by name, email, or LinkedIn URL.
    If job is specified, only search that list. Otherwise search all lists.
    """
    lists_to_search = {}
    if job:
        list_name = resolve_list(job)
        if list_name:
            lists_to_search[list_name] = LISTS[list_name]
        else:
            return {"error": f"Could not resolve job '{job}'"}
    else:
        lists_to_search = LISTS

    matches = []
    for list_name, list_id in lists_to_search.items():
        page = 0
        while True:
            data = search_tasks(list_id, page)
            tasks = data.get("tasks", [])
            if not tasks:
                break

            for task in tasks:
                match_type = None
                # Name match
                if name and name.strip().lower() in task["name"].lower():
                    match_type = "name"
                # Check custom fields for email/linkedin
                for cf in task.get("custom_fields", []):
                    if email and cf["id"] == FIELDS["email"]:
                        val = cf.get("value") or ""
                        if val.lower() == email.strip().lower():
                            match_type = "email"
                    if linkedin and cf["id"] == FIELDS["linkedin"]:
                        val = cf.get("value") or ""
                        if linkedin.strip().lower().rstrip("/") in val.lower().rstrip("/"):
                            match_type = "linkedin"

                if match_type:
                    # Extract key fields
                    task_info = extract_task_info(task, list_name)
                    task_info["match_type"] = match_type
                    matches.append(task_info)

            if len(tasks) < 100:
                break
            page += 1

    return {"count": len(matches), "matches": matches}


def extract_task_info(task, list_name=None):
    """Extract useful info from a raw task object."""
    info = {
        "task_id": task["id"],
        "name": task["name"],
        "status": task["status"]["status"],
        "list": list_name or "",
        "url": task["url"],
    }
    for cf in task.get("custom_fields", []):
        if cf["id"] == FIELDS["email"]:
            info["email"] = cf.get("value") or ""
        elif cf["id"] == FIELDS["linkedin"]:
            info["linkedin"] = cf.get("value") or ""
        elif cf["id"] == FIELDS["channel"]:
            # Resolve channel option back to name
            type_config = cf.get("type_config", {})
            options = type_config.get("options", [])
            selected = cf.get("value")
            if isinstance(selected, int) and selected < len(options):
                info["channel"] = options[selected].get("name", "")
            elif isinstance(selected, str):
                for opt in options:
                    if opt.get("id") == selected:
                        info["channel"] = opt.get("name", "")
                        break
        elif cf["id"] == FIELDS["campaign"]:
            info["campaign"] = cf.get("value") or ""
        elif cf["id"] == FIELDS["phone"]:
            info["phone"] = cf.get("value") or ""
        elif cf["id"] == FIELDS["rating"]:
            info["rating"] = cf.get("value")
        elif cf["id"] == FIELDS["salary"]:
            info["salary"] = cf.get("value")
        elif cf["id"] == FIELDS["notes"]:
            val = cf.get("value") or ""
            info["notes_preview"] = val[:200] + "..." if len(val) > 200 else val
        elif cf["id"] == FIELDS["date_contacted"]:
            val = cf.get("value")
            if val:
                info["date_contacted"] = datetime.fromtimestamp(int(val)/1000).strftime("%Y-%m-%d")
        elif cf["id"] == FIELDS["date_replied"]:
            val = cf.get("value")
            if val:
                info["date_replied"] = datetime.fromtimestamp(int(val)/1000).strftime("%Y-%m-%d")
    return info


# ── UPDATE ──────────────────────────────────────────────────
def update_candidate(task_id, status=None, email=None, linkedin=None,
                     phone=None, channel=None, campaign=None, notes=None,
                     salary=None, rating=None, date_replied=None,
                     interview_date=None, name=None):
    """Update fields on an existing candidate task."""
    # Update task-level fields (name, status)
    task_update = {}
    if name:
        task_update["name"] = name.strip()
    if status:
        status_lower = status.strip().lower()
        if status_lower in STATUSES:
            task_update["status"] = status_lower
        else:
            return {"error": f"Invalid status '{status}'. Valid: {STATUSES}"}

    if task_update:
        api_put(f"/task/{task_id}", task_update)

    # Update custom fields
    field_updates = []
    if email:
        field_updates.append(("email", email))
    if linkedin:
        field_updates.append(("linkedin", linkedin))
    if phone:
        field_updates.append(("phone", phone))
    if campaign:
        field_updates.append(("campaign", campaign))
    if notes:
        field_updates.append(("notes", notes))
    if salary:
        field_updates.append(("salary", str(salary)))
    if rating:
        r_val = min(int(rating), 3)  # emoji rating, max 3
        field_updates.append(("rating", r_val))
    if channel:
        ch_lower = channel.strip().lower()
        if ch_lower in CHANNELS:
            field_updates.append(("channel", CHANNELS[ch_lower]))
    if date_replied:
        if isinstance(date_replied, str):
            dt = datetime.strptime(date_replied, "%Y-%m-%d")
            date_replied = int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
        field_updates.append(("date_replied", date_replied))
    if interview_date:
        if isinstance(interview_date, str):
            dt = datetime.strptime(interview_date, "%Y-%m-%d")
            interview_date = int(dt.replace(tzinfo=timezone.utc).timestamp() * 1000)
        field_updates.append(("interview_date", interview_date))

    for field_key, value in field_updates:
        field_id = FIELDS[field_key]
        time.sleep(RATE_LIMIT_DELAY)
        r = requests.post(
            f"{CLICKUP_BASE}/task/{task_id}/field/{field_id}",
            headers=HEADERS,
            json={"value": value}
        )
        r.raise_for_status()

    return {"success": True, "task_id": task_id, "updates_applied": len(field_updates) + len(task_update)}


# ── ADD COMMENT ─────────────────────────────────────────────
def add_comment(task_id, comment_text):
    """Add a comment to a candidate task (for activity log)."""
    payload = {"comment_text": comment_text}
    result = api_post(f"/task/{task_id}/comment", payload)
    return {"success": True, "comment_id": result.get("id")}


# ── DEDUP CHECK ─────────────────────────────────────────────
def dedup_check(emails=None, linkedins=None, names=None):
    """
    Check if candidates already exist across all lists.
    Pass lists of emails, LinkedIn URLs, or names.
    Returns: dict of {identifier: match_info or "clear"}
    """
    results = {}
    search_items = []
    if emails:
        for e in emails:
            search_items.append(("email", e))
    if linkedins:
        for l in linkedins:
            search_items.append(("linkedin", l))
    if names:
        for n in names:
            search_items.append(("name", n))

    # Load all tasks once
    all_tasks = {}
    for list_name, list_id in LISTS.items():
        page = 0
        while True:
            data = search_tasks(list_id, page)
            tasks = data.get("tasks", [])
            if not tasks:
                break
            for task in tasks:
                info = extract_task_info(task, list_name)
                key = task["id"]
                all_tasks[key] = info
            if len(tasks) < 100:
                break
            page += 1

    # Check each search item
    for search_type, search_val in search_items:
        search_lower = search_val.strip().lower().rstrip("/")
        found = None
        for tid, info in all_tasks.items():
            if search_type == "email" and info.get("email", "").lower() == search_lower:
                found = info
                break
            elif search_type == "linkedin" and search_lower in info.get("linkedin", "").lower().rstrip("/"):
                found = info
                break
            elif search_type == "name" and search_lower in info.get("name", "").lower():
                found = info
                break
        results[search_val] = found if found else "clear"

    return results


# ── QUERY ───────────────────────────────────────────────────
def query_candidates(job=None, status=None, channel=None, limit=50):
    """
    Query candidates with optional filters.
    Returns matching candidates with key info.
    """
    lists_to_search = {}
    if job:
        list_name = resolve_list(job)
        if list_name:
            lists_to_search[list_name] = LISTS[list_name]
        else:
            return {"error": f"Could not resolve job '{job}'"}
    else:
        lists_to_search = LISTS

    results = []
    for list_name, list_id in lists_to_search.items():
        page = 0
        while True:
            params = {"page": page, "subtasks": "true", "include_closed": "true"}
            if status:
                params["statuses[]"] = status.strip().lower()
            data = api_get(f"/list/{list_id}/task", params)
            tasks = data.get("tasks", [])
            if not tasks:
                break

            for task in tasks:
                info = extract_task_info(task, list_name)
                # Channel filter (post-query since ClickUp API doesn't filter by custom field)
                if channel:
                    ch_lower = channel.strip().lower()
                    task_channel = info.get("channel", "").lower()
                    if ch_lower not in task_channel:
                        continue
                results.append(info)
                if len(results) >= limit:
                    break

            if len(results) >= limit or len(tasks) < 100:
                break
            page += 1

        if len(results) >= limit:
            break

    return {"count": len(results), "candidates": results}


# ── PIPELINE SUMMARY ────────────────────────────────────────
def pipeline_summary(job=None):
    """Get a count of candidates per status, optionally filtered by job."""
    lists_to_search = {}
    if job:
        list_name = resolve_list(job)
        if list_name:
            lists_to_search[list_name] = LISTS[list_name]
        else:
            return {"error": f"Could not resolve job '{job}'"}
    else:
        lists_to_search = LISTS

    summary = {s: 0 for s in STATUSES}
    summary["total"] = 0
    by_list = {}

    for list_name, list_id in lists_to_search.items():
        list_counts = {s: 0 for s in STATUSES}
        page = 0
        while True:
            data = search_tasks(list_id, page)
            tasks = data.get("tasks", [])
            if not tasks:
                break
            for task in tasks:
                st = task["status"]["status"].lower()
                summary[st] = summary.get(st, 0) + 1
                summary["total"] += 1
                list_counts[st] = list_counts.get(st, 0) + 1
            if len(tasks) < 100:
                break
            page += 1
        list_counts["total"] = sum(v for k, v in list_counts.items() if k != "total")
        by_list[list_name] = list_counts

    return {"overall": summary, "by_job": by_list}


# ── CLI INTERFACE ───────────────────────────────────────────
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python clickup_manager.py <command> [args...]")
        print("Commands: create, find, update, dedup, query, summary, comment")
        sys.exit(1)

    cmd = sys.argv[1].lower()

    if cmd == "test":
        # Quick connectivity test
        print("Testing ClickUp API connection...")
        try:
            data = api_get(f"/list/{LISTS['Senior Product Manager']}/task", {"page": 0})
            tasks = data.get("tasks", [])
            print(f"✓ Connected. Senior Product Manager has {len(tasks)} tasks (page 0)")
            if tasks:
                print(f"  First task: {tasks[0]['name']} — status: {tasks[0]['status']['status']}")
        except Exception as e:
            print(f"✗ Error: {e}")

    elif cmd == "summary":
        job = sys.argv[2] if len(sys.argv) > 2 else None
        result = pipeline_summary(job)
        print(json.dumps(result, indent=2))

    else:
        print(f"Unknown command: {cmd}")
        print("Commands: create, find, update, dedup, query, summary, comment, test")
