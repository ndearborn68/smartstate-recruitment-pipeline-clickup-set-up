"""
SmartState Notification System — Heyreach Message Notifier
Polls Heyreach for new LinkedIn messages (both inbound replies and outbound
sent messages) and posts full message content to Slack.
"""
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from . import config, slack_client, state_manager
except ImportError:
    import config, slack_client, state_manager

SOURCE_KEY = "heyreach"
RATE_LIMIT_DELAY = 0.65
CONVERSATIONS_ENDPOINT = "/inbox/GetConversationsV2"


# ── Heyreach API helpers ─────────────────────────────────────────────────────

def _heyreach_headers() -> dict:
    return {
        "X-API-KEY": config.HEYREACH_API_KEY,
        "Content-Type": "application/json",
    }


def _post(path: str, payload: dict) -> dict:
    time.sleep(RATE_LIMIT_DELAY)
    try:
        resp = requests.post(
            f"{config.HEYREACH_BASE_URL}{path}",
            headers=_heyreach_headers(),
            json=payload,
            timeout=30,
        )
        if resp.status_code != 200:
            print(f"[heyreach] POST {path} → {resp.status_code}: {resp.text[:200]}")
            return {}
        return resp.json()
    except Exception as e:
        print(f"[heyreach] POST {path} error: {e}")
        return {}


# ── Core fetch logic ─────────────────────────────────────────────────────────

def fetch_conversations(campaign_id: int) -> list:
    """
    Fetch all conversations for a given Heyreach campaign ID.
    Handles pagination automatically.
    Returns list of raw conversation dicts.
    """
    conversations = []
    offset = 0
    limit = 50

    while True:
        data = _post(CONVERSATIONS_ENDPOINT, {
            "campaignId": campaign_id,
            "offset": offset,
            "limit": limit,
        })
        items = data.get("items", [])
        total = data.get("totalCount", 0)

        if not items:
            break

        conversations.extend(items)
        offset += limit

        if offset >= total:
            break

    return conversations


def extract_new_messages(conversations: list, since_dt: datetime, campaign_id: int, job_role: str) -> list:
    """
    Extract individual messages from conversations that are newer than since_dt.

    Returns list of dicts:
        lead_name, lead_linkedin_url, lead_email, campaign_id, campaign_name,
        job_role, message_text, message_at (datetime), direction ("INBOUND"/"OUTBOUND"),
        sender_name, unique_id
    """
    results = []

    for conv in conversations:
        profile = conv.get("correspondentProfile", {})
        linkedin_url = (profile.get("profileUrl") or "").strip()
        first = (profile.get("firstName") or "").strip()
        last = (profile.get("lastName") or "").strip()
        lead_name = f"{first} {last}".strip() or "Unknown"
        lead_email = (
            profile.get("emailAddress") or
            profile.get("customEmailAddress") or ""
        ).lower().strip()

        messages = conv.get("messages", [])
        if not messages:
            continue

        for msg in messages:
            created_raw = msg.get("createdAt") or ""
            if not created_raw:
                continue

            try:
                message_at = datetime.fromisoformat(created_raw.replace("Z", "+00:00"))
                if message_at.tzinfo is None:
                    message_at = message_at.replace(tzinfo=timezone.utc)
            except Exception:
                continue

            if message_at <= since_dt:
                continue

            sender = msg.get("sender", "")
            direction = "INBOUND" if sender == "CORRESPONDENT" else "OUTBOUND"
            message_text = (msg.get("body") or "").strip()

            if not message_text:
                continue

            # Build a stable unique ID from campaign + linkedin + timestamp
            unique_id = f"heyreach:{campaign_id}:{linkedin_url}:{created_raw}"

            results.append({
                "lead_name": lead_name,
                "lead_linkedin_url": linkedin_url,
                "lead_email": lead_email,
                "campaign_id": campaign_id,
                "campaign_name": job_role,
                "job_role": job_role,
                "message_text": message_text,
                "message_at": message_at,
                "direction": direction,
                "sender_name": lead_name if direction == "INBOUND" else "Recruiter",
                "unique_id": unique_id,
            })

    return results


