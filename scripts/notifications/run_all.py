"""
SmartState Notification System — Main Orchestrator
Runs all notifiers on a schedule. Can be triggered via cron or run directly.

Usage:
    # Run once immediately (good for testing):
    python run_all.py

    # Run on a loop (polls every POLL_INTERVAL_MINUTES):
    python run_all.py --loop

    # Force a health report now (ignores interval):
    python run_all.py --health

Cron example (every 15 minutes):
    */15 * * * * cd /path/to/scripts/notifications && python run_all.py >> /tmp/smartstate_notifier.log 2>&1

    # Health check every 6 hours (also covered by --loop, but can run standalone):
    0 */6 * * * cd /path/to/scripts/notifications && python run_all.py --health >> /tmp/smartstate_health.log 2>&1
"""
import sys
import time
import argparse
from datetime import datetime, timezone

try:
    from . import config
    from . import instantly_notifier
    from . import heyreach_notifier
    from . import health_monitor
    from . import state_manager
except ImportError:
    import config
    import instantly_notifier
    import heyreach_notifier
    import health_monitor
    import state_manager


def run_once() -> dict:
    """
    Run all notifiers once. Returns a summary dict.
    """
    now = datetime.now(timezone.utc)
    print(f"\n{'='*60}")
    print(f"SmartState Notifier — {now.strftime('%Y-%m-%d %H:%M:%S UTC')}")
    print(f"{'='*60}")

    summary = {
        "instantly": 0,
        "heyreach": 0,
        "health_posted": False,
        "errors": [],
    }

    # 1. Instantly reply notifier
    print("\n[1/3] Instantly reply notifier...")
    try:
        summary["instantly"] = instantly_notifier.run()
    except Exception as e:
        msg = f"Instantly notifier error: {e}"
        print(f"ERROR: {msg}")
        summary["errors"].append(msg)

    # 2. Heyreach message notifier
    print("\n[2/3] Heyreach message notifier...")
    try:
        summary["heyreach"] = heyreach_notifier.run()
    except Exception as e:
        msg = f"Heyreach notifier error: {e}"
        print(f"ERROR: {msg}")
        summary["errors"].append(msg)

    # 3. Account health monitor (respects HEALTH_CHECK_INTERVAL_HOURS)
    print("\n[3/3] Account health monitor...")
    try:
        summary["health_posted"] = health_monitor.run(force=False)
    except Exception as e:
        msg = f"Health monitor error: {e}"
        print(f"ERROR: {msg}")
        summary["errors"].append(msg)

    # Cleanup old state entries (runs silently, once a day is fine)
    try:
        removed = state_manager.cleanup_old_entries(days=30)
        if removed > 0:
            print(f"\n[state] Cleaned up {removed} old notified entry(ies)")
    except Exception:
        pass

    print(f"\n{'='*60}")
    print(f"Done — Instantly: {summary['instantly']} | Heyreach: {summary['heyreach']} | Health: {'posted' if summary['health_posted'] else 'skipped'}")
    if summary["errors"]:
        print(f"Errors: {len(summary['errors'])}")
        for err in summary["errors"]:
            print(f"  - {err}")
    print(f"{'='*60}\n")

    return summary


def run_loop():
    """Run on a continuous loop, sleeping POLL_INTERVAL_MINUTES between runs."""
    interval_secs = config.POLL_INTERVAL_MINUTES * 60
    print(f"Starting SmartState notifier loop (interval: {config.POLL_INTERVAL_MINUTES} min)")
    print("Press Ctrl+C to stop.\n")

    while True:
        try:
            run_once()
        except KeyboardInterrupt:
            print("\nStopped by user.")
            break
        except Exception as e:
            print(f"ERROR in run_once: {e}")

        print(f"Sleeping {config.POLL_INTERVAL_MINUTES} minutes until next poll...")
        try:
            time.sleep(interval_secs)
        except KeyboardInterrupt:
            print("\nStopped by user.")
            break


def main():
    parser = argparse.ArgumentParser(description="SmartState Slack Notification Runner")
    parser.add_argument("--loop", action="store_true", help="Run on a continuous polling loop")
    parser.add_argument("--health", action="store_true", help="Force a health report now and exit")
    args = parser.parse_args()

    if args.health:
        print("Running forced health check...")
        health_monitor.run(force=True)
        return

    if args.loop:
        run_loop()
    else:
        run_once()


if __name__ == "__main__":
    main()
