import csv
import requests
import pandas as pd
from datetime import datetime
from jobspy import scrape_jobs

# -------------------------------------------------------------
# HELPER FUNCTIONS TO SCRAPE TOTALLY FREE, HIGH-QUALITY APIs
# -------------------------------------------------------------

def fetch_himalayas_jobs(query):
    """
    Fetches remote jobs from Himalayas (a completely free, no-key public API)
    """
    url = f"https://himalayas.app/jobs/api/search?q={query}"
    print(f"-> Querying Himalayas API for '{query}'...")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            jobs = data.get("jobs", [])
            parsed_jobs = []
            for j in jobs:
                # Parse pubDate (epoch to YYYY-MM-DD)
                pub_date = datetime.fromtimestamp(j["pubDate"]).strftime("%Y-%m-%d") if j.get("pubDate") else ""
                
                # Check location restrictions (to ensure it's open globally or to Pakistan/Worldwide)
                locs = j.get("locationRestrictions", [])
                location_str = ", ".join(locs) if locs else "Remote (Worldwide)"
                
                # Filter out jobs that specifically block international candidates if necessary
                # If they say Remote (Worldwide) or allow Pakistan/Asia
                parsed_jobs.append({
                    "site": "himalayas",
                    "title": j.get("title"),
                    "company": j.get("companyName"),
                    "location": location_str,
                    "date_posted": pub_date,
                    "job_url": j.get("applicationLink"),
                    "is_remote": True
                })
            print(f"   [Himalayas] Found {len(parsed_jobs)} remote jobs.")
            return parsed_jobs
    except Exception as e:
        print(f"   [Himalayas Error] Could not fetch: {e}")
    return []

def fetch_remotive_jobs(query):
    """
    Fetches remote jobs from Remotive (a completely free, no-key public API)
    """
    url = f"https://remotive.com/api/remote-jobs?search={query}"
    print(f"-> Querying Remotive API for '{query}'...")
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()
            jobs = data.get("jobs", [])
            parsed_jobs = []
            for j in jobs:
                pub_date = j.get("publication_date", "").split("T")[0] if "publication_date" in j else ""
                location_str = j.get("candidate_required_location", "Remote (Worldwide)")
                
                parsed_jobs.append({
                    "site": "remotive",
                    "title": j.get("title"),
                    "company": j.get("company_name"),
                    "location": location_str,
                    "date_posted": pub_date,
                    "job_url": j.get("url"),
                    "is_remote": True
                })
            print(f"   [Remotive] Found {len(parsed_jobs)} remote jobs.")
            return parsed_jobs
    except Exception as e:
        print(f"   [Remotive Error] Could not fetch: {e}")
    return []

# -------------------------------------------------------------
# MAIN MULTI-SOURCE SCRAPER EXECUTION
# -------------------------------------------------------------

def main():
    print("=========================================================================")
    print("            Pakistan & Remote AI/ML Job Scraper v2.0 (Multi-API)        ")
    print("=========================================================================")
    
    # Define local job board scrape criteria
    local_search_term = '("AI" OR "ML" OR "Machine Learning" OR "Artificial Intelligence") intern'
    location = "Lahore"
    
    # 1. Scrape standard job boards via JobSpy (Indeed, LinkedIn, Google)
    print(f"\n1. Scraping local job boards (Indeed, LinkedIn, Google) for: {local_search_term} in {location}...")
    try:
        local_jobs_df = scrape_jobs(
            site_name=["indeed", "linkedin", "google"], 
            search_term=local_search_term,
            location=location,
            country_indeed='Pakistan',
            results_wanted=30
        )
        print(f"   Local boards returned {len(local_jobs_df)} raw results.")
    except Exception as e:
        print(f"   [Local Scraper Error] {e}")
        local_jobs_df = pd.DataFrame()

    # Normalize local scraper columns to match our standard format
    local_jobs_list = []
    if not local_jobs_df.empty:
        # Standardize indeed/linkedin/google columns
        # Map: site_name -> site, company_name -> company, location -> location, date_posted -> date_posted, job_url -> job_url
        for _, row in local_jobs_df.iterrows():
            local_jobs_list.append({
                "site": str(row.get("site", "scraper")),
                "title": str(row.get("title", "")),
                "company": str(row.get("company", "")),
                "location": str(row.get("location", "Lahore, Pakistan")),
                "date_posted": str(row.get("date_posted", "")),
                "job_url": str(row.get("job_url", "")),
                "is_remote": bool(row.get("is_remote", False))
            })

    # 2. Query Free Remote Job APIs (Himalayas & Remotive) specifically for AI/ML/Software Internships
    print("\n2. Fetching from Free Public Remote Job APIs (Himalayas & Remotive)...")
    api_jobs = []
    
    # Query for AI and ML internships
    api_jobs += fetch_himalayas_jobs("AI intern")
    api_jobs += fetch_himalayas_jobs("machine learning intern")
    api_jobs += fetch_remotive_jobs("AI intern")
    api_jobs += fetch_remotive_jobs("machine learning intern")
    
    # 3. Combine and filter all jobs
    print("\n3. Combining and filtering all listings...")
    all_jobs = local_jobs_list + api_jobs
    
    if not all_jobs:
        print("No jobs found across any platform or API.")
        return
        
    df = pd.DataFrame(all_jobs)
    
    # Deduplicate by URL
    df = df.drop_duplicates(subset=["job_url"])
    
    # Convert title to lowercase for robust pandas filtering
    df['title_lower'] = df['title'].str.lower()
    
    # Filter for AI/ML keywords AND Internship keywords to ensure high relevance
    ai_keywords = ['ai', 'ml', 'machine learning', 'artificial intelligence', 'data science', 'deep learning', 'nlp', 'computer vision']
    intern_keywords = ['intern', 'internship', 'trainee', 'fresh', 'student', 'co-op']
    
    is_ai = df['title_lower'].apply(lambda x: any(kw in str(x) for kw in ai_keywords))
    is_intern = df['title_lower'].apply(lambda x: any(kw in str(x) for kw in intern_keywords))
    
    # Filter: Keep if it matches both AI/ML AND is an Internship
    final_df = df[is_ai & is_intern].copy()
    
    # Remove our temporary lowercase column
    final_df = final_df.drop(columns=['title_lower'])
    
    print(f"\n=========================================================================")
    print(f"   SCRAPING COMPLETED: Surfaced {len(final_df)} highly relevant AI Internships!")
    print(f"=========================================================================")
    
    if not final_df.empty:
        # Sort by date posted (newest first)
        final_df = final_df.sort_values(by="date_posted", ascending=False)
        
        # Preview Results
        print(final_df[['site', 'title', 'company', 'location', 'date_posted']].head(20))
        
        # Save to unified CSV file
        output_file = "ai_internships_lahore.csv"
        final_df.to_csv(output_file, index=False, quoting=csv.QUOTE_NONNUMERIC, escapechar="\\")
        print(f"\n[SUCCESS] Exported all {len(final_df)} clean listings to: {output_file}")
    else:
        print("No strict AI/ML internships were found in this run.")
        print("Tip: You can expand your configuration in search_jobs.py to include wider tech terms.")

if __name__ == "__main__":
    main()
