"""
SmartState Non-Responder Follow-Up Pipeline

Runs daily. Identifies candidates contacted via LinkedIn Recruiter or Heyreach
who have not replied after NO_REPLY_DAYS days. Enriches each lead via LeadMagic
(phone + email), sends SMS via Twilio, and pushes to Clay webhooks.

Sources checked:
  - LinkedIn Recruiter "Awaiting Reply" inbox (Chrome CDP — requires Chrome open)
  - Heyreach conversations with outbound messages but no inbound reply

Dedup: state.json tracks every lead actioned so no one is contacted twice.
"""
import json
import os
import subprocess
import time
import requests
from datetime import datetime, timedelta, timezone
from typing import Optional

try:
    from . import config, state_manager
except ImportError:
    import config, state_manager

SOURCE_KEY   = "nonresponder"
CDP_SCRIPT   = os.path.expanduser("~/.claude/skills/chrome-cdp/scripts/cdp.mjs")
LEADMAGIC_KEY = "13e0ebd117f63815562eacbd9492fb51"
LEADMAGIC_URL = "https://api.leadmagic.io"


# ── Chrome CDP helpers ────────────────────────────────────────────────────────

def _cdp_list() -> str:
    """Return output of `cdp.mjs list`."""
    r = subprocess.run(["node", CDP_SCRIPT, "list"], capture_output=True, text=True, timeout=15)
    return r.stdout


def _cdp_eval(target: str, expr: str) -> str:
    """Run a JS expression in the given Chrome tab. Returns stdout string."""
    r = subprocess.run(
        ["node", CDP_SCRIPT, "eval", target, expr],
        capture_output=True, text=True, timeout=30
    )
    return r.stdout.strip()


def _find_linkedin_recruiter_target() -> Optional[str]:
    """Find the Chrome tab ID for LinkedIn Talent/Recruiter inbox."""
    listing = _cdp_list()
    for line in listing.splitlines():
        if "linkedin.com/talent" in line or "LinkedIn Talent" in line:
            parts = line.strip().split()
            if parts:
                return parts[0]
    return None


# ── LinkedIn Recruiter scraper ────────────────────────────────────────────────

def get_linkedin_recruiter_nonresponders() -> list:
    """
    Scrape LinkedIn Recruiter 'Awaiting Reply' inbox via Chrome CDP.
    Returns leads pending 2+ days: [{name, sent_at, source, linkedin_url, email, phone}]
    Requires Chrome to be open on the LinkedIn Recruiter inbox tab.
    """
    target = _find_linkedin_recruiter_target()
    if not target:
        print("[nonresponder] LinkedIn Recruiter tab not open — skipping")
        return []

    print(f"[nonresponder] LinkedIn Recruiter tab found: {target}")

    # Scroll the conversation list to load all entries
    scroll_expr = (
        "var p=document.querySelector('._conversations-container_zkxis6');"
        "if(p){p.scrollTop=p.scrollHeight;p.scrollHeight;}else{0;}"
    )
    prev_h = 0
    for _ in range(12):
        raw = _cdp_eval(target, scroll_expr)
        try:
            h = int(raw)
        except Exception:
            break
        if h == prev_h:
            break
        prev_h = h
        time.sleep(1.5)

    # Extract names + dates
    extract = (
        "JSON.stringify("
        "Array.from(document.querySelectorAll('li')).filter(function(el){"
        "  return el.innerText&&el.innerText.indexOf('Pending')>-1;"
        "}).map(function(el){"
        "  var lines=el.innerText.trim().split('\\n').map(function(l){return l.trim();}).filter(Boolean);"
        "  return {name:lines[0],date:lines[1]||''};"
        "}).filter(function(x){return x.name&&x.date&&x.date.indexOf(' ')>-1;}))"
    )
    raw = _cdp_eval(target, extract)
    try:
        items = json.loads(raw)
    except Exception:
        print("[nonresponder] Could not parse LinkedIn Recruiter list")
        return []

    cutoff     = datetime.now(timezone.utc) - timedelta(days=config.NO_REPLY_DAYS)
    cur_year   = datetime.now().year
    results    = []

    for item in items:
        date_str = (item.get("date") or "").strip()
        if not date_str:
            continue
        try:
            dt = datetime.strptime(f"{date_str} {cur_year}", "%b %d %Y").replace(tzinfo=timezone.utc)
        except Exception:
            continue
        if dt > cutoff:
            continue  # Too recent

        results.append({
            "name":         item["name"],
            "sent_at":      dt,
            "source":       "linkedin_recruiter",
            "linkedin_url": "",
            "email":        "",
            "phone":        "",
        })

    print(f"[nonresponder] LinkedIn Recruiter: {len(results)} non-responder(s)")
    return results


# ── Heyreach non-responder detection ─────────────────────────────────────────

