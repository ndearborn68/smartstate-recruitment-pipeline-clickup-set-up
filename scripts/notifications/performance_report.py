"""
SmartState Notification System — Performance Report
Posts a 3x/week campaign + account health report to #smartstate-performance.

Covers:
  - Instantly (email) campaigns listed in INSTANTLY_CAMPAIGN_TO_ROLE
  - Heyreach (LinkedIn) campaigns listed in HEYREACH_CAMPAIGN_TO_ROLE
  - Instantly sending-account warmup / health scores

Note on Heyreach API: The GetConversationsV2 campaignId filter is ignored by the
API (returns all conversations regardless). Reply counts are read from state.json,
which tracks every inbound reply that has been posted to Slack.
"""

import json
import os
import time
import requests
from datetime import datetime
from typing import Optional

try:
    from . import config, state_manager
except ImportError:
    import config, state_manager

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

SLEEP_BETWEEN_CALLS = 0.65  # seconds — rate-limiting between API calls


# ---------------------------------------------------------------------------
# Slack helpers
# ---------------------------------------------------------------------------

def post_to_performance(text: str, blocks: Optional[list] = None) -> bool:
    """Post a message to SLACK_PERFORMANCE_WEBHOOK_URL. Returns True on success."""
    if not config.SLACK_PERFORMANCE_WEBHOOK_URL:
        print("[Performance] ERROR: SLACK_PERFORMANCE_WEBHOOK_URL not configured")
        return False

    payload: dict = {"text": text}
    if blocks:
        payload["blocks"] = blocks

    try:
        resp = requests.post(
            config.SLACK_PERFORMANCE_WEBHOOK_URL,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"},
            timeout=10,
        )
        if resp.status_code == 200:
            return True
        print(f"[Performance] ERROR: status {resp.status_code} — {resp.text}")
        return False
    except Exception as exc:
        print(f"[Performance] ERROR posting to Slack: {exc}")
        return False


# ---------------------------------------------------------------------------
# Instantly helpers
# ---------------------------------------------------------------------------

def _instantly_headers() -> dict:
    return {"Authorization": f"Bearer {config.INSTANTLY_API_KEY}"}


def _instantly_get(path: str, params: dict = None):
    """GET request against the Instantly v2 API. Returns parsed JSON or {}."""
    base = config.INSTANTLY_BASE_URL.rstrip("/")
    time.sleep(SLEEP_BETWEEN_CALLS)
    try:
        resp = requests.get(
            f"{base}{path}",
            headers=_instantly_headers(),
            params=params or {},
            timeout=20,
        )
        if resp.status_code != 200:
            print(f"[Instantly] GET {path} → {resp.status_code}: {resp.text[:200]}")
            return {}
        return resp.json()
    except Exception as exc:
        print(f"[Instantly] GET {path} error: {exc}")
        return {}


def fetch_instantly_campaigns() -> dict:
    """
    Fetch all SmartState campaigns from Instantly.
    Returns dict keyed by campaign id -> campaign object.
    """
    data = _instantly_get("/campaigns", {"limit": 100})
    if isinstance(data, list):
        items = data
    elif isinstance(data, dict):
        items = data.get("items", data.get("campaigns", data.get("data", [])))
    else:
        items = []
    return {c.get("id", ""): c for c in items if c}


def fetch_instantly_accounts() -> list:
    """Fetch all Instantly sending accounts. Returns list of account dicts."""
    data = _instantly_get("/accounts", {"limit": 100})
    if isinstance(data, list):
        return data
    if isinstance(data, dict):
        return data.get("items", data.get("accounts", data.get("data", [])))
    return []


def _parse_instantly_campaign_stats(campaign: dict) -> tuple[int, int, float]:
    """Extract (sent, replied, reply_rate_pct) from a campaign object."""
    sent = (
        campaign.get("emails_sent")
        or campaign.get("sent_count")
        or campaign.get("total_sent")
        or 0
    )
    replied = (
        campaign.get("replies")
        or campaign.get("reply_count")
        or campaign.get("replied_count")
        or campaign.get("total_replies")
        or 0
    )
    stats = campaign.get("stats") or campaign.get("analytics") or {}
    if isinstance(stats, dict):
        sent = sent or stats.get("sent", 0) or stats.get("emails_sent", 0) or 0
        replied = replied or stats.get("replied", 0) or stats.get("reply_count", 0) or 0

    sent = int(sent)
    replied = int(replied)
    rate = round((replied / sent * 100), 1) if sent > 0 else 0.0
    return sent, replied, rate


