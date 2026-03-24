#!/usr/bin/env python3
"""
Sync LinkedIn Recruiter candidates into SmartState Supabase.

Flow:
1. Reuse an existing Chrome tab with LinkedIn Talent open via the local CDP helper.
2. Open each configured Recruiter project's manage/all page and fetch candidate IDs from the
   Recruiter search API that page already calls.
3. Skip candidates already stored in candidate_sources for channel=linkedin_recruiter.
4. For each new candidate, open their Recruiter profile, fetch the exact profile/activity API
   URLs Chrome already requested, and extract:
   - public linkedin.com/in URL
   - full name
   - first outbound InMail timestamp
   - latest outbound InMail state
5. Insert or attach the candidate in Supabase and write a candidate_sources row with the
   Recruiter profile URL as source_lead_id.

The script is intentionally light on dependencies:
- uses requests for Supabase REST
- uses the existing node-based cdp.mjs helper for authenticated LinkedIn fetches

Environment:
- SUPABASE_SERVICE_ROLE_KEY is required for live runs
- SUPABASE_URL defaults to the SmartState project if omitted
- .env / .env.local in the repo root are loaded automatically before env lookup
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional
from urllib.parse import urlsplit

import requests


DEFAULT_SUPABASE_URL = "https://uckcplhvjtxnkyxhccxr.supabase.co"
DEFAULT_CDP_SCRIPT = Path.home() / ".claude/skills/chrome-cdp/scripts/cdp.mjs"

# The Recruiter projects currently used for SmartState.
# The Flutter Recruiter project has historically been treated as a mixed pool and routed to the
# senior role by default. Adjust here if the project should land in the mid-level role instead.
DEFAULT_PROJECTS = {
    1661933460: {
        "project_name": "SmartState Product Manager",
        "job_title": "Senior Product Manager",
    },
    1661750948: {
        "project_name": "Flutter",
        "job_title": "Senior Flutter Developer",
    },
    1440335625: {
        "project_name": "HTML CSS Lead",
        "job_title": "Lead HTML/Markup Developer",
    },
}

ACTIVITY_QUERY_ID = "talentRecruitingActivityItems.d61a4b60146b6fb7d0cf6aa1a5c361ae"


@dataclass
class RecruiterProject:
    project_id: int
    project_name: str
    job_title: str


@dataclass
class SearchCandidate:
    project_id: int
    member_id: str
    candidate_id: str

    @property
    def source_lead_id(self) -> str:
        return f"https://www.linkedin.com/talent/profile/{self.member_id}?project={self.project_id}"

    @property
    def recruiter_profile_url(self) -> str:
        return self.source_lead_id


@dataclass
class CandidateProfile:
    full_name: str
    public_profile_url: str
    first_message_at_ms: int
    last_message_at_ms: int
    latest_message_state: str
    total_inmail_messages: int

    @property
    def is_pending(self) -> bool:
        return self.latest_message_state == "PENDING"


class SyncError(RuntimeError):
    pass


def load_env_file(path: Path) -> None:
    if not path.exists():
        return
    for raw_line in path.read_text().splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'").strip('"')
        if key and key not in os.environ:
            os.environ[key] = value


def load_repo_env() -> Path:
    repo_root = Path(__file__).resolve().parents[2]
    for name in (".env", ".env.local"):
        load_env_file(repo_root / name)
    return repo_root


def utc_iso_from_ms(timestamp_ms: int) -> str:
    dt = datetime.fromtimestamp(timestamp_ms / 1000, tz=timezone.utc)
    return dt.isoformat().replace("+00:00", "Z")


def normalize_public_profile_url(url: str) -> str:
    if not url:
        return ""
    parsed = urlsplit(url.strip())
    path = parsed.path.rstrip("/")
    if not path:
        return ""
    return f"https://www.linkedin.com{path}"


def parse_member_id(value: str) -> str:
    match = re.search(r"urn:li:ts_profile:([^,)]+)", value or "")
    return match.group(1) if match else ""


def parse_candidate_id(value: str) -> str:
    match = re.search(r"urn:li:ts_hire_identity:(\d+)", value or "")
    return match.group(1) if match else ""


def looks_like_placeholder_name(name: str) -> bool:
    value = (name or "").strip()
    return bool(value) and (" " not in value or re.fullmatch(r"[a-z0-9._-]+", value.lower()) is not None)


class SupabaseRest:
    def __init__(self, base_url: str, service_role_key: str) -> None:
        self.base_url = base_url.rstrip("/")
        self.rest_url = f"{self.base_url}/rest/v1"
        self.headers = {
            "apikey": service_role_key,
            "Authorization": f"Bearer {service_role_key}",
            "Content-Type": "application/json",
        }

    def _request(self, method: str, table: str, *, params: Optional[dict] = None, payload=None, prefer: str = ""):
        headers = dict(self.headers)
        if prefer:
            headers["Prefer"] = prefer
        response = requests.request(
            method,
            f"{self.rest_url}/{table}",
            headers=headers,
            params=params,
            json=payload,
            timeout=30,
        )
        if response.status_code >= 400:
            raise SyncError(f"Supabase {method} {table} failed: {response.status_code} {response.text[:400]}")
        if not response.text:
            return []
        try:
            return response.json()
        except Exception as exc:
            raise SyncError(f"Supabase {method} {table} returned non-JSON: {exc}") from exc

    def select(self, table: str, *, params: dict) -> list:
        return self._request("GET", table, params=params)

    def insert(self, table: str, payload: dict) -> list:
        return self._request("POST", table, payload=payload, prefer="return=representation")

    def update(self, table: str, *, params: dict, payload: dict) -> list:
        return self._request("PATCH", table, params=params, payload=payload, prefer="return=representation")

    def fetch_jobs(self) -> Dict[str, str]:
        rows = self.select("jobs", params={"select": "id,title", "limit": "200"})
        return {row["title"]: row["id"] for row in rows if row.get("title") and row.get("id")}

    def fetch_all_recruiter_sources(self) -> Dict[str, str]:
        offset = 0
        limit = 500
        seen: Dict[str, str] = {}
        while True:
            rows = self.select(
                "candidate_sources",
                params={
                    "select": "candidate_id,source_lead_id",
                    "channel": "eq.linkedin_recruiter",
                    "limit": str(limit),
                    "offset": str(offset),
                },
            )
            if not rows:
                break
            for row in rows:
                source_lead_id = row.get("source_lead_id")
                candidate_id = row.get("candidate_id")
                if source_lead_id and candidate_id:
                    seen[source_lead_id] = candidate_id
            if len(rows) < limit:
                break
            offset += limit
        return seen

    def find_candidate(self, *, job_id: str, public_profile_url: str) -> Optional[dict]:
        rows = self.select(
            "candidates",
            params={
                "select": "id,name,status,date_contacted,linkedin_url",
                "job_id": f"eq.{job_id}",
                "linkedin_url": f"eq.{public_profile_url}",
                "limit": "1",
            },
        )
        return rows[0] if rows else None


class ChromeRecruiterClient:
    def __init__(self, cdp_script: Path, verbose: bool = False) -> None:
        self.cdp_script = cdp_script
        self.verbose = verbose

    def _run(self, args: List[str], *, timeout: int = 90) -> str:
        cmd = ["node", str(self.cdp_script), *args]
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        if result.returncode != 0:
            stderr = (result.stderr or "").strip()
            stdout = (result.stdout or "").strip()
            raise SyncError(stderr or stdout or f"CDP command failed: {' '.join(args)}")
        return (result.stdout or "").strip()

    def list_pages(self) -> str:
        return self._run(["list"], timeout=20)

    def find_recruiter_target(self) -> str:
        listing = self.list_pages()
        for line in listing.splitlines():
            if "linkedin.com/talent" in line or "LinkedIn Talent" in line:
                return line.strip().split()[0]
        raise SyncError("No LinkedIn Talent tab found. Open Recruiter in Chrome first.")

    def eval(self, target: str, expression: str, *, timeout: int = 90) -> str:
        return self._run(["eval", target, expression], timeout=timeout)

    def eval_json(self, target: str, expression: str, *, timeout: int = 90):
        raw = self.eval(target, expression, timeout=timeout)
        if not raw:
            raise SyncError("CDP eval returned no output")
        try:
            return json.loads(raw)
        except Exception as exc:
            raise SyncError(f"Failed to parse CDP JSON: {raw[:400]}") from exc

    def navigate(self, target: str, url: str) -> None:
        if self.verbose:
            print(f"[cdp] navigate -> {url}")
        self._run(["nav", target, url], timeout=120)

    def wait_for_truthy(self, target: str, expression: str, *, timeout_s: float = 12.0, interval_s: float = 0.5) -> None:
        deadline = time.time() + timeout_s
        while time.time() < deadline:
            try:
                if self.eval(target, expression, timeout=30) == "true":
                    return
            except SyncError:
                pass
            time.sleep(interval_s)
        raise SyncError(f"Timed out waiting for page state: {expression[:120]}")

    def current_url(self, target: str) -> str:
        return self.eval(target, "window.location.href", timeout=15)

    def fetch_project_candidates(self, target: str, project: RecruiterProject) -> List[SearchCandidate]:
        manage_url = f"https://www.linkedin.com/talent/hire/{project.project_id}/manage/all"
        self.navigate(target, manage_url)
        self.wait_for_truthy(
            target,
            f"""
            (() => {{
              const urls = performance.getEntriesByType("resource").map((entry) => entry.name);
              return urls.some((url) =>
                url.includes("talent/search/api/talentRecruiterSearchHits") &&
                url.includes("{project.project_id}")
              );
            }})()
            """.strip(),
        )

        payload = self.eval_json(
            target,
            f"""
            (async () => {{
              const projectId = {project.project_id};
              const urls = performance.getEntriesByType("resource").map((entry) => entry.name);
              const candidates = urls
                .filter((url) =>
                  url.includes("talent/search/api/talentRecruiterSearchHits") &&
                  url.includes(String(projectId))
                )
                .sort((left, right) => right.length - left.length);
              const rawUrl = candidates[0] || null;
              if (!rawUrl) return {{ error: "search_url_not_found" }};
              const baseUrl = rawUrl
                .replace(/decoration=[^&]+&/, "")
                .replace(/count=\\d+/, "count=100");

              const jsession = (document.cookie.match(/JSESSIONID="([^"]+)"/) || [])[1];
              const headers = {{
                "csrf-token": jsession,
                "x-restli-protocol-version": "2.0.0",
              }};

              let start = 0;
              const count = 100;
              let total = null;
              const items = [];

              while (true) {{
                const pageUrl = baseUrl
                  .replace(/([?&])start=\\d+/, `$1start=${{start}}`)
                  .replace(/([?&])count=\\d+/, `$1count=${{count}}`);
                const response = await fetch(pageUrl, {{ credentials: "include", headers }});
                const data = await response.json();
                const elements = data.elements || [];

                for (const element of elements) {{
                  items.push({{
                    candidate: element.candidate || "",
                    memberProfileUrn: element.memberProfileUrn || element.memberProfile || "",
                  }});
                }}

                total = data.paging?.total ?? data.metadata?.total ?? total ?? items.length;
                if (!elements.length || items.length >= total) break;
                start += count;
              }}

              return {{ total, items }};
            }})()
            """.strip(),
            timeout=120,
        )

        if payload.get("error"):
            raise SyncError(f"Project {project.project_name}: {payload['error']}")

        unique: Dict[str, SearchCandidate] = {}
        for item in payload.get("items", []):
            member_id = parse_member_id(item.get("memberProfileUrn", ""))
            candidate_id = parse_candidate_id(item.get("candidate", ""))
            if not member_id or not candidate_id:
                continue
            key = f"{project.project_id}:{member_id}"
            unique[key] = SearchCandidate(
                project_id=project.project_id,
                member_id=member_id,
                candidate_id=candidate_id,
            )

        return list(unique.values())

    def fetch_candidate_profile(self, target: str, candidate: SearchCandidate) -> CandidateProfile:
        self.navigate(target, candidate.recruiter_profile_url)
        self.wait_for_truthy(
            target,
            f"""
            (() => {{
              const urls = performance.getEntriesByType("resource").map((entry) => entry.name);
              const hasProfile = urls.some((url) =>
                url.includes("talentLinkedInMemberProfiles") &&
                url.includes("{candidate.member_id}") &&
                url.includes("publicProfileUrl")
              );
              const hasActivity = urls.some((url) =>
                url.includes("queryId={ACTIVITY_QUERY_ID}")
              );
              return hasProfile && hasActivity;
            }})()
            """.strip(),
        )

        payload = self.eval_json(
            target,
            f"""
            (async () => {{
              const memberId = "{candidate.member_id}";
              const jsession = (document.cookie.match(/JSESSIONID="([^"]+)"/) || [])[1];
              const headers = {{
                "csrf-token": jsession,
                "x-restli-protocol-version": "2.0.0",
              }};

              const urls = performance.getEntriesByType("resource").map((entry) => entry.name);
              const profileUrl = urls.find((url) =>
                url.includes("talentLinkedInMemberProfiles") &&
                url.includes(memberId) &&
                url.includes("publicProfileUrl")
              );

              let activityUrl = urls.find((url) =>
                url.includes("queryId={ACTIVITY_QUERY_ID}")
              );

              if (!profileUrl || !activityUrl) {{
                return {{
                  error: "profile_resources_not_found",
                  profileUrlFound: !!profileUrl,
                  activityUrlFound: !!activityUrl,
                }};
              }}

              activityUrl = activityUrl.replace("count%3A4", "count%3A20");

              const [profileResp, activityResp] = await Promise.all([
                fetch(profileUrl, {{ credentials: "include", headers }}),
                fetch(activityUrl, {{ credentials: "include", headers }}),
              ]);

              const [profile, activity] = await Promise.all([
                profileResp.json(),
                activityResp.json(),
              ]);

              const activityItems = activity?.data?.recruitingActivityItemsByCandidate?.elements || [];
              const messages = activityItems
                .filter((item) => item?.activityItem?.message?.contactType === "INMAIL")
                .sort((left, right) => (left.created?.time || 0) - (right.created?.time || 0));

              const latest = messages[messages.length - 1] || null;
              const first = messages[0] || null;

              const firstName = profile.unobfuscatedFirstName || profile.firstName || "";
              const lastName = profile.unobfuscatedLastName || profile.lastName || "";
              const fullName = [firstName, lastName].filter(Boolean).join(" ").trim();

              return {{
                full_name: fullName,
                public_profile_url: profile.publicProfileUrl || "",
                first_message_at_ms: first?.created?.time || null,
                last_message_at_ms: latest?.created?.time || null,
                latest_message_state: latest?.activityItem?.message?.messageState || "",
                total_inmail_messages: messages.length,
              }};
            }})()
            """.strip(),
            timeout=120,
        )

        if payload.get("error"):
            raise SyncError(f"{candidate.member_id}: {payload['error']}")

        public_profile_url = normalize_public_profile_url(payload.get("public_profile_url", ""))
        full_name = (payload.get("full_name") or "").strip()
        first_message_at_ms = payload.get("first_message_at_ms")
        last_message_at_ms = payload.get("last_message_at_ms")
        latest_message_state = (payload.get("latest_message_state") or "").strip()
        total_inmail_messages = int(payload.get("total_inmail_messages") or 0)

        if not public_profile_url:
            raise SyncError(f"{candidate.member_id}: missing public profile URL")
        if not full_name:
            raise SyncError(f"{candidate.member_id}: missing candidate name")
        if not first_message_at_ms or not last_message_at_ms:
            raise SyncError(f"{candidate.member_id}: no recruiter InMail activity found")

        return CandidateProfile(
            full_name=full_name,
            public_profile_url=public_profile_url,
            first_message_at_ms=int(first_message_at_ms),
            last_message_at_ms=int(last_message_at_ms),
            latest_message_state=latest_message_state,
            total_inmail_messages=total_inmail_messages,
        )


def resolve_projects(selected_project_ids: Iterable[int]) -> List[RecruiterProject]:
    selected = set(selected_project_ids)
    projects: List[RecruiterProject] = []
    for project_id, config in DEFAULT_PROJECTS.items():
        if selected and project_id not in selected:
            continue
        projects.append(
            RecruiterProject(
                project_id=project_id,
                project_name=config["project_name"],
                job_title=config["job_title"],
            )
        )
    if not projects:
        raise SyncError("No Recruiter projects selected")
    return projects


def attach_or_create_candidate(
    db: SupabaseRest,
    *,
    job_id: str,
    search_candidate: SearchCandidate,
    profile: CandidateProfile,
    source_index: Dict[str, str],
    verbose: bool = False,
) -> str:
    existing = db.find_candidate(job_id=job_id, public_profile_url=profile.public_profile_url)
    if existing:
        candidate_id = existing["id"]
        patch: Dict[str, str] = {}
        if looks_like_placeholder_name(existing.get("name", "")) and not looks_like_placeholder_name(profile.full_name):
            patch["name"] = profile.full_name
        if not existing.get("linkedin_url"):
            patch["linkedin_url"] = profile.public_profile_url
        if not existing.get("date_contacted"):
            patch["date_contacted"] = utc_iso_from_ms(profile.first_message_at_ms)
        if not existing.get("status"):
            patch["status"] = "outreach sent"
        if patch:
            db.update("candidates", params={"id": f"eq.{candidate_id}"}, payload=patch)
        action = "attached"
    else:
        rows = db.insert(
            "candidates",
            {
                "name": profile.full_name,
                "linkedin_url": profile.public_profile_url,
                "job_id": job_id,
                "status": "outreach sent",
                "date_contacted": utc_iso_from_ms(profile.first_message_at_ms),
            },
        )
        if not rows or not rows[0].get("id"):
            raise SyncError(f"Failed to insert candidate for {profile.full_name}")
        candidate_id = rows[0]["id"]
        action = "created"

    db.insert(
        "candidate_sources",
        {
            "candidate_id": candidate_id,
            "channel": "linkedin_recruiter",
            "source_lead_id": search_candidate.source_lead_id,
        },
    )
    source_index[search_candidate.source_lead_id] = candidate_id

    if verbose:
        print(f"[supabase] {action}: {profile.full_name} -> {candidate_id}")
    return candidate_id


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync LinkedIn Recruiter candidates into SmartState Supabase.")
    parser.add_argument(
        "--project-id",
        dest="project_ids",
        type=int,
        action="append",
        help="Only sync the given Recruiter project ID. Repeat to include multiple projects.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=0,
        help="Limit how many new candidates to inspect per project. Useful for testing.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Scrape and print what would be inserted, but do not call Supabase.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print extra progress details.",
    )
    parser.add_argument(
        "--cdp-script",
        default=str(DEFAULT_CDP_SCRIPT),
        help="Path to the local cdp.mjs helper.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = load_repo_env()
    projects = resolve_projects(args.project_ids or [])
    cdp_script = Path(args.cdp_script).expanduser()

    if not cdp_script.exists():
        raise SyncError(f"CDP helper not found at {cdp_script}")

    base_url = os.environ.get("SUPABASE_URL", DEFAULT_SUPABASE_URL)
    service_role_key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY", "")

    db: Optional[SupabaseRest] = None
    source_index: Dict[str, str] = {}
    job_ids: Dict[str, str] = {}

    if not args.dry_run:
        if not service_role_key:
            raise SyncError(
                "SUPABASE_SERVICE_ROLE_KEY is required for live runs. "
                f"Set it in the environment or in {repo_root / '.env'}."
            )
        db = SupabaseRest(base_url, service_role_key)
        source_index = db.fetch_all_recruiter_sources()
        job_ids = db.fetch_jobs()

        missing_jobs = [project.job_title for project in projects if project.job_title not in job_ids]
        if missing_jobs:
            raise SyncError(f"Jobs not found in Supabase: {', '.join(sorted(missing_jobs))}")

    chrome = ChromeRecruiterClient(cdp_script=cdp_script, verbose=args.verbose)
    target = chrome.find_recruiter_target()
    original_url = chrome.current_url(target)

    summary = {
        "created_or_attached": 0,
        "skipped_existing": 0,
        "skipped_not_pending": 0,
        "skipped_missing_activity": 0,
        "errors": 0,
    }

    try:
        for project in projects:
            print(f"\n== {project.project_name} ({project.project_id}) ==")
            candidates = chrome.fetch_project_candidates(target, project)
            print(f"found {len(candidates)} project candidates")

            unseen = [
                candidate
                for candidate in candidates
                if candidate.source_lead_id not in source_index
            ]

            if args.limit > 0:
                unseen = unseen[: args.limit]

            if not unseen:
                print("no new recruiter candidates to inspect")
                continue

            print(f"inspecting {len(unseen)} new candidate(s)")
            for index, candidate in enumerate(unseen, start=1):
                try:
                    profile = chrome.fetch_candidate_profile(target, candidate)
                except SyncError as exc:
                    summary["errors"] += 1
                    summary["skipped_missing_activity"] += 1
                    print(f"[skip] {candidate.member_id}: {exc}")
                    continue

                if not profile.is_pending:
                    summary["skipped_not_pending"] += 1
                    print(
                        f"[skip] {profile.full_name}: latest InMail state is "
                        f"{profile.latest_message_state or 'unknown'}"
                    )
                    continue

                contact_iso = utc_iso_from_ms(profile.first_message_at_ms)
                print(
                    f"[{index}/{len(unseen)}] {profile.full_name} "
                    f"-> {profile.public_profile_url} "
                    f"(contacted {contact_iso})"
                )

                if args.dry_run:
                    continue

                assert db is not None
                assert project.job_title in job_ids
                attach_or_create_candidate(
                    db,
                    job_id=job_ids[project.job_title],
                    search_candidate=candidate,
                    profile=profile,
                    source_index=source_index,
                    verbose=args.verbose,
                )
                summary["created_or_attached"] += 1
                time.sleep(0.2)
    finally:
        try:
            chrome.navigate(target, original_url)
        except Exception:
            pass

    print("\n== Summary ==")
    for key, value in summary.items():
        print(f"{key}: {value}")
    return 0 if summary["errors"] == 0 else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SyncError as exc:
        print(f"error: {exc}", file=sys.stderr)
        raise SystemExit(1)
