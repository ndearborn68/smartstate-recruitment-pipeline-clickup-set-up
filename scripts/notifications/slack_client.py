"""
SmartState Notification System — Slack Client
Handles all Slack message formatting and posting.
"""
import json
import requests
from datetime import datetime
from typing import Optional

try:
    from . import config
except ImportError:
    import config


def post_message(text: str = "", blocks: Optional[list] = None) -> bool:
    """Post a message to the configured Slack webhook. Returns True on success."""
    if not config.SLACK_WEBHOOK_URL:
        print("[Slack] ERROR: SLACK_WEBHOOK_URL not configured")
        return False

    payload = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    try:
        resp = requests.post(
            config.SLACK_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            return True
        else:
            print(f"[Slack] ERROR: status {resp.status_code} — {resp.text}")
            return False
    except Exception as e:
        print(f"[Slack] ERROR: {e}")
        return False


def format_reply_block(
    source: str,
    candidate_name: str,
    job_role: str,
    campaign: str,
    message_body: str,
    clickup_url: Optional[str] = None,
    replied_at: Optional[datetime] = None,
) -> list:
    """
    Build a Slack blocks payload for a new candidate reply/message.

    Example output:
        🔔 New Reply — Senior Flutter Developer
        Candidate: John Smith
        Source: Heyreach (LinkedIn)
        Campaign: Senior Flutter - LinkedIn 1
        <full message body>
        📋 View in ClickUp: <link>
    """
    header = f"🔔 New Reply — {job_role}"

    ts_str = ""
    if replied_at:
        ts_str = f"\n*Received:* {replied_at.strftime('%Y-%m-%d %H:%M UTC')}"

    meta = (
        f"*Candidate:* {candidate_name}\n"
        f"*Source:* {source}\n"
        f"*Campaign:* {campaign}"
        f"{ts_str}"
    )

    # Slack block text max is 3000 chars — split into multiple blocks if needed
    full_body = message_body.strip()
    body_chunks = [full_body[i:i+2900] for i in range(0, max(len(full_body), 1), 2900)]

    blocks = [
        {"type": "header", "text": {"type": "plain_text", "text": header}},
        {"type": "section", "text": {"type": "mrkdwn", "text": meta}},
        {"type": "divider"},
    ]
    for chunk in body_chunks:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": chunk}})

    if clickup_url:
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"📋 <{clickup_url}|View in ClickUp>"},
        })

    blocks.append({"type": "divider"})
    return blocks


def format_health_block(
    account_email: str,
    health_score: Optional[int],
    status: str,
    details: str,
) -> str:
    """Format a single account health line for inclusion in a health report."""
    emoji_map = {
        "Healthy": "✅",
        "Warning": "⚠️",
        "Critical": "🔴",
        "Warmup Off": "⏸️",
        "Unknown": "❓",
    }
    emoji = emoji_map.get(status, "❓")
    score_str = f"Score: {health_score}" if health_score is not None else "Score: N/A"
    return f"{emoji} `{account_email}` — {score_str} | {details}"


def post_health_report(accounts: list) -> bool:
    """
    Post a consolidated health report to Slack.
    Each item in accounts should be a dict with keys:
        email, health_score (int or None), status (str), details (str)
    """
    if not accounts:
        return False

    counts = {"Healthy": 0, "Warning": 0, "Critical": 0, "Warmup Off": 0, "Unknown": 0}
    lines = []
    for acct in accounts:
        status = acct.get("status", "Unknown")
        counts[status] = counts.get(status, 0) + 1
        lines.append(format_health_block(
            acct.get("email", "unknown"),
            acct.get("health_score"),
            status,
            acct.get("details", ""),
        ))

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    summary = (
        f"{len(accounts)} accounts checked | "
        f"{counts['Healthy']} healthy | "
        f"{counts['Warning']} warning | "
        f"{counts['Critical']} critical"
    )

    full_text = f"📊 *Sending Account Health Report — {timestamp}*\n\n" + "\n".join(lines) + f"\n\n_{summary}_"

    # Split lines into chunks that fit within Slack's 3000-char section limit
    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"📊 Account Health Report — {timestamp}"},
        },
    ]
    chunk, chunk_len = [], 0
    for line in lines:
        line_len = len(line) + 1  # +1 for newline
        if chunk and chunk_len + line_len > 2900:
            blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(chunk)}})
            chunk, chunk_len = [], 0
        chunk.append(line)
        chunk_len += line_len
    if chunk:
        blocks.append({"type": "section", "text": {"type": "mrkdwn", "text": "\n".join(chunk)}})

    blocks += [
        {"type": "context", "elements": [{"type": "mrkdwn", "text": summary}]},
        {"type": "divider"},
    ]

    return post_message(full_text, blocks)
