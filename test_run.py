"""
test_run.py — Non-interactive test of the scraper pipeline
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

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import pandas as pd
from jobspy import scrape_jobs
from keyword_engine import build_keyword_plan
from sources import fetch_all_api_jobs
from relevance import filter_jobs


def main():
    # Hardcoded test inputs
    position = "Backend Developer Internship"
    description = "backend, python, node.js, django, databases"
    city = "Lahore"
    work_type = "any"

    print(f"\n{'='*60}")
    print(f"  TEST RUN: Smart Job Scraper v3.0")
    print(f"{'='*60}")
    print(f"  Position:    {position}")
    print(f"  Description: {description}")
    print(f"  City:        {city}")
    print(f"  Work type:   {work_type}")

    # Step 1: Build keyword plan
    print(f"\n[1] Building keyword plan...")
    plan = build_keyword_plan(position, description)
    print(f"  Queries ({len(plan.search_queries)}):")
    for i, q in enumerate(plan.search_queries[:10], 1):
        print(f"    {i}. {q}")
    print(f"  Must-have: {', '.join(plan.must_have[:10])}")
    print(f"  Negative:  {', '.join(plan.negative[:8])}")

    # Step 2: Scrape JobSpy
    print(f"\n[2] Scraping JobSpy (Indeed, LinkedIn, Google, Glassdoor)...")
    jobspy_jobs = []
    jobspy_queries = plan.search_queries[:3]
    sites = ["indeed", "linkedin", "google"]
    seen_urls = set()

    for i, query in enumerate(jobspy_queries):
        print(f"  > Query {i+1}/{len(jobspy_queries)}: \"{query}\"")
        try:
            df = scrape_jobs(
                site_name=sites,
                search_term=query,
                location=city,
                country_indeed="Pakistan",
                results_wanted=20,
                hours_old=48,
            )
            if df.empty:
                print(f"    (no results)")
                continue

            for _, row in df.iterrows():
                job_url = str(row.get("job_url", ""))
                if job_url in seen_urls or not job_url:
                    continue
                seen_urls.add(job_url)
                jobspy_jobs.append({
                    "site": str(row.get("site", "jobspy")),
                    "title": str(row.get("title", "")),
                    "company": str(row.get("company", "")),
                    "location": str(row.get("location", city)),
                    "date_posted": str(row.get("date_posted", "")),
                    "job_url": job_url,
                    "description": str(row.get("description", "")),
                    "is_remote": bool(row.get("is_remote", False)),
                })
            print(f"    [{len(df)} results]")
        except Exception as e:
            print(f"    [Error] {e}")

    print(f"  JobSpy total: {len(jobspy_jobs)} unique")

    # Step 3: Scrape APIs
    print(f"\n[3] Scraping free APIs...")
    api_jobs = fetch_all_api_jobs(plan.search_queries, hours_old=48)

    # Step 4: Combine
    all_jobs = jobspy_jobs + api_jobs
    seen = set()
    unique = []
    for j in all_jobs:
        url = j.get("job_url", "")
        if url and url not in seen:
            seen.add(url)
            unique.append(j)

    print(f"\n[4] Total: {len(all_jobs)} -> Deduped: {len(unique)}")

    if not unique:
        print("  No jobs found!")
        return

    # Step 5: Relevance filter
    print(f"\n[5] Relevance filtering...")
    scored = filter_jobs(unique, plan, threshold=35)

    if not scored:
        print("  No jobs passed filter!")
        return

    # Step 6: Export
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
    df = df.sort_values(by=["relevance_score", "date_posted"], ascending=[False, False]).reset_index(drop=True)

    output_file = f"{position.lower().replace(' ', '_').replace('/', '_')}_{datetime.now().strftime('%Y-%m-%d')}.csv"

    print(f"\n{'='*60}")
    print(f"  RESULTS: {len(df)} high-quality jobs")
    print(f"{'='*60}")

    source_counts = df["site"].value_counts()
    print(f"\n  By source:")
    for src, cnt in source_counts.items():
        print(f"    - {src}: {cnt}")

    print(f"\n  Top results:")
    print(df[["relevance_score", "title", "company", "site"]].head(20).to_string(index=True))

    try:
        df.to_csv(output_file, index=False, quoting=csv.QUOTE_NONNUMERIC, escapechar="\\")
        print(f"\n  Exported to: {output_file}")
    except PermissionError:
        print(f"\n  WARNING: Could not save to {output_file} (File might be open). Skipping CSV export.")


if __name__ == "__main__":
    main()
