"""
SmartState Notification System — Configuration
Copy this file to config_local.py, fill in real values.
config_local.py is gitignored and should never be committed.
"""
import os

# --- Slack ---
SLACK_WEBHOOK_URL = ""  # Paste your Slack incoming webhook URL here

# --- Instantly ---
INSTANTLY_API_KEY = ""  # Your Instantly API key
INSTANTLY_BASE_URL = "https://api.instantly.ai/api/v1"

# --- Heyreach ---
HEYREACH_API_KEY = ""  # Your Heyreach API key
HEYREACH_BASE_URL = "https://api.heyreach.io/api/public"

# --- ClickUp ---
CLICKUP_API_TOKEN = ""
CLICKUP_WORKSPACE_ID = ""
CLICKUP_BASE_URL = "https://api.clickup.com/api/v2"

# Job role name -> ClickUp List ID (copy from config_template.py)
CLICKUP_LIST_IDS = {
    "HTML/Markup Developer": "",
    "Mid-Level Flutter Developer": "",
    "Senior Flutter Developer": "",
    "Senior Product Manager": "",
    "Frontend Developer": "",
    "Backend Developer": "",
    "QA Engineer": "",
    "Affiliate Manager": "",
}

# ClickUp custom field IDs
CUSTOM_FIELDS = {
    "Email": "",
    "Phone": "",
    "LinkedIn": "",
    "Channel": "",
    "Campaign/Sequence": "",
    "Notes": "",
    "Date Replied": "",
    "Date Contacted": "",
    "Candidate Rating": "",
    "Salary Range": "",
    "Interview Date": "",
}

# Heyreach campaign ID (int) -> job role name
HEYREACH_CAMPAIGN_TO_ROLE = {
    # e.g. 12345: "Senior Flutter Developer"
}

# Instantly campaign ID (str UUID) -> job role name
INSTANTLY_CAMPAIGN_TO_ROLE = {
    # e.g. "uuid-here": "Senior Flutter Developer"
}

# --- Scheduling ---
POLL_INTERVAL_MINUTES = 15       # How often to poll for new replies
HEALTH_CHECK_INTERVAL_HOURS = 6  # How often to post account health report

# --- State ---
STATE_FILE = os.path.join(os.path.dirname(__file__), "state.json")

# --- Load local overrides (config_local.py is gitignored) ---
try:
    from config_local import *  # noqa: F401, F403
except ImportError:
    try:
        from .config_local import *  # noqa: F401, F403
    except ImportError:
        pass
