"""
SmartState Notification System — Instantly Reply Notifier
Polls Instantly for new email replies across all tracked campaigns
and posts full reply messages to Slack.
"""
import re
import time
import requests
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
from typing import Optional

try:
    from . import config, slack_client, state_manager
except ImportError:
    import config, slack_client, state_manager

SOURCE_KEY = "instantly"
RATE_LIMIT_DELAY = 0.65  # seconds between API calls


# ── HTML Stripper (matches pattern from sync/sync_messages.py) ───────────────

class HTMLStripper(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self._skip = False

    def handle_starttag(self, tag, attrs):
        if tag in ("br", "p", "div", "tr"):
            self.result.append("\n")
        if tag in ("style", "script"):
            self._skip = True

    def handle_endtag(self, tag):
        if tag in ("style", "script"):
            self._skip = False

    def handle_data(self, data):
        if not self._skip:
            self.result.append(data)

    def get_text(self):
        return "".join(self.result)


def strip_html(html: str) -> str:
    """Strip HTML tags and normalize whitespace."""
    if not html:
        return ""
    s = HTMLStripper()
    s.feed(html)
    text = s.get_text()
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


# ── Instantly API helpers ────────────────────────────────────────────────────

def _auth_headers() -> dict:
    return {
        "Authorization": f"Bearer {config.INSTANTLY_API_KEY}",
        "Content-Type": "application/json",
    }


def _get(path: str, params: dict = None) -> dict:
    time.sleep(RATE_LIMIT_DELAY)
    try:
        resp = requests.get(
            f"{config.INSTANTLY_BASE_URL}{path}",
            headers=_auth_headers(),
            params=params or {},
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"[instantly] GET {path} → {resp.status_code}: {resp.text[:200]}")
            return {}
        return resp.json()
    except Exception as e:
        print(f"[instantly] GET {path} error: {e}")
        return {}


def _post(path: str, payload: dict) -> dict:
    time.sleep(RATE_LIMIT_DELAY)
    try:
        resp = requests.post(
            f"{config.INSTANTLY_BASE_URL}{path}",
            headers=_auth_headers(),
            json=payload,
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"[instantly] POST {path} → {resp.status_code}: {resp.text[:200]}")
            return {}
        return resp.json()
    except Exception as e:
        print(f"[instantly] POST {path} error: {e}")
        return {}


# ── Core fetch logic ─────────────────────────────────────────────────────────

def fetch_new_replies(since_dt: datetime) -> list:
    """
    Query all tracked Instantly campaigns for leads that have replied since
    since_dt. For each matching lead, fetches the full email thread.

    Returns list of dicts:
        lead_email, lead_name, campaign_id, campaign_name, job_role,
        reply_text (full body, HTML stripped), replied_at (datetime UTC)
    """
    results = []

    for campaign_id, job_role in config.INSTANTLY_CAMPAIGN_TO_ROLE.items():
        print(f"[instantly] Checking campaign: {job_role} ({campaign_id})")
        skip = 0
        limit = 100

        while True:
            data = _post("/lead/list", {
                "campaign_id": campaign_id,
                "reply_count_filter": 1,
                "limit": limit,
                "skip": skip,
            })

            leads = data if isinstance(data, list) else data.get("data", [])
            if not leads:
                break

            for lead in leads:
                lead_email = (lead.get("email") or "").strip().lower()
                if not lead_email:
                    continue

                first = (lead.get("first_name") or "").strip()
                last = (lead.get("last_name") or "").strip()
                lead_name = f"{first} {last}".strip() or lead_email.split("@")[0]

                # Fetch full email thread
                thread_data = _get("/emails/list", {
                    "email": lead_email,
                    "campaign_id": campaign_id,
                    "limit": 50,
                })
                emails = thread_data if isinstance(thread_data, list) else thread_data.get("emails", [])
                if not emails:
                    continue

                emails_sorted = sorted(emails, key=lambda e: e.get("timestamp_email") or e.get("created_at") or "")

                # Find most recent inbound reply (ue_type 2=reply, 3=manual reply)
                last_reply = None
                for em in reversed(emails_sorted):
                    if em.get("ue_type") in (2, 3):
                        last_reply = em
                        break

                if not last_reply:
                    continue

                # Parse replied_at
                ts_raw = last_reply.get("timestamp_email") or last_reply.get("created_at") or ""
                replied_at = None
                if ts_raw:
                    try:
                        replied_at = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                        if replied_at.tzinfo is None:
                            replied_at = replied_at.replace(tzinfo=timezone.utc)
                    except Exception:
                        pass

                if replied_at is None or replied_at <= since_dt:
                    continue

                # Extract and clean body
                body_text = (last_reply.get("body") or {}).get("text") or ""
                body_html = (last_reply.get("body") or {}).get("html") or ""
                raw_body = body_text or strip_html(body_html)

                # Strip quoted history (lines starting with > or "On ... wrote:")
                clean_lines = []
                for line in raw_body.split("\n"):
                    if line.strip().startswith(">") or (line.strip().startswith("On ") and "wrote:" in line):
                        break
                    clean_lines.append(line)
                reply_text = "\n".join(clean_lines).strip()

                results.append({
                    "lead_email": lead_email,
                    "lead_name": lead_name,
                    "campaign_id": campaign_id,
                    "campaign_name": job_role,
                    "job_role": job_role,
                    "reply_text": reply_text,
                    "replied_at": replied_at,
                })

            if len(leads) < limit:
                break
            skip += limit

    print(f"[instantly] Found {len(results)} new reply(ies) since {since_dt.isoformat()}")
    return results


# ── ClickUp task lookup ──────────────────────────────────────────────────────

def get_clickup_task_url(email: str, list_id: str) -> Optional[str]:
    """Search ClickUp list for a task matching the given email. Returns task URL or None."""
    headers = {"Authorization": config.CLICKUP_API_TOKEN}
    email_field_id = config.CUSTOM_FIELDS.get("Email", "")
    email_lower = email.strip().lower()
    page = 0

    while True:
        time.sleep(RATE_LIMIT_DELAY)
        try:
            resp = requests.get(
                f"{config.CLICKUP_BASE_URL}/list/{list_id}/task",
                headers=headers,
                params={"page": page, "include_closed": "true"},
                timeout=30,
            )
            if resp.status_code != 200:
                break
            tasks = resp.json().get("tasks", [])
            if not tasks:
                break
            for task in tasks:
                for cf in task.get("custom_fields", []):
                    if cf.get("id") == email_field_id and (cf.get("value") or "").strip().lower() == email_lower:
                        return task.get("url")
            if len(tasks) < 100:
                break
            page += 1
        except Exception as e:
            print(f"[instantly] ClickUp lookup error for {email}: {e}")
            break

    return None


# ── Main entry point ─────────────────────────────────────────────────────────

def run() -> int:
    """
    Poll Instantly for new replies and post each one to Slack.
    Returns count of new notifications sent.
    """
    now = datetime.now(timezone.utc)
    since_dt = state_manager.get_last_checked(SOURCE_KEY)
    print(f"[instantly] Checking replies since {since_dt.isoformat()}")

    try:
        new_replies = fetch_new_replies(since_dt)
    except Exception as e:
        print(f"[instantly] fetch_new_replies failed: {e}")
        return 0

    sent = 0
    for reply in new_replies:
        replied_date = reply["replied_at"].strftime("%Y-%m-%d") if reply["replied_at"] else "unknown"
        unique_id = f"{reply['campaign_id']}:{reply['lead_email']}:{replied_date}"

        if state_manager.is_notified(SOURCE_KEY, unique_id):
            continue

        # Look up ClickUp task URL
        list_id = config.CLICKUP_LIST_IDS.get(reply["job_role"])
        clickup_url = None
        if list_id:
            try:
                clickup_url = get_clickup_task_url(reply["lead_email"], list_id)
            except Exception as e:
                print(f"[instantly] ClickUp lookup failed for {reply['lead_email']}: {e}")

        # Post to Slack
        blocks = slack_client.format_reply_block(
            source="Instantly (Email)",
            candidate_name=reply["lead_name"],
            job_role=reply["job_role"],
            campaign=reply["campaign_name"],
            message_body=reply["reply_text"],
            clickup_url=clickup_url,
            replied_at=reply["replied_at"],
        )
        if slack_client.post_message(blocks=blocks):
            state_manager.mark_notified(SOURCE_KEY, unique_id)
            sent += 1
            print(f"[instantly] Notified: {reply['lead_name']} <{reply['lead_email']}>")

    state_manager.set_last_checked(SOURCE_KEY, now)
    print(f"[instantly] Done — {sent} notification(s) sent.")
    return sent


if __name__ == "__main__":
    count = run()
    print(f"Instantly notifier finished — {count} notification(s) sent.")
