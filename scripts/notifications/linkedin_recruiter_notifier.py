"""
SmartState Notification System — LinkedIn Recruiter InMail Notifier
Polls Gmail for LinkedIn InMail reply notification emails (from hit-reply@linkedin.com)
and posts each reply to Slack #smartstate-responses.

Handles two email formats:
  - LinkedIn Recruiter:     subject "Message replied: ..."
  - LinkedIn Sales Navigator: subject "Message replied from ..."
  - Message accepted:       subject "Message accepted: ..."

Reply text is extracted from the email body. Emails with no reply text are skipped.
"""
import json
import os
import re
import time
import requests
from datetime import datetime, timezone
from typing import Optional

try:
    from . import config, slack_client, state_manager
except ImportError:
    import config, slack_client, state_manager

SOURCE_KEY = "linkedin_recruiter"

GMAIL_CREDENTIALS_FILE = os.path.expanduser("~/.gmail-mcp/credentials.json")
GMAIL_OAUTH_KEYS_FILE  = os.path.expanduser("~/.gmail-mcp/gcp-oauth.keys.json")
GMAIL_TOKEN_URI        = "https://oauth2.googleapis.com/token"
GMAIL_API_BASE         = "https://gmail.googleapis.com/gmail/v1/users/me"


# ---------------------------------------------------------------------------
# Gmail OAuth helpers
# ---------------------------------------------------------------------------

def _load_credentials() -> dict:
    with open(GMAIL_CREDENTIALS_FILE) as f:
        return json.load(f)


def _save_credentials(creds: dict) -> None:
    with open(GMAIL_CREDENTIALS_FILE, "w") as f:
        json.dump(creds, f, indent=2)


def _get_access_token() -> Optional[str]:
    """
    Return a valid access token, refreshing if expired.
    Uses the OAuth client id/secret from gcp-oauth.keys.json and
    the stored refresh token from credentials.json.
    """
    try:
        creds = _load_credentials()
        keys  = json.load(open(GMAIL_OAUTH_KEYS_FILE))["installed"]

        # Check if current access token is still valid (with 60s buffer)
        expiry_ms = creds.get("expiry_date", 0)
        now_ms = int(time.time() * 1000)
        if expiry_ms - now_ms > 60_000 and creds.get("access_token"):
            return creds["access_token"]

        # Refresh
        resp = requests.post(
            GMAIL_TOKEN_URI,
            data={
                "client_id":     keys["client_id"],
                "client_secret": keys["client_secret"],
                "refresh_token": creds["refresh_token"],
                "grant_type":    "refresh_token",
            },
            timeout=15,
        )
        if resp.status_code != 200:
            print(f"[linkedin] ERROR: token refresh failed: {resp.status_code} {resp.text[:200]}")
            return None

        token_data = resp.json()
        creds["access_token"] = token_data["access_token"]
        creds["expiry_date"]  = now_ms + int(token_data.get("expires_in", 3600)) * 1000
        _save_credentials(creds)
        return creds["access_token"]

    except Exception as exc:
        print(f"[linkedin] ERROR getting access token: {exc}")
        return None


def _gmail_get(path: str, params: dict = None, token: str = None) -> dict:
    """GET against Gmail API. Returns parsed JSON or {}."""
    try:
        resp = requests.get(
            f"{GMAIL_API_BASE}{path}",
            headers={"Authorization": f"Bearer {token}"},
            params=params or {},
            timeout=20,
        )
        if resp.status_code != 200:
            print(f"[linkedin] Gmail GET {path} → {resp.status_code}: {resp.text[:200]}")
            return {}
        return resp.json()
    except Exception as exc:
        print(f"[linkedin] Gmail GET {path} error: {exc}")
        return {}


# ---------------------------------------------------------------------------
# Email search + parsing
# ---------------------------------------------------------------------------