def get_heyreach_nonresponders() -> list:
    """
    Fetch Heyreach conversations and return those with outbound messages
    sent 2+ days ago and no inbound reply at all.
    """
    cutoff      = datetime.now(timezone.utc) - timedelta(days=config.NO_REPLY_DAYS)
    too_old     = datetime.now(timezone.utc) - timedelta(days=30)
    headers     = {"X-API-KEY": config.HEYREACH_API_KEY, "Content-Type": "application/json"}
    results     = []
    offset      = 0
    limit       = 50

    while True:
        time.sleep(0.65)
        try:
            resp = requests.post(
                f"{config.HEYREACH_BASE_URL}/inbox/GetConversationsV2",
                headers=headers,
                json={"offset": offset, "limit": limit},
                timeout=30,
            )
            if resp.status_code != 200:
                break
            data  = resp.json()
            items = data.get("items", [])
        except Exception as e:
            print(f"[nonresponder] Heyreach fetch error: {e}")
            break

        if not items:
            break

        # Stop paging if conversations are older than 30 days
        oldest_raw = ""
        for item in items:
            lma = item.get("lastMessageAt") or ""
            if lma and (not oldest_raw or lma < oldest_raw):
                oldest_raw = lma
        if oldest_raw:
            try:
                oldest = datetime.fromisoformat(oldest_raw.replace("Z", "+00:00"))
                if oldest.tzinfo is None:
                    oldest = oldest.replace(tzinfo=timezone.utc)
                if oldest < too_old:
                    break
            except Exception:
                pass

        for conv in items:
            messages = conv.get("messages", [])
            inbound  = [m for m in messages if m.get("sender") == "CORRESPONDENT"]
            outbound = [m for m in messages if m.get("sender") != "CORRESPONDENT"]

            if inbound:
                continue  # Already replied
            if not outbound:
                continue

            # Earliest outbound message date
            first_raw = min(
                (m.get("createdAt", "") for m in outbound if m.get("createdAt")),
                default="",
            )
            if not first_raw:
                continue
            try:
                sent_at = datetime.fromisoformat(first_raw.replace("Z", "+00:00"))
                if sent_at.tzinfo is None:
                    sent_at = sent_at.replace(tzinfo=timezone.utc)
            except Exception:
                continue

            if sent_at > cutoff:
                continue  # Too recent — wait longer

            profile      = conv.get("correspondentProfile", {})
            first        = (profile.get("firstName") or "").strip()
            last         = (profile.get("lastName")  or "").strip()
            name         = f"{first} {last}".strip() or "Unknown"
            linkedin_url = (profile.get("profileUrl") or "").strip()
            email        = (
                profile.get("emailAddress") or
                profile.get("customEmailAddress") or ""
            ).strip().lower()

            results.append({
                "name":         name,
                "sent_at":      sent_at,
                "source":       "heyreach",
                "linkedin_url": linkedin_url,
                "email":        email,
                "phone":        "",
            })

        if len(items) < limit:
            break
        offset += limit

    print(f"[nonresponder] Heyreach: {len(results)} non-responder(s)")
    return results


# ── Instantly non-responder detection ────────────────────────────────────────

