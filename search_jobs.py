"""
search_jobs.py — Smart Job Scraper v3.0
=======================================
Interactive multi-source job scraper with intelligent relevance filtering.

Workflow:
  1. Ask the user for: position, brief description, city, work type
  2. Generate smart search queries via keyword engine
  3. Scrape 8+ sources (JobSpy boards + 4 free APIs) — last 48 hours only
  4. Score and filter for relevance
  5. Export a clean, high-quality CSV
"""

import csv
import sys
import os
import re
import io
from datetime import datetime

# Fix Windows console encoding
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8", errors="replace")

import pandas as pd

# Add current dir to path so our modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from jobspy import scrape_jobs
from keyword_engine import build_keyword_plan
from sources import fetch_all_api_jobs
from relevance import filter_jobs


# ─────────────────────────────────────────────────────────────
# Pretty console helpers
# ─────────────────────────────────────────────────────────────

def _header(text: str):
    width = 70
    print()
    print("=" * width)
    print(f"  {text}".center(width))
    print("=" * width)


def _section(num: int, text: str):
    print(f"\n{'-'*50}")
    print(f"  [{num}] {text}")
    print(f"{'-'*50}")


# ─────────────────────────────────────────────────────────────
# User input
# ─────────────────────────────────────────────────────────────

def get_user_input() -> dict:
    """Interactively collect job search parameters from the user."""
    _header("Smart Job Scraper v3.0")
    print()

    # Position
    position = input("  [POSITION] Enter the position you're looking for:\n     > ").strip()
    if not position:
        position = "AI/ML Internship"
        print(f"     (defaulting to: {position})")
    print()

    # Brief description
    print("  [DESCRIPTION] Briefly describe the kind of role you want")
    print("     (skills, tech, domain - helps us find better matches):")
    description = input("     > ").strip()
    print()

    # City
    city = input("  [CITY] Preferred city (leave blank for any/worldwide):\n     > ").strip()
    print()

    # Work type
    print("  [WORK TYPE]")
    print("     1. Remote")
    print("     2. Onsite")
    print("     3. Hybrid")
    print("     4. Any (all types)")
    work_choice = input("     > Choose [1-4]: ").strip()
    work_type_map = {"1": "remote", "2": "onsite", "3": "hybrid", "4": "any"}
    work_type = work_type_map.get(work_choice, "any")
    print(f"     (selected: {work_type})")
    print()

    return {
        "position": position,
        "description": description,
        "city": city,
        "work_type": work_type,
    }


# ─────────────────────────────────────────────────────────────
# JobSpy scraping (Indeed, LinkedIn, Google, Glassdoor)
# ─────────────────────────────────────────────────────────────

def scrape_jobspy_boards(queries: list[str], city: str, work_type: str, hours_old: int = 48) -> list[dict]:
    """
    Scrape standard job boards via JobSpy with multiple query terms.
    Returns standardised list of job dicts.
    """
    all_results: list[dict] = []
    seen_urls: set[str] = set()

    # Determine location and country for JobSpy
    location = city if city else None
    # Detect country from city name for Indeed
    country_indeed = "Pakistan"  # default
    pk_cities = {"lahore", "karachi", "islamabad", "rawalpindi", "peshawar", "faisalabad", "multan"}
    us_cities = {"new york", "san francisco", "austin", "seattle", "chicago", "boston", "los angeles"}
    uk_cities = {"london", "manchester", "cambridge", "oxford"}
    ca_cities = {"toronto", "vancouver", "montreal", "ottawa"}

    city_lower = city.lower() if city else ""
    if city_lower in pk_cities:
        country_indeed = "Pakistan"
    elif city_lower in us_cities:
        country_indeed = "USA"
    elif city_lower in uk_cities:
        country_indeed = "UK"
    elif city_lower in ca_cities:
        country_indeed = "Canada"
    elif not city:
        country_indeed = "USA"  # broader default for remote searches

    is_remote = work_type == "remote"

    # Use top 4 most targeted queries for JobSpy (it's slower per query)
    jobspy_queries = queries[:4]
    sites = ["indeed", "linkedin", "google", "glassdoor"]

    for i, query in enumerate(jobspy_queries):
        print(f"  > JobSpy query {i+1}/{len(jobspy_queries)}: \"{query}\"")
        try:
            df = scrape_jobs(
                site_name=sites,
                search_term=query,
                location=location,
                country_indeed=country_indeed,
                is_remote=is_remote,
                results_wanted=25,
                hours_old=hours_old,
            )
            if df.empty:
                print(f"    (no results)")
                continue

            for _, row in df.iterrows():
                job_url = str(row.get("job_url", ""))
                if job_url in seen_urls or not job_url:
                    continue
                seen_urls.add(job_url)

                all_results.append({
                    "site": str(row.get("site", "jobspy")),
                    "title": str(row.get("title", "")),
                    "company": str(row.get("company", "")),
                    "location": str(row.get("location", city or "")),
                    "date_posted": str(row.get("date_posted", "")),
                    "job_url": job_url,
                    "description": str(row.get("description", "")),
                    "is_remote": bool(row.get("is_remote", False)),
                })

            print(f"    [{len(df)} raw results from boards]")
        except Exception as e:
            print(f"    [JobSpy Error] {e}")

    print(f"  > JobSpy total: {len(all_results)} unique jobs")
    return all_results