def _classify_warmup(email: str, account: dict) -> dict:
    """
    Classify warmup health from the account object fields.
    Instantly v2 API includes stat_warmup_score and warmup_status inline.
    warmup_status: 1 = active, 2 = paused, 0 = disabled
    Returns {email, health_score, status, details}.
    """
    score = account.get("stat_warmup_score")
    score = int(score) if score is not None else None
    warmup_status = account.get("warmup_status", 1)  # 1=active, 2=paused/off
    account_status = account.get("status", 1)  # 1=active, 0=disconnected

    if account_status == 0:
        status = "Disconnected"
    elif warmup_status != 1:
        status = "Warmup Off"
    elif score is None:
        status = "Unknown"
    elif score >= 80:
        status = "Healthy"
    elif score >= 55:
        status = "Warning"
    else:
        status = "Critical"

    daily_limit = account.get("daily_limit", "?")
    warmup_limit = (account.get("warmup") or {}).get("limit", "?")
    details = f"Daily limit: {daily_limit} | Warmup limit: {warmup_limit}/day"

    return {"email": email, "health_score": score, "status": status, "details": details}


# ---------------------------------------------------------------------------
# Heyreach helpers
# ---------------------------------------------------------------------------

def _heyreach_headers() -> dict:
    return {
        "X-API-KEY": config.HEYREACH_API_KEY,
        "Content-Type": "application/json",
    }


def fetch_heyreach_total_conversations() -> int:
    """
    Return total conversation count across all LinkedIn accounts.
    Uses a single GetConversationsV2 call (limit=1) to read totalCount.
    Note: campaignId filter is not honoured by the API; this is a global count.
    """
    base = config.HEYREACH_BASE_URL.rstrip("/")
    try:
        r = requests.post(
            f"{base}/inbox/GetConversationsV2",
            headers=_heyreach_headers(),
            json={"offset": 0, "limit": 1},
            timeout=15,
        )
        time.sleep(SLEEP_BETWEEN_CALLS)
        if r.status_code != 200:
            print(f"[Heyreach] ERROR getting total conversations: {r.status_code}")
            return 0
        return r.json().get("totalCount", 0) or 0
    except Exception as exc:
        print(f"[Heyreach] ERROR getting total conversations: {exc}")
        return 0


def count_heyreach_replies_from_state() -> int:
    """
    Count how many unique Heyreach inbound replies have been posted to Slack.
    Reads from state.json (the authoritative source of notified inbound replies).
    """
    try:
        state = state_manager.load_state()
        return len(state.get("notified_ids", {}).get("heyreach", {}))
    except Exception as exc:
        print(f"[Heyreach] ERROR reading state for reply count: {exc}")
        return 0


# ---------------------------------------------------------------------------
# Report builders
# ---------------------------------------------------------------------------

def _pad(label: str, width: int = 26) -> str:
    return label.ljust(width)


