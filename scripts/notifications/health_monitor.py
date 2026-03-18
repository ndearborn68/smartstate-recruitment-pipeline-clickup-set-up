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
    data = _get("/account/list", {"limit": 100, "skip": 0})
    accounts = data if isinstance(data, list) else data.get("accounts", [])
    print(f"[health] Found {len(accounts)} sending account(s)")
    return accounts


def fetch_account_warmup(email: str) -> dict:
    """
    Fetch warmup/deliverability analytics for one sending account.
    Returns dict: email, warmup_score, inbox_rate, spam_rate, warmup_enabled, raw_response
    """
    result = {
        "email": email,
        "warmup_score": None,
        "inbox_rate": None,
        "spam_rate": None,
        "warmup_enabled": False,
        "raw_response": {},
    }

    # Primary endpoint: warmup analytics
    data = _get("/account/warmup/analytics", {"email": email})

    if data:
        result["raw_response"] = data
        result["warmup_enabled"] = data.get("warmup_enabled", data.get("warmupEnabled", False))

        # Score: Instantly may return as "score", "warmup_score", or "health_score"
        score = (
            data.get("score") or
            data.get("warmup_score") or
            data.get("health_score") or
            data.get("warmupScore")
        )
        if score is not None:
            try:
                result["warmup_score"] = int(float(score))
            except (ValueError, TypeError):
                pass

        # Inbox/spam rates
        inbox = data.get("inbox_rate") or data.get("inboxRate") or data.get("inbox_percent")
        spam = data.get("spam_rate") or data.get("spamRate") or data.get("spam_percent")
        if inbox is not None:
            try:
                result["inbox_rate"] = round(float(inbox), 1)
            except (ValueError, TypeError):
                pass
        if spam is not None:
            try:
                result["spam_rate"] = round(float(spam), 1)
            except (ValueError, TypeError):
                pass

    return result


def classify_health(account: dict) -> tuple:
    """
    Classify an account's health status.
    Returns (status: str, details: str).
    """
    score = account.get("warmup_score")
    enabled = account.get("warmup_enabled", False)
    inbox = account.get("inbox_rate")
    spam = account.get("spam_rate")

    inbox_str = f"{inbox}%" if inbox is not None else "N/A"
    spam_str = f"{spam}%" if spam is not None else "N/A"
    rate_details = f"Inbox: {inbox_str} | Spam: {spam_str}"

    if not enabled:
        return ("Warmup Off", "Warmup disabled — enable to track deliverability")

    if score is None:
        return ("Unknown", "Could not fetch warmup data")

    if score >= 80:
        return ("Healthy", rate_details)
    elif score >= 50:
        return ("Warning", f"{rate_details} — monitor closely")
    else:
        return ("Critical", f"{rate_details} — ACTION REQUIRED")


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

        print(f"[health] Checking: {email}")
        try:
            health_data = fetch_account_warmup(email)
        except Exception as e:
            print(f"[health] fetch_account_warmup failed for {email}: {e}")
            health_data = {
                "email": email,
                "warmup_score": None,
                "inbox_rate": None,
                "spam_rate": None,
                "warmup_enabled": False,
            }

        status, details = classify_health(health_data)

        record = {
            "email": email,
            "health_score": health_data.get("warmup_score"),
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