# ─────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────

def main():
    # -- Step 0: Get user input --
    user_input = get_user_input()
    position = user_input["position"]
    description = user_input["description"]
    city = user_input["city"]
    work_type = user_input["work_type"]

    # -- Step 1: Build keyword plan --
    _section(1, "Building smart search queries...")
    plan = build_keyword_plan(position, description)

    print(f"  Position:        {position}")
    print(f"  Description:     {description or '(none)'}")
    print(f"  City:            {city or 'Any / Worldwide'}")
    print(f"  Work type:       {work_type}")
    print(f"  Search queries:  {len(plan.search_queries)}")
    for i, q in enumerate(plan.search_queries[:8], 1):
        print(f"    {i}. {q}")
    if len(plan.search_queries) > 8:
        print(f"    ... +{len(plan.search_queries) - 8} more")
    print(f"  Must-have kws:   {', '.join(plan.must_have[:10])}")
    print(f"  Negative kws:    {', '.join(plan.negative[:8])}")

    # -- Step 2: Scrape job boards (JobSpy) --
    _section(2, "Scraping job boards (Indeed, LinkedIn, Google, Glassdoor)...")
    jobspy_jobs = scrape_jobspy_boards(
        queries=plan.search_queries,
        city=city,
        work_type=work_type,
        hours_old=48,
    )

    # -- Step 3: Scrape free APIs --
    _section(3, "Scraping free remote-job APIs (Himalayas, Remotive, Arbeitnow, RemoteOK)...")
    api_jobs = fetch_all_api_jobs(
        queries=plan.search_queries,
        hours_old=48,
    )

    # -- Step 4: Combine --
    _section(4, "Combining and deduplicating...")
    all_jobs = jobspy_jobs + api_jobs

    # Deduplicate by URL
    seen: set[str] = set()
    unique_jobs: list[dict] = []
    for j in all_jobs:
        url = j.get("job_url", "")
        if url and url not in seen:
            seen.add(url)
            unique_jobs.append(j)

    print(f"  Total scraped:   {len(all_jobs)}")
    print(f"  After dedup:     {len(unique_jobs)}")

    if not unique_jobs:
        print("\n  WARNING: No jobs found. Try broader search terms or different city.")
        return

    # -- Step 5: Apply work-type filter --
    if work_type == "remote":
        unique_jobs = [j for j in unique_jobs if j.get("is_remote")]
        print(f"  After remote filter: {len(unique_jobs)}")
    elif work_type == "onsite":
        unique_jobs = [j for j in unique_jobs if not j.get("is_remote")]
        print(f"  After onsite filter: {len(unique_jobs)}")

    if not unique_jobs:
        print("\n  WARNING: No jobs left after work-type filter. Try 'any' for all types.")
        return

    # -- Step 6: Relevance scoring + filtering --
    _section(5, "Scoring relevance & filtering out junk...")
    scored = filter_jobs(unique_jobs, plan, threshold=35)

    if not scored:
        print("\n  WARNING: No jobs passed the relevance filter.")
        print("  Tip: Try a broader description or different keywords.")
        return

    # -- Step 7: Build final DataFrame --
    _section(6, "Building final results...")

    rows = []
    for sj in scored:
        j = sj.job
        rows.append({
            "relevance_score": sj.score,
            "site": j.get("site", ""),
            "title": j.get("title", ""),
            "company": j.get("company", ""),
            "location": j.get("location", ""),
            "date_posted": j.get("date_posted", ""),
            "job_url": j.get("job_url", ""),
            "is_remote": j.get("is_remote", False),
        })

    df = pd.DataFrame(rows)

    # Sort by relevance score descending, then date descending
    df = df.sort_values(by=["relevance_score", "date_posted"], ascending=[False, False]).reset_index(drop=True)

    # -- Step 8: Display & Export --
    _header("RESULTS")

    # Summary per source
    source_counts = df["site"].value_counts()
    print("\n  Results by source:")
    for source, count in source_counts.items():
        print(f"     - {source}: {count}")

    # Top results preview
    print(f"\n  Top {min(20, len(df))} results:\n")
    preview_cols = ["relevance_score", "title", "company", "site"]
    print(df[preview_cols].head(20).to_string(index=True))

    # Export
    safe_position = re.sub(r"[^a-zA-Z0-9]+", "_", position).strip("_").lower()
    date_str = datetime.now().strftime("%Y-%m-%d")
    output_file = f"{safe_position}_{date_str}.csv"

    df.to_csv(output_file, index=False, quoting=csv.QUOTE_NONNUMERIC, escapechar="\\")

    print(f"\n  EXPORTED {len(df)} high-quality results to: {output_file}")
    print(f"  All results scored >= 35 relevance (out of 100)")
    print()


if __name__ == "__main__":
    main()
