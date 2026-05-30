import requests
from bs4 import BeautifulSoup

def check_mustakbil():
    url = "https://www.mustakbil.com/jobs/search?q=software+intern"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    
    print(f"Fetching Mustakbil Pakistan: {url}")
    response = requests.get(url, headers=headers)
    print(f"Status code: {response.status_code}")
    print(f"Content length: {len(response.text)}")
    
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Save a snippet
    with open("scratch/mustakbil_snippet.html", "w", encoding="utf-8") as f:
        f.write(response.text[:20000])
        
    # Let's find all job links. Mustakbil detail links usually look like /jobs/detail/... or have class title
    job_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/jobs/details/" in href or "/job/" in href:
            job_links.append((a.text.strip(), href))
            
    print(f"Found {len(job_links)} potential job links:")
    for title, href in job_links[:15]:
        print(f"  - Title: {title} | Href: {href}")

if __name__ == "__main__":
    check_mustakbil()