def build_campaign_report() -> tuple[str, int, int]:
    """
    Compile campaign performance text.
    Returns (report_text, total_email_sent, total_replied).
    """
    date_str = datetime.now().strftime("%a %b %-d, %Y")
    lines = [f"📊 *SmartState Campaign Performance — {date_str}*\n"]

    # ── EMAIL (Instantly) ───────────────────────────────────────────────────
    lines.append("*✉️ EMAIL (Instantly)*")
    instantly_campaigns = {}
    if config.INSTANTLY_CAMPAIGN_TO_ROLE:
        print("[Performance] Fetching Instantly campaigns...")
        instantly_campaigns = fetch_instantly_campaigns()

    email_sent_total = 0
    email_replied_total = 0

    for campaign_id, role in config.INSTANTLY_CAMPAIGN_TO_ROLE.items():
        campaign_obj = instantly_campaigns.get(str(campaign_id), instantly_campaigns.get(campaign_id))
        if campaign_obj is None:
            lines.append(f"  {_pad(role)} — Sent: N/A | Replied: N/A | Rate: N/A")
            continue
        sent, replied, rate = _parse_instantly_campaign_stats(campaign_obj)
        email_sent_total += sent
        email_replied_total += replied
        status_str = campaign_obj.get("status", "")
        status_label = {1: "active", 2: "paused", 3: "completed", 0: "draft"}.get(status_str, str(status_str))
        lines.append(
            f"  {_pad(role)} — Sent: {sent:<5} | Replied: {replied:<4} | Rate: {rate}% | {status_label}"
        )

    if not config.INSTANTLY_CAMPAIGN_TO_ROLE:
        lines.append("  _(no campaigns configured)_")

    email_rate = round(email_replied_total / email_sent_total * 100, 1) if email_sent_total else 0.0
    lines.append(f"\n  *Email totals:* {email_sent_total} sent | {email_replied_total} replied | {email_rate}% reply rate")

    # ── LINKEDIN (Heyreach) ─────────────────────────────────────────────────
    lines.append("\n*💼 LINKEDIN (Heyreach)*")

    print("[Performance] Counting Heyreach replies from state.json...")
    total_conversations = fetch_heyreach_total_conversations()
    li_replies = count_heyreach_replies_from_state()

    lines.append(f"  Total LinkedIn conversations: {total_conversations:,}")
    lines.append(f"  Inbound replies posted to Slack: {li_replies}")

    # List each campaign and its status (from config mapping)
    campaign_statuses = {
        354909: "IN_PROGRESS", 349645: "IN_PROGRESS",
        357063: "DRAFT", 357067: "FINISHED",
        357072: "FINISHED", 357074: "DRAFT",
        357075: "DRAFT", 357076: "DRAFT",
    }
    lines.append("  ─")
    for campaign_id, role in config.HEYREACH_CAMPAIGN_TO_ROLE.items():
        st = campaign_statuses.get(int(campaign_id), "—")
        emoji = {"IN_PROGRESS": "🟢", "FINISHED": "✅", "DRAFT": "⏸️"}.get(st, "⚪")
        lines.append(f"  {emoji} {_pad(role)} ({st.lower().replace('_',' ')})")

    # ── Overall ─────────────────────────────────────────────────────────────
    total_replied = email_replied_total + li_replies
    lines.append(
        f"\n*Overall replies:* {email_replied_total} email + {li_replies} LinkedIn = {total_replied} total"
    )

    return "\n".join(lines), email_sent_total, total_replied


def build_account_health_report() -> str:
    """
    Compile Instantly sending-account health text.
    Returns formatted report string.
    """
    lines = ["🏥 *Sending Account Health (Instantly)*\n"]

    print("[Performance] Fetching account list...")
    accounts = fetch_instantly_accounts()
    if not accounts:
        lines.append("_(no sending accounts found or API error)_")
        return "\n".join(lines)

    print(f"[Performance] Classifying warmup for {len(accounts)} account(s)...")
    emoji_map = {
        "Healthy": "✅", "Warning": "⚠️", "Critical": "🔴",
        "Warmup Off": "⏸️", "Unknown": "❓", "Disconnected": "🔌",
    }
    counts = {"Healthy": 0, "Warning": 0, "Critical": 0, "Warmup Off": 0, "Unknown": 0, "Disconnected": 0}

    for account in accounts:
        email = account.get("email", account.get("address", "unknown"))
        health = _classify_warmup(email, account)
        status = health["status"]
        counts[status] = counts.get(status, 0) + 1
        emoji = emoji_map.get(status, "❓")
        score_str = f"Score: {health['health_score']}" if health["health_score"] is not None else "Score: N/A"
        lines.append(f"{emoji} `{email}` — {score_str} | {health['details']}")

    summary = (
        f"{len(accounts)} accounts | "
        f"{counts['Healthy']} healthy | {counts['Warning']} warning | {counts['Critical']} critical"
    )
    lines.append(f"\n_{summary}_")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Main entry point
# ---------------------------------------------------------------------------

def run() -> bool:
    """
    Build and post both performance messages to #smartstate-performance.
    Returns True only if both posts succeed.
    """
    print("[Performance] Starting performance report...")

    # Message 1 — Campaign Performance
    try:
        campaign_text, _email_sent, _total_replied = build_campaign_report()
    except Exception as exc:
        print(f"[Performance] ERROR building campaign report: {exc}")
        import traceback; traceback.print_exc()
        campaign_text = "📊 *SmartState Campaign Performance* — error building report."

    ok1 = post_to_performance(campaign_text)
    print(f"[Performance] Campaign report posted: {ok1}")

    time.sleep(SLEEP_BETWEEN_CALLS)

    # Message 2 — Account Health
    try:
        health_text = build_account_health_report()
    except Exception as exc:
        print(f"[Performance] ERROR building health report: {exc}")
        import traceback; traceback.print_exc()
        health_text = "🏥 *Sending Account Health* — error building report."

    ok2 = post_to_performance(health_text)
    print(f"[Performance] Account health report posted: {ok2}")

    return ok1 and ok2


if __name__ == "__main__":
    success = run()
    print(f"[Performance] Done — {'OK' if success else 'one or more posts failed'}")
