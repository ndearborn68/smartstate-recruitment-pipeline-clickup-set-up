"""
SmartState Notification System — State Manager
Tracks what has already been notified to prevent duplicate Slack messages.
State is persisted in state.json next to this file.
"""
import json
import os
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from . import config
except ImportError:
    import config


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _parse_iso(s: str) -> datetime:
    dt = datetime.fromisoformat(s)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt


def load_state() -> dict:
    """Load state from disk. Returns default state if file doesn't exist."""
    if not os.path.exists(config.STATE_FILE):
        return {"last_checked": {}, "notified_ids": {}}
    try:
        with open(config.STATE_FILE, "r") as f:
            return json.load(f)
    except Exception as e:
        print(f"[State] WARNING: Could not load state file: {e}. Starting fresh.")
        return {"last_checked": {}, "notified_ids": {}}


def save_state(state: dict) -> None:
    """Write state to disk. Tries atomic rename; falls back to direct write."""
    tmp_path = config.STATE_FILE + ".tmp"
    try:
        with open(tmp_path, "w") as f:
            json.dump(state, f, indent=2)
        os.replace(tmp_path, config.STATE_FILE)
    except Exception:
        # Fallback: write directly (non-atomic but won't crash the notifier)
        try:
            with open(config.STATE_FILE, "w") as f:
                json.dump(state, f, indent=2)
        except Exception as e2:
            print(f"[State] ERROR: could not save state: {e2}")


def get_last_checked(source: str) -> datetime:
    """Return last-checked datetime for a source. Defaults to 24 hours ago if not set."""
    state = load_state()
    ts = state.get("last_checked", {}).get(source)
    if ts:
        return _parse_iso(ts)
    return datetime.now(timezone.utc) - timedelta(hours=24)


def set_last_checked(source: str, dt: Optional[datetime] = None) -> None:
    """Set last-checked for a source to dt (default: now)."""
    state = load_state()
    state.setdefault("last_checked", {})
    state["last_checked"][source] = (dt or datetime.now(timezone.utc)).isoformat()
    save_state(state)


def is_notified(source: str, item_id: str) -> bool:
    """Return True if this item_id has already been notified for the given source."""
    state = load_state()
    return item_id in state.get("notified_ids", {}).get(source, {})


def mark_notified(source: str, item_id: str) -> None:
    """Mark an item as notified so it won't be re-posted to Slack."""
    state = load_state()
    state.setdefault("notified_ids", {}).setdefault(source, {})[item_id] = _now_iso()
    save_state(state)


def cleanup_old_entries(days: int = 30) -> int:
    """Remove notified entries older than `days` days. Returns count removed."""
    state = load_state()
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    removed = 0
    for source, items in state.get("notified_ids", {}).items():
        to_delete = [k for k, v in items.items() if _parse_iso(v) < cutoff]
        for k in to_delete:
            del items[k]
            removed += 1
    save_state(state)
    return removed