# ── ClickUp task lookup ──────────────────────────────────────────────────────

def get_clickup_task_url(linkedin_url: str, email: str, list_id: str) -> Optional[str]:
    """Search ClickUp list for a task matching linkedin_url or email. Returns URL or None."""
    headers = {"Authorization": config.CLICKUP_API_TOKEN}
    linkedin_field_id = config.CUSTOM_FIELDS.get("LinkedIn", "")
    email_field_id = config.CUSTOM_FIELDS.get("Email", "")
    linkedin_lower = (linkedin_url or "").lower().strip()
    email_lower = (email or "").lower().strip()
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
                    val = (cf.get("value") or "").lower().strip()
                    if cf.get("id") == linkedin_field_id and linkedin_lower and val == linkedin_lower:
                        return task.get("url")
                    if cf.get("id") == email_field_id and email_lower and val == email_lower:
                        return task.get("url")
            if len(tasks) < 100:
                break
            page += 1
        except Exception as e:
            print(f"[heyreach] ClickUp lookup error: {e}")
            break

    return None


# ── Main entry point ─────────────────────────────────────────────────────────

def run() -> int:
    """
    Poll all Heyreach campaigns for new messages and post each to Slack.
    Posts both INBOUND (candidate replies) and OUTBOUND (recruiter sent) messages
    so you have full conversation visibility.
    Returns count of new notifications sent.
    """
    now = datetime.now(timezone.utc)
    since_dt = state_manager.get_last_checked(SOURCE_KEY)
    print(f"[heyreach] Checking messages since {since_dt.isoformat()}")

    sent = 0

    for campaign_id, job_role in config.HEYREACH_CAMPAIGN_TO_ROLE.items():
        print(f"[heyreach] Fetching conversations for: {job_role} (campaign {campaign_id})")

        try:
            conversations = fetch_conversations(campaign_id)
        except Exception as e:
            print(f"[heyreach] fetch_conversations failed for {campaign_id}: {e}")
            continue

        new_messages = extract_new_messages(conversations, since_dt, campaign_id, job_role)
        print(f"[heyreach] {len(new_messages)} new message(s) for {job_role}")

        for msg in new_messages:
            if state_manager.is_notified(SOURCE_KEY, msg["unique_id"]):
                continue

            # Look up ClickUp task
            list_id = config.CLICKUP_LIST_IDS.get(job_role)
            clickup_url = None
            if list_id:
                try:
                    clickup_url = get_clickup_task_url(
                        msg["lead_linkedin_url"], msg["lead_email"], list_id
                    )
                except Exception as e:
                    print(f"[heyreach] ClickUp lookup failed: {e}")

            # Format source label and message prefix
            if msg["direction"] == "INBOUND":
                source = "Heyreach (LinkedIn) — Candidate Reply"
                body_prefix = "[INBOUND REPLY]\n"
            else:
                source = "Heyreach (LinkedIn) — Sent"
                body_prefix = "[OUTBOUND MESSAGE]\n"

            full_body = body_prefix + msg["message_text"]

            blocks = slack_client.format_reply_block(
                source=source,
                candidate_name=msg["lead_name"],
                job_role=msg["job_role"],
                campaign=msg["campaign_name"],
                message_body=full_body,
                clickup_url=clickup_url,
                replied_at=msg["message_at"],
            )

            if slack_client.post_message(blocks=blocks):
                state_manager.mark_notified(SOURCE_KEY, msg["unique_id"])
                sent += 1
                direction_label = "reply" if msg["direction"] == "INBOUND" else "sent msg"
                print(f"[heyreach] Notified ({direction_label}): {msg['lead_name']} — {msg['job_role']}")

            time.sleep(RATE_LIMIT_DELAY)

    state_manager.set_last_checked(SOURCE_KEY, now)
    print(f"[heyreach] Done — {sent} notification(s) sent.")
    return sent


if __name__ == "__main__":
    count = run()
    print(f"Heyreach notifier finished — {count} notification(s) sent.")
