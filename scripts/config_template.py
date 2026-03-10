# SmartState Recruitment Pipeline - Configuration Template
# Copy this file to config.py and fill in your actual values.
# NEVER commit config.py — it's in .gitignore.

# ── ClickUp ──────────────────────────────────────────────
CLICKUP_API_TOKEN = "pk_YOUR_TOKEN_HERE"
CLICKUP_WORKSPACE_ID = "14106796"

# ClickUp List IDs (Candidates lists)
CLICKUP_LISTS = {
    "Lead HTML/Markup Developer":   "901414414348",
    "Mid-Level Flutter Developer":  "901414414372",
    "Sr Front End Developer":       "901414414393",
    "Senior Backend Developer":     "901414414404",
    "Senior Manual QA Engineer":    "901414414415",
    "Senior Product Manager":       "901414414435",
    "Affiliate Manager":            "901414417420",
    "Senior Flutter Developer":     "901414417498",
}

# Custom Field IDs (shared across all lists)
CUSTOM_FIELDS = {
    "Date Contacted":    "23315184-23b5-44b7-b25e-a04ddc6ed9c0",
    "Email":             "43b5c0f0-5de1-486c-9a5d-4c3c34afd97d",
    "Campaign/Sequence": "549a80b8-22cf-4eba-9df0-d3ce52ad4bd8",
    "Notes":             "5dc608ba-565f-41e0-8063-ca5c8681ed88",
    "Interview Date":    "64ff798a-7af8-4bdf-b3b4-d762481f7da9",
    "Date Replied":      "8638fc92-086c-455a-8a72-dfc750df7233",
    "Phone":             "a340a4f0-23ae-4678-a722-604d4c81f0ff",
    "Candidate Rating":  "abc69253-4279-4e50-a9a1-75f82cc49a79",
    "Channel":           "c161752a-3a35-467d-bef6-ab76c245cceb",
    "Salary Range":      "c83313f2-2620-4894-9a3b-2ebc0b0754bf",
    "Linkedin":          "cdc5ce8e-daa9-4279-9f8b-63f325085f62",
}

# Channel Dropdown Option IDs
CHANNEL_OPTIONS = {
    "Instantly":          "f88806c4-396c-4890-a7ff-f93bac1ea00f",
    "Heyreach":           "b47a6098-b305-4dad-a20e-f16cb4fdbafb",
    "LinkedIn Recruiter": "38839ea6-f705-4fc6-abe0-e18311be12ae",
    "Inbound":            "00659e3a-4af7-4f14-9fef-06fb27079860",
}

# ── Instantly ────────────────────────────────────────────
INSTANTLY_API_KEY = "YOUR_INSTANTLY_API_KEY_HERE"

# Instantly Campaign ID → ClickUp List mapping
INSTANTLY_CAMPAIGNS = {
    "ff1fb3e5-4af1-433d-8a7f-d396eba5f0dd": "Lead HTML/Markup Developer",   # Senior HTML
    "f241305e-57d5-4812-a278-2fcf68b65f9e": "Lead HTML/Markup Developer",   # Mid HTML
    "d0da5edd-293e-4b21-8e35-ce504377362a": "Sr Front End Developer",       # Senior Front End
    "b6a30d37-091e-4ab3-ae7b-6e0674c7d764": "Senior Manual QA Engineer",    # Manual QA Postman
    "8b6cb40c-0cb1-41d1-97d1-286b04a01391": "Senior Flutter Developer",     # Senior Flutter
    "6284a72c-7927-41fe-b7ec-2e1df22e1903": "Mid-Level Flutter Developer",  # Middle Flutter
    "3cc1f7ae-c1df-4f29-afb1-ff5ff1143780": "Senior Product Manager",       # Product Owner
    "0ccefc2b-fa4d-4615-b180-4d17cf27960f": "Senior Backend Developer",     # Senior Back End
    "05f6e117-9187-421f-ad45-951300d2822f": "Affiliate Manager",            # Affiliate Manager
}

# ── Heyreach ─────────────────────────────────────────────
HEYREACH_API_KEY = "YOUR_HEYREACH_API_KEY_HERE"
HEYREACH_BASE_URL = "https://api.heyreach.io/api/public"

# Heyreach Campaign ID → ClickUp List mapping
HEYREACH_CAMPAIGNS = {
    354909: "Senior Product Manager",       # Product Manager (active)
    349645: "Mid-Level Flutter Developer",  # Mid Flutter (active)
    357063: "Senior Flutter Developer",     # Draft
    357067: "Lead HTML/Markup Developer",   # Draft
    357072: "Sr Front End Developer",       # Draft
    357074: "Senior Backend Developer",     # Draft
    357075: "Senior Manual QA Engineer",    # Draft
    357076: "Affiliate Manager",            # Draft
}