def get_instantly_nonresponders() -> list:
    """
    Find Instantly leads who were sent an email 2+ days ago with no reply.
    Returns [{name, email, sent_at, source, linkedin_url, phone}]
    LinkedIn URL is fetched via LeadMagic by email — these go to Clay LinkedIn table.
    """
    cutoff  = datetime.now(timezone.utc) - timedelta(days=config.NO_REPLY_DAYS)
    headers = {
        "Authorization": f"Bearer {config.INSTANTLY_API_KEY}",
        "Content-Type": "application/json",
    }
    results     = []
    replied_emails = set()

    # First pass: collect all emails that have replied (ue_type 2 or 3)
    for campaign_id in config.INSTANTLY_CAMPAIGN_TO_ROLE:
        cursor = None
        while True:
            time.sleep(0.65)
            params = {"campaign_id": campaign_id, "limit": 100}
            if cursor:
                params["starting_after"] = cursor
            try:
                resp = requests.get(
                    f"{config.INSTANTLY_BASE_URL}/emails",
                    headers=headers, params=params, timeout=30,
                )
                data  = resp.json() if resp.status_code == 200 else {}
                items = data.get("items", [])
            except Exception:
                break
            for em in items:
                if em.get("ue_type") in (2, 3):
                    email = (em.get("lead") or em.get("from_address_email") or "").lower().strip()
                    if email:
                        replied_emails.add(email)
            cursor = data.get("next_starting_after")
            if not cursor or not items:
                break

    # Second pass: find sent emails (ue_type 1) with no reply that are 2+ days old
    seen_leads = set()
    for campaign_id, job_role in config.INSTANTLY_CAMPAIGN_TO_ROLE.items():
        cursor = None
        while True:
            time.sleep(0.65)
            params = {"campaign_id": campaign_id, "limit": 100}
            if cursor:
                params["starting_after"] = cursor
            try:
                resp = requests.get(
                    f"{config.INSTANTLY_BASE_URL}/emails",
                    headers=headers, params=params, timeout=30,
                )
                data  = resp.json() if resp.status_code == 200 else {}
                items = data.get("items", [])
            except Exception:
                break

            found_new = False
            for em in items:
                if em.get("ue_type") != 1:  # sent emails only
                    continue
                ts_raw = em.get("timestamp_email") or ""
                if not ts_raw:
                    continue
                try:
                    sent_at = datetime.fromisoformat(ts_raw.replace("Z", "+00:00"))
                    if sent_at.tzinfo is None:
                        sent_at = sent_at.replace(tzinfo=timezone.utc)
                except Exception:
                    continue

                if sent_at > cutoff:
                    found_new = True
                    continue  # Too recent

                lead_email = (em.get("lead") or em.get("to_address_email") or "").lower().strip()
                if not lead_email or lead_email in replied_emails or lead_email in seen_leads:
                    continue

                seen_leads.add(lead_email)
                name = lead_email.split("@")[0].replace(".", " ").title()
                results.append({
                    "name":         name,
                    "email":        lead_email,
                    "sent_at":      sent_at,
                    "source":       "instantly",
                    "linkedin_url": "",
                    "phone":        "",
                    "job_role":     job_role,
                })

            cursor = data.get("next_starting_after")
            if not cursor or not found_new:
                break

    print(f"[nonresponder] Instantly: {len(results)} non-responder(s)")
    return results


# ── LeadMagic enrichment ──────────────────────────────────────────────────────

def enrich_lead(name: str, linkedin_url: str) -> dict:
    """
    Look up email + phone via LeadMagic using LinkedIn URL.
    Returns {email, phone}. Both may be empty strings if not found.
    """
    result = {"email": "", "phone": ""}
    if not linkedin_url:
        return result
    try:
        resp = requests.post(
            f"{LEADMAGIC_URL}/profile-finder",
            headers={"X-BLOBR-KEY": LEADMAGIC_KEY, "Content-Type": "application/json"},
            json={"linkedin_url": linkedin_url},
            timeout=20,
        )
        if resp.status_code == 200:
            data = resp.json()
            result["email"] = (data.get("email") or "").strip().lower()
            result["phone"] = (
                data.get("mobile_number") or
                data.get("phone_number")  or
                data.get("phone")         or ""
            ).strip()
    except Exception as e:
        print(f"[nonresponder] LeadMagic error for {name}: {e}")
    return result


# ── Twilio SMS ────────────────────────────────────────────────────────────────

def send_sms(to_phone: str, name: str) -> bool:
    """Send follow-up SMS via Twilio. Returns True on success."""
    if not to_phone or not config.TWILIO_ACCOUNT_SID or not config.FOLLOWUP_SMS_COPY:
        return False

    # Normalize phone to E.164
    digits = "".join(c for c in to_phone if c.isdigit())
    if len(digits) == 10:
        digits = "1" + digits
    phone = "+" + digits

    first_name = name.split()[0] if name else "there"
    body = config.FOLLOWUP_SMS_COPY.replace("[name]", first_name)

    try:
        resp = requests.post(
            f"https://api.twilio.com/2010-04-01/Accounts/{config.TWILIO_ACCOUNT_SID}/Messages.json",
            auth=(config.TWILIO_ACCOUNT_SID, config.TWILIO_AUTH_TOKEN),
            data={"From": config.TWILIO_FROM_NUMBER, "To": phone, "Body": body},
            timeout=15,
        )
        if resp.status_code in (200, 201):
            print(f"[nonresponder] SMS sent → {name} ({phone})")
            return True
        print(f"[nonresponder] SMS failed for {name}: {resp.status_code} {resp.text[:200]}")
        return False
    except Exception as e:
        print(f"[nonresponder] SMS error for {name}: {e}")
        return False


# ── Clay webhook ──────────────────────────────────────────────────────────────

def push_to_clay(webhook_url: str, lead: dict) -> bool:
    """Push a single lead row to a Clay webhook. Returns True on success."""
    if not webhook_url:
        return False
    try:
        resp = requests.post(webhook_url, json=lead, timeout=15)
        return resp.status_code in (200, 201, 202)
    except Exception as e:
        print(f"[nonresponder] Clay push error: {e}")
        return False


# ── Main entry point ──────────────────────────────────────────────────────────

