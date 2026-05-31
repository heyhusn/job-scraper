"""
sources.py
----------
Unified API clients for free remote-job boards.
Each function accepts a list of search queries, fetches results,
deduplicates by URL, and returns a standardised list of dicts.

Standardised schema:
    site, title, company, location, date_posted, job_url, description, is_remote
"""

from __future__ import annotations

import re
import time
import requests
from datetime import datetime, timedelta, timezone

_SESSION = requests.Session()
_SESSION.headers.update({
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
})

TIMEOUT = 15  # seconds per request


def _within_hours(date_str: str | None, hours: int) -> bool:
    """Return True if *date_str* (YYYY-MM-DD or ISO) is within *hours* of now."""
    if not date_str:
        return True  # keep if date unknown
    try:
        # Handle both "YYYY-MM-DD" and full ISO timestamps
        clean = date_str.split("T")[0]
        dt = datetime.strptime(clean, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        cutoff = datetime.now(timezone.utc) - timedelta(hours=hours)
        return dt >= cutoff
    except (ValueError, TypeError):
        return True  # keep if unparseable


# ─────────────────────────────────────────────────────────────
# Himalayas  (https://himalayas.app)
# ─────────────────────────────────────────────────────────────

def fetch_himalayas_jobs(queries: list[str], hours_old: int = 48) -> list[dict]:
    """Fetch remote jobs from Himalayas public API."""
    seen_urls: set[str] = set()
    results: list[dict] = []

    for query in queries:
        url = f"https://himalayas.app/jobs/api/search?q={requests.utils.quote(query)}"
        try:
            resp = _SESSION.get(url, timeout=TIMEOUT)
            if resp.status_code != 200:
                continue
            data = resp.json()
            for j in data.get("jobs", []):
                pub_ts = j.get("pubDate")
                date_str = ""
                if pub_ts:
                    try:
                        date_str = datetime.fromtimestamp(pub_ts, tz=timezone.utc).strftime("%Y-%m-%d")
                    except (OSError, ValueError):
                        pass

                if not _within_hours(date_str, hours_old):
                    continue

                job_url = j.get("applicationLink") or ""
                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                locs = j.get("locationRestrictions", [])
                location_str = ", ".join(locs) if locs else "Remote (Worldwide)"

                results.append({
                    "site": "himalayas",
                    "title": j.get("title", ""),
                    "company": j.get("companyName", ""),
                    "location": location_str,
                    "date_posted": date_str,
                    "job_url": job_url,
                    "description": j.get("description", ""),
                    "is_remote": True,
                })
        except Exception:
            continue
        time.sleep(0.3)

    return results


# ─────────────────────────────────────────────────────────────
# Remotive  (https://remotive.com)
# ─────────────────────────────────────────────────────────────

def fetch_remotive_jobs(queries: list[str], hours_old: int = 48) -> list[dict]:
    """Fetch remote jobs from Remotive public API."""
    seen_urls: set[str] = set()
    results: list[dict] = []

    for query in queries:
        url = f"https://remotive.com/api/remote-jobs?search={requests.utils.quote(query)}"
        try:
            resp = _SESSION.get(url, timeout=TIMEOUT)
            if resp.status_code != 200:
                continue
            data = resp.json()
            for j in data.get("jobs", []):
                pub_date = j.get("publication_date", "")
                date_str = pub_date.split("T")[0] if pub_date else ""

                if not _within_hours(date_str, hours_old):
                    continue

                job_url = j.get("url", "")
                if job_url in seen_urls:
                    continue
                seen_urls.add(job_url)

                results.append({
                    "site": "remotive",
                    "title": j.get("title", ""),
                    "company": j.get("company_name", ""),
                    "location": j.get("candidate_required_location", "Remote (Worldwide)"),
                    "date_posted": date_str,
                    "job_url": job_url,
                    "description": j.get("description", ""),
                    "is_remote": True,
                })
        except Exception:
            continue
        time.sleep(0.3)

    return results


# ─────────────────────────────────────────────────────────────
# Arbeitnow  (https://arbeitnow.com)
# ─────────────────────────────────────────────────────────────

def fetch_arbeitnow_jobs(queries: list[str], hours_old: int = 48) -> list[dict]:
    """Fetch jobs from Arbeitnow public API."""
    seen_urls: set[str] = set()
    results: list[dict] = []

    # Arbeitnow API doesn't support search — fetch all and filter locally
    try:
        resp = _SESSION.get("https://www.arbeitnow.com/api/job-board-api", timeout=TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
        all_jobs = data.get("data", [])
    except Exception:
        return []

    query_tokens = set()
    for q in queries:
        query_tokens.update(re.findall(r"[a-z0-9]+", q.lower()))

    for j in all_jobs:
        title_lower = (j.get("title") or "").lower()
        desc_lower = (j.get("description") or "").lower()
        combined = f"{title_lower} {desc_lower}"

        # Check if any query token matches
        if not any(tok in combined for tok in query_tokens if len(tok) > 2):
            continue

        # Date filter
        created = j.get("created_at")
        date_str = ""
        if created:
            try:
                # Arbeitnow uses epoch seconds
                if isinstance(created, (int, float)):
                    dt = datetime.fromtimestamp(created, tz=timezone.utc)
                    date_str = dt.strftime("%Y-%m-%d")
                else:
                    date_str = str(created).split("T")[0]
            except (OSError, ValueError):
                pass

        if not _within_hours(date_str, hours_old):
            continue

        job_url = j.get("url", "")
        if job_url in seen_urls:
            continue
        seen_urls.add(job_url)

        remote = j.get("remote", False)
        location_str = j.get("location", "")

        results.append({
            "site": "arbeitnow",
            "title": j.get("title", ""),
            "company": j.get("company_name", ""),
            "location": location_str,
            "date_posted": date_str,
            "job_url": job_url,
            "description": j.get("description", ""),
            "is_remote": bool(remote),
        })

    return results


# ─────────────────────────────────────────────────────────────
# RemoteOK  (https://remoteok.com)
# ─────────────────────────────────────────────────────────────

def fetch_remoteok_jobs(queries: list[str], hours_old: int = 48) -> list[dict]:
    """Fetch remote jobs from RemoteOK public API."""
    seen_urls: set[str] = set()
    results: list[dict] = []

    try:
        resp = _SESSION.get("https://remoteok.com/api", timeout=TIMEOUT)
        if resp.status_code != 200:
            return []
        data = resp.json()
        # First element is metadata, skip it
        all_jobs = data[1:] if len(data) > 1 else []
    except Exception:
        return []

    query_tokens = set()
    for q in queries:
        query_tokens.update(re.findall(r"[a-z0-9]+", q.lower()))

    for j in all_jobs:
        title_lower = (j.get("position") or "").lower()
        desc_lower = (j.get("description") or "").lower()
        tags = " ".join(j.get("tags", []) or []).lower()
        combined = f"{title_lower} {desc_lower} {tags}"

        if not any(tok in combined for tok in query_tokens if len(tok) > 2):
            continue

        # Date filter — epoch timestamp
        date_str = ""
        epoch = j.get("epoch")
        if epoch:
            try:
                dt = datetime.fromtimestamp(int(epoch), tz=timezone.utc)
                date_str = dt.strftime("%Y-%m-%d")
            except (OSError, ValueError):
                pass
        else:
            date_str = (j.get("date") or "").split("T")[0]

        if not _within_hours(date_str, hours_old):
            continue

        job_url = j.get("url", "")
        if not job_url and j.get("id"):
            job_url = f"https://remoteok.com/remote-jobs/{j['id']}"
        if job_url in seen_urls:
            continue
        seen_urls.add(job_url)

        location_str = j.get("location", "Remote (Worldwide)")
        if not location_str:
            location_str = "Remote (Worldwide)"

        results.append({
            "site": "remoteok",
            "title": j.get("position", ""),
            "company": j.get("company", ""),
            "location": location_str,
            "date_posted": date_str,
            "job_url": job_url,
            "description": j.get("description", ""),
            "is_remote": True,
        })

    return results


# ─────────────────────────────────────────────────────────────
# Public helper — fetch all API sources at once
# ─────────────────────────────────────────────────────────────

def fetch_all_api_jobs(queries: list[str], hours_old: int = 48) -> list[dict]:
    """
    Query every free API source and return a combined, deduplicated list.
    """
    all_jobs: list[dict] = []
    seen_urls: set[str] = set()

    fetchers = [
        ("Himalayas", fetch_himalayas_jobs),
        ("Remotive", fetch_remotive_jobs),
        ("Arbeitnow", fetch_arbeitnow_jobs),
        ("RemoteOK", fetch_remoteok_jobs),
    ]

    for name, fn in fetchers:
        print(f"  → Querying {name}...")
        try:
            jobs = fn(queries, hours_old=hours_old)
            new = 0
            for j in jobs:
                if j["job_url"] not in seen_urls:
                    seen_urls.add(j["job_url"])
                    all_jobs.append(j)
                    new += 1
            print(f"    [{name}] {new} jobs (last {hours_old}h)")
        except Exception as e:
            print(f"    [{name}] Error: {e}")

    return all_jobs
