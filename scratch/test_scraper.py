from jobspy import scrape_jobs
import pandas as pd

def test():
    print("Testing broad search for 'software' in Pakistan, last 7 days...")
    jobs = scrape_jobs(
        site_name=["indeed", "linkedin", "google"], 
        search_term="software",
        location="Pakistan",
        hours_old=168,
        country_indeed='Pakistan',
        results_wanted=100
    )
    print(f"Scraped {len(jobs)} total jobs raw.")
    if len(jobs) == 0:
        return
        
    # Convert columns to lower for filtering
    jobs['title_lower'] = jobs['title'].str.lower()
    
    # Filter for internship-like keywords
    intern_keywords = ['intern', 'internship', 'trainee', 'fresh', 'grad', 'associate']
    is_intern = jobs['title_lower'].apply(lambda x: any(kw in str(x) for kw in intern_keywords))
    
    # Filter for Lahore or Remote
    jobs['location_lower'] = jobs['location'].str.lower()
    is_lahore_or_remote = jobs['location_lower'].apply(lambda x: 'lahore' in str(x) or 'remote' in str(x)) | jobs['is_remote']
    
    filtered_jobs = jobs[is_intern & is_lahore_or_remote]
    
    print(f"Filtered to {len(filtered_jobs)} internships in Lahore or Remote:")
    if len(filtered_jobs) > 0:
        print(filtered_jobs[['site', 'title', 'company', 'location', 'date_posted', 'is_remote']])
    else:
        print("No internships found in the filtered subset.")

if __name__ == "__main__":
    test()