def run() -> int:
    """
    Collect non-responders from all sources, enrich, send SMS, push to Clay.
    Returns count of leads actioned.
    """
    print("[nonresponder] Starting non-responder pipeline...")

    state    = state_manager.load_state()
    actioned = state.setdefault("followup_sent", {})

    # Gather from all sources
    sms_leads      = []   # LinkedIn Recruiter + Heyreach → Clay SMS table
    linkedin_leads = []   # Instantly → Clay LinkedIn table (for manual InMail)

    sms_leads.extend(get_linkedin_recruiter_nonresponders())
    sms_leads.extend(get_heyreach_nonresponders())
    linkedin_leads.extend(get_instantly_nonresponders())

    print(f"[nonresponder] SMS targets: {len(sms_leads)} | LinkedIn InMail targets: {len(linkedin_leads)}")

    processed = 0

    # --- Route 1: LinkedIn Recruiter + Heyreach → SMS ---
    for lead in sms_leads:
        uid = (
            f"followup:{lead['source']}:"
            + (lead["linkedin_url"] or lead["name"].lower().replace(" ", "_"))
        )
        if uid in actioned:
            continue

        # Enrich via LeadMagic to get phone
        if lead["linkedin_url"] and not lead["phone"]:
            enriched      = enrich_lead(lead["name"], lead["linkedin_url"])
            lead["email"] = lead["email"] or enriched["email"]
            lead["phone"] = enriched["phone"]
            time.sleep(1)

        # Send SMS directly
        sms_sent = send_sms(lead["phone"], lead["name"])

        # Also push to Clay SMS table
        days = (datetime.now(timezone.utc) - lead["sent_at"]).days if lead.get("sent_at") else ""
        clay_sms = push_to_clay(
            getattr(config, "CLAY_SMS_WEBHOOK", ""),
            {
                "name":         lead["name"],
                "first_name":   lead["name"].split()[0] if lead["name"] else "",
                "phone":        lead.get("phone", ""),
                "email":        lead.get("email", ""),
                "linkedin_url": lead.get("linkedin_url", ""),
                "source":       lead["source"],
                "days_pending": days,
            },
        )

        if sms_sent or clay_sms:
            actioned[uid] = {
                "actioned_at": datetime.now(timezone.utc).isoformat(),
                "route":       "sms",
                "sms_sent":    sms_sent,
                "clay_sms":    clay_sms,
                "phone":       lead.get("phone", ""),
            }
            state_manager.save_state(state)
            processed += 1
            print(f"[nonresponder] SMS route: {lead['name']} ({lead['source']}) — SMS:{sms_sent} Clay:{clay_sms}")
        else:
            print(f"[nonresponder] Skipped {lead['name']} — no phone found, no Clay webhook set")

        time.sleep(0.5)

    # --- Route 2: Instantly → Clay LinkedIn table (manual InMail queue) ---
    for lead in linkedin_leads:
        uid = f"followup:instantly:{lead['email']}"
        if uid in actioned:
            continue

        # Enrich via LeadMagic by email to get LinkedIn URL
        if lead["email"] and not lead["linkedin_url"]:
            try:
                resp = requests.post(
                    f"{LEADMAGIC_URL}/email-finder",
                    headers={"X-BLOBR-KEY": LEADMAGIC_KEY, "Content-Type": "application/json"},
                    json={"email": lead["email"]},
                    timeout=20,
                )
                if resp.status_code == 200:
                    data = resp.json()
                    lead["linkedin_url"] = (data.get("linkedin_url") or "").strip()
            except Exception as e:
                print(f"[nonresponder] LeadMagic email lookup error for {lead['email']}: {e}")
            time.sleep(1)

        clay_li = push_to_clay(
            getattr(config, "CLAY_LINKEDIN_WEBHOOK", ""),
            {
                "name":         lead["name"],
                "email":        lead["email"],
                "linkedin_url": lead.get("linkedin_url", ""),
                "job_role":     lead.get("job_role", ""),
                "source":       "instantly",
                "days_pending": (datetime.now(timezone.utc) - lead["sent_at"]).days
                                if lead.get("sent_at") else "",
            },
        )

        if clay_li:
            actioned[uid] = {
                "actioned_at":  datetime.now(timezone.utc).isoformat(),
                "route":        "linkedin_inmail",
                "clay_li":      clay_li,
                "linkedin_url": lead.get("linkedin_url", ""),
            }
            state_manager.save_state(state)
            processed += 1
            print(f"[nonresponder] LinkedIn route: {lead['name']} <{lead['email']}> → Clay")
        else:
            print(f"[nonresponder] Skipped {lead['name']} — Clay LinkedIn webhook not set")

        time.sleep(0.5)

    print(f"[nonresponder] Done — {processed} lead(s) actioned.")
    return processed


if __name__ == "__main__":
    count = run()
    print(f"Non-responder pipeline finished — {count} lead(s) actioned.")
