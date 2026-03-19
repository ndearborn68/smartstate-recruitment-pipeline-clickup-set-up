"""
SmartState — ClickUp Task Manager
Handles creating and updating candidate tasks in ClickUp.
Used by the non-responder pipeline to log LinkedIn Recruiter contacts
and update their stage when follow-up actions are taken.
"""
import time
import requests
from typing import Optional

try:
    from . import config
except ImportError:
    import config

RATE_LIMIT_DELAY = 0.5

# LinkedIn Recruiter project ID → {job_role, clickup_list_id}
LINKEDIN_PROJECT_MAP = {
    1440335625: {"job_role": "Lead HTML/Markup Developer",  "list_id": "901414414348"},
    1661750948: {"job_role": "Flutter Developer",           "list_id": "901414417498"},  # mixed → Senior Flutter
    1661933460: {"job_role": "Senior Product Manager",      "list_id": "901414414435"},
    1667430964: {"job_role": "PPC Manager",                 "list_id": "901414631002"},
    1667430612: {"job_role": "CRM Manager",                 "list_id": "901414630932"},
    1667430644: {"job_role": "Head of VIP",                 "list_id": "901414630938"},
    1166968036: {"job_role": "Skyline Software Engineer",   "list_id": None},  # no ClickUp list
    1067663436: {"job_role": "Skyline Products",            "list_id": None},  # no ClickUp list
    1377102636: {"job_role": "GSI",                         "list_id": None},  # no ClickUp list
    1524703268: {"job_role": "Agent Ins 1",                 "list_id": None},  # no ClickUp list
}


def _headers() -> dict:
    return {"Authorization": config.CLICKUP_API_TOKEN, "Content-Type": "application/json"}


def _get(path: str) -> dict:
    time.sleep(RATE_LIMIT_DELAY)
    try:
        resp = requests.get(
            f"{config.CLICKUP_BASE_URL}{path}", headers=_headers(), timeout=20
        )
        return resp.json() if resp.status_code == 200 else {}
    except Exception as e:
        print(f"[clickup] GET {path} error: {e}")
        return {}


def _post(path: str, body: dict) -> dict:
    time.sleep(RATE_LIMIT_DELAY)
    try:
        resp = requests.post(
            f"{config.CLICKUP_BASE_URL}{path}", headers=_headers(), json=body, timeout=20
        )
        return resp.json() if resp.status_code in (200, 201) else {}
    except Exception as e:
        print(f"[clickup] POST {path} error: {e}")
        return {}


def _put(path: str, body: dict) -> dict:
    time.sleep(RATE_LIMIT_DELAY)
    try:
        resp = requests.put(
            f"{config.CLICKUP_BASE_URL}{path}", headers=_headers(), json=body, timeout=20
        )
        return resp.json() if resp.status_code == 200 else {}
    except Exception as e:
        print(f"[clickup] PUT {path} error: {e}")
        return {}


# ── Task lookup ───────────────────────────────────────────────────────────────

def find_task_by_name(list_id: str, name: str) -> Optional[dict]:
    """Search a ClickUp list for a task matching the candidate name. Returns task or None."""
    page = 0
    name_lower = name.strip().lower()
    while True:
        data = _get(f"/list/{list_id}/task?page={page}&include_closed=true")
        tasks = data.get("tasks", [])
        if not tasks:
            break
        for task in tasks:
            if task.get("name", "").strip().lower() == name_lower:
                return task
        if len(tasks) < 100:
            break
        page += 1
    return None


def find_task_by_linkedin(list_id: str, linkedin_url: str) -> Optional[dict]:
    """Search a ClickUp list for a task matching the LinkedIn URL. Returns task or None."""
    if not linkedin_url:
        return None
    linkedin_field_id = config.CUSTOM_FIELDS.get("LinkedIn", "")
    linkedin_lower = linkedin_url.strip().lower()
    page = 0
    while True:
        data = _get(f"/list/{list_id}/task?page={page}&include_closed=true")
        tasks = data.get("tasks", [])
        if not tasks:
            break
        for task in tasks:
            for cf in task.get("custom_fields", []):
                if cf.get("id") == linkedin_field_id:
                    val = str(cf.get("value") or "").strip().lower()
                    if val and val == linkedin_lower:
                        return task
        if len(tasks) < 100:
            break
        page += 1
    return None


# ── Task creation ─────────────────────────────────────────────────────────────

def create_task(
    list_id: str,
    name: str,
    status: str = "outreach sent",
    linkedin_url: str = "",
    email: str = "",
    phone: str = "",
    source: str = "LinkedIn Recruiter",
    job_role: str = "",
) -> Optional[str]:
    """
    Create a ClickUp candidate task. Returns task URL or None on failure.
    Skips creation if a task with the same name already exists.
    """
    # Dedup check
    existing = None
    if linkedin_url:
        existing = find_task_by_linkedin(list_id, linkedin_url)
    if not existing:
        existing = find_task_by_name(list_id, name)

    if existing:
        print(f"[clickup] Task already exists for {name} — skipping creation")
        return existing.get("url")

    # Build custom fields
    custom_fields = []
    if linkedin_url and config.CUSTOM_FIELDS.get("LinkedIn"):
        custom_fields.append({"id": config.CUSTOM_FIELDS["LinkedIn"], "value": linkedin_url})
    if email and config.CUSTOM_FIELDS.get("Email"):
        custom_fields.append({"id": config.CUSTOM_FIELDS["Email"], "value": email})
    if phone and config.CUSTOM_FIELDS.get("Phone"):
        custom_fields.append({"id": config.CUSTOM_FIELDS["Phone"], "value": phone})
    if source and config.CUSTOM_FIELDS.get("Channel"):
        custom_fields.append({"id": config.CUSTOM_FIELDS["Channel"], "value": source})

    body = {
        "name": name,
        "status": status,
        "custom_fields": custom_fields,
    }

    result = _post(f"/list/{list_id}/task", body)
    task_url = result.get("url")
    if task_url:
        print(f"[clickup] Created task: {name} → {status} ({list_id})")
    else:
        print(f"[clickup] Failed to create task for {name}: {result}")
    return task_url


# ── Task status update ────────────────────────────────────────────────────────

def update_task_status(task_id: str, status: str) -> bool:
    """Update a task's status. Returns True on success."""
    result = _put(f"/task/{task_id}", {"status": status})
    return bool(result.get("id"))


def set_sms_sent(list_id: str, name: str, linkedin_url: str = "") -> bool:
    """
    Find a candidate's task and move it to 'sms sent' status.
    Returns True if updated successfully.
    """
    task = None
    if linkedin_url:
        task = find_task_by_linkedin(list_id, linkedin_url)
    if not task:
        task = find_task_by_name(list_id, name)

    if not task:
        print(f"[clickup] No task found for {name} to update to sms sent")
        return False

    task_id = task.get("id")
    success = update_task_status(task_id, "sms sent")
    if success:
        print(f"[clickup] {name} → sms sent")
    return success


# ── Custom field update ───────────────────────────────────────────────────────

def set_custom_field(task_id: str, field_name: str, value) -> bool:
    """Set a custom field value on a task."""
    field_id = config.CUSTOM_FIELDS.get(field_name)
    if not field_id:
        return False
    try:
        time.sleep(RATE_LIMIT_DELAY)
        resp = requests.post(
            f"{config.CLICKUP_BASE_URL}/task/{task_id}/field/{field_id}",
            headers=_headers(),
            json={"value": value},
            timeout=20,
        )
        return resp.status_code in (200, 201)
    except Exception as e:
        print(f"[clickup] set_custom_field error: {e}")
        return False