def search_inmail_emails(token: str, since_dt: datetime) -> list:
    """
    Search Gmail for LinkedIn InMail reply notifications since since_dt.
    Returns list of message stubs [{"id": ..., "threadId": ...}].
    """
    # Gmail date filter is day-level only; we filter by exact timestamp later
    since_date = since_dt.strftime("%Y/%m/%d")
    query = f"from:hit-reply@linkedin.com after:{since_date}"

    data = _gmail_get("/messages", {"q": query, "maxResults": 100}, token=token)
    return data.get("messages", [])


def fetch_email(message_id: str, token: str) -> dict:
    """Fetch full email by message ID. Returns parsed message dict."""
    return _gmail_get(f"/messages/{message_id}", {"format": "full"}, token=token)


def _decode_body(msg: dict) -> str:
    """Extract plain-text body from Gmail message payload."""
    import base64

    def _extract(payload):
        mime = payload.get("mimeType", "")
        if mime == "text/plain":
            data = payload.get("body", {}).get("data", "")
            if data:
                return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace")
        for part in payload.get("parts", []):
            result = _extract(part)
            if result:
                return result
        return ""

    return _extract(msg.get("payload", {}))


def _header(msg: dict, name: str) -> str:
    """Get a header value from a Gmail message."""
    for h in msg.get("payload", {}).get("headers", []):
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def parse_inmail_reply(msg: dict) -> Optional[dict]:
    """
    Parse a LinkedIn InMail reply email into a structured dict.
    Returns None if this email has no reply text (e.g., acceptance-only ping).

    Returns:
        candidate_name  - from the From: display name
        reply_text      - the candidate's message
        subject         - InMail subject line
        linkedin_url    - deep link back to the conversation
        received_at     - datetime (UTC)
        message_id      - Gmail message ID (used for dedup)
    """
    message_id = msg.get("id", "")
    subject    = _header(msg, "subject")
    from_raw   = _header(msg, "from")
    date_raw   = _header(msg, "date")

    # Extract candidate name from "Display Name <hit-reply@linkedin.com>"
    name_match = re.match(r'^"?([^"<]+)"?\s*<', from_raw)
    candidate_name = name_match.group(1).strip() if name_match else from_raw.split("<")[0].strip()

    # Parse received_at
    received_at = None
    try:
        from email.utils import parsedate_to_datetime
        received_at = parsedate_to_datetime(date_raw).astimezone(timezone.utc)
    except Exception:
        received_at = datetime.now(timezone.utc)

    body = _decode_body(msg)
    if not body:
        return None

    reply_text = None
    linkedin_url = None

    # --- Format 1: LinkedIn Recruiter (eml-email_hire_inmail_reply_01) ---
    # Body structure:
    #   [subject line]
    #   InMail: You have a new message
    #   [candidate name]
    #   Reply
    #   https://www.linkedin.com/talent/inbox/...
    #   [reply text]
    #   -----
    #   This email was intended for...
    if "InMail: You have a new message" in body or "talent/inbox" in body:
        # Extract LinkedIn URL
        url_match = re.search(r'(https://www\.linkedin\.com/talent/inbox/[^\s\n]+)', body)
        if url_match:
            linkedin_url = url_match.group(1)

        # Reply text is between the URL (or "Reply\n") and the dashes separator
        # Try to find text after the URL line
        after_url = ""
        if url_match:
            after_url = body[url_match.end():].strip()
        elif "Reply\n" in body:
            after_url = body.split("Reply\n", 1)[-1].strip()

        # Strip everything from the dashes line onward
        if after_url:
            reply_text = re.split(r'\n\s*-{20,}', after_url)[0].strip()

    # --- Format 2: LinkedIn Sales Navigator (eml-email_lss_inmail_reply_01) ---
    elif "sales/inbox" in body or "You have a new InMail message" in body:
        url_match = re.search(r'(https://www\.linkedin\.com/sales/inbox/[^\s\n]+)', body)
        if url_match:
            linkedin_url = url_match.group(1)

        # Text is right after "You have a new InMail message.\n\n"
        if "You have a new InMail message." in body:
            after_header = body.split("You have a new InMail message.", 1)[-1].strip()
            # Stop at "View in Sales Navigator" or dashes
            reply_text = re.split(r'\nView in Sales Navigator|\n\s*-{20,}', after_header)[0].strip()

    # --- Format 3: Generic / other LinkedIn reply format ---
    else:
        # Fallback: grab everything before the dashes separator
        parts = re.split(r'\n\s*-{20,}', body)
        candidate_text = parts[0].strip() if parts else ""
        # Remove "This email was intended" footer if somehow in part 0
        candidate_text = candidate_text.split("This email was intended")[0].strip()
        # Remove lines that are just the subject or "LinkedIn" header
        lines = [l for l in candidate_text.splitlines()
                 if l.strip() and l.strip() not in ("LinkedIn", subject, "InMail: You have a new message")]
        reply_text = "\n".join(lines).strip() if lines else None

    # Skip if no actual reply text
    if not reply_text or len(reply_text.strip()) < 3:
        return None

    # Skip if reply_text is just a URL
    if reply_text.strip().startswith("http"):
        return None

    return {
        "candidate_name": candidate_name,
        "reply_text":     reply_text.strip(),
        "subject":        subject,
        "linkedin_url":   linkedin_url,
        "received_at":    received_at,
        "message_id":     message_id,
    }


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run() -> int:
    """
    Poll Gmail for new LinkedIn InMail reply notifications and post each to Slack.
    Returns count of new notifications sent.
    """
    since_dt = state_manager.get_last_checked(SOURCE_KEY)
    now = datetime.now(timezone.utc)
    print(f"[linkedin] Checking InMail replies since {since_dt.isoformat()}")

    token = _get_access_token()
    if not token:
        print("[linkedin] ERROR: could not get Gmail access token")
        return 0

    stubs = search_inmail_emails(token, since_dt)
    print(f"[linkedin] Found {len(stubs)} LinkedIn email(s) to check")

    sent = 0
    for stub in stubs:
        msg_id = stub.get("id", "")
        unique_id = f"linkedin:{msg_id}"

        if state_manager.is_notified(SOURCE_KEY, unique_id):
            continue

        msg = fetch_email(msg_id, token)
        if not msg:
            continue

        # Check exact timestamp — Gmail date filter is day-level only
        date_raw = _header(msg, "date")
        try:
            from email.utils import parsedate_to_datetime
            msg_dt = parsedate_to_datetime(date_raw).astimezone(timezone.utc)
            if msg_dt <= since_dt:
                state_manager.mark_notified(SOURCE_KEY, unique_id)
                continue
        except Exception:
            pass

        parsed = parse_inmail_reply(msg)
        if parsed is None:
            # No reply text — mark seen so we don't re-check
            state_manager.mark_notified(SOURCE_KEY, unique_id)
            continue

        subject = parsed["subject"]
        # Strip "Message replied: " / "Message accepted: " prefix for display
        inmail_subject = re.sub(r'^Message (replied|accepted)(: | from )', '', subject).strip()

        blocks = slack_client.format_reply_block(
            source="LinkedIn Recruiter (InMail)",
            candidate_name=parsed["candidate_name"],
            job_role=inmail_subject or "LinkedIn InMail",
            campaign="LinkedIn Recruiter",
            message_body=parsed["reply_text"],
            clickup_url=None,
            replied_at=parsed["received_at"],
        )

        if slack_client.post_message(blocks=blocks):
            state_manager.mark_notified(SOURCE_KEY, unique_id)
            sent += 1
            print(f"[linkedin] Notified: {parsed['candidate_name']} — {inmail_subject}")

        time.sleep(0.5)

    state_manager.set_last_checked(SOURCE_KEY, now)
    print(f"[linkedin] Done — {sent} notification(s) sent.")
    return sent


if __name__ == "__main__":
    count = run()
    print(f"LinkedIn Recruiter notifier finished — {count} notification(s) sent.")
