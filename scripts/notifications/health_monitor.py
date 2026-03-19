"""
SmartState Notification System — Account Health Monitor
Periodically checks the warmup/deliverability health of each Instantly
sending account and posts a consolidated report to Slack.
Urgent alerts are sent immediately for Critical accounts.
"""
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from . import config, slack_client, state_manager
except ImportError:
    import config, slack_client, state_manager

SOURCE_KEY = "health"
RATE_LIMIT_DELAY = 0.65


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
            print(f"[health] GET {path} → {resp.status_code}: {resp.text[:200]}")
            return {}
        return resp.json()
    except Exception as e:
        print(f"[health] GET {path} error: {e}")
        return {}


# ── Account fetching ─────────────────────────────────────────────────────────

def fetch_account_list() -> list:
    """
    Fetch all sending accounts from Instantly.
    Returns list of dicts with at minimum: email, status, daily_limit.
    """
    data = _get("/accounts", {"limit": 100})
    accounts = data.get("items", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
    print(f"[health] Found {len(accounts)} sending account(s)")
    return accounts


def classify_health(acct: dict) -> tuple:
    """
    Classify an account's health status using inline fields from GET /accounts.
    Instantly v2 includes stat_warmup_score, warmup_status, status, daily_limit
    directly in the account object — no separate warmup API call needed.

    warmup_status: 1=active, 2=paused/off
    status: 1=connected, 0=disconnected
    Returns (status: str, details: str, score: int|None).
    """
    score = acct.get("stat_warmup_score")
    score = int(score) if score is not None else None
    warmup_status = acct.get("warmup_status", 1)
    account_status = acct.get("status", 1)
    daily_limit = acct.get("daily_limit", "?")
    warmup_limit = (acct.get("warmup") or {}).get("limit", "?")
    details = f"Daily limit: {daily_limit} | Warmup: {warmup_limit}/day"

    if account_status == 0:
        return ("Unknown", "Account disconnected", None)
    if warmup_status != 1:
        return ("Warmup Off", details, score)
    if score is None:
        return ("Unknown", "No warmup score available", None)
    if score >= 80:
        return ("Healthy", details, score)
    elif score >= 50:
        return ("Warning", f"{details} — monitor closely", score)
    else:
        return ("Critical", f"{details} — ACTION REQUIRED", score)


# ── Main entry point ─────────────────────────────────────────────────────────

def run(force: bool = False) -> bool:
    """
    Check health of all Instantly sending accounts and post report to Slack.

    Args:
        force: If True, skip the interval check and always run.

    Returns:
        True if the health report was posted, False if skipped or failed.
    """
    # Check if enough time has passed since last health report
    if not force:
        last = state_manager.get_last_checked(SOURCE_KEY)
        interval = timedelta(hours=config.HEALTH_CHECK_INTERVAL_HOURS)
        time_since = datetime.now(timezone.utc) - last
        if time_since < interval:
            remaining = interval - time_since
            mins = int(remaining.total_seconds() / 60)
            print(f"[health] Skipping — next check in {mins} min(s)")
            return False

    print(f"[health] Running account health check...")

    # Fetch accounts
    try:
        accounts = fetch_account_list()
    except Exception as e:
        print(f"[health] fetch_account_list failed: {e}")
        return False

    if not accounts:
        print("[health] No accounts found — check INSTANTLY_API_KEY")
        return False

    # Fetch health for each account
    results = []
    critical_accounts = []

    for acct in accounts:
        email = (acct.get("email") or acct.get("address") or "").strip()
        if not email:
            continue

        status, details, score = classify_health(acct)

        record = {
            "email": email,
            "health_score": score,
            "status": status,
            "details": details,
        }
        results.append(record)

        if status == "Critical":
            critical_accounts.append(record)

    # Post consolidated report
    print(f"[health] Posting report for {len(results)} account(s)...")
    success = slack_client.post_health_report(results)

    # Post individual urgent alerts for Critical accounts
    for acct in critical_accounts:
        inbox_info = acct["details"].split("|")[0].replace("Inbox:", "").strip()
        slack_client.post_message(
            f"🚨 *URGENT — Critical Account:* `{acct['email']}`\n"
            f"Score: {acct['health_score']} | {acct['details']}\n"
            f"This account may be landing in spam. Pause and investigate immediately."
        )

    if success:
        state_manager.set_last_checked(SOURCE_KEY)
        print(f"[health] Report posted. {len(critical_accounts)} critical account(s) flagged.")

    return success


if __name__ == "__main__":
    result = run(force=True)
    print(f"Health monitor finished — report posted: {result}")
