import requests
from bs4 import BeautifulSoup
import re

def inspect_careerjet():
    url = "https://www.careerjet.com.pk/search/jobs?s=software+intern&l=Lahore"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Save a snippet of the page
    with open("scratch/careerjet_snippet.html", "w", encoding="utf-8") as f:
        f.write(response.text[:30000])
        
    print("--- Searching for potential job elements ---")
    
    # Let's check all standard headings or lists
    # Careerjet listing usually has class 'job' on <li> elements
    li_tags = soup.find_all("li")
    print(f"Total <li> tags: {len(li_tags)}")
    for li in li_tags[:20]:
        class_list = li.get("class", [])
        if class_list:
            print(f"li class: {class_list}")
            
    # Check all links
    job_links = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        if "/job/" in href:
            job_links.append((a.text.strip(), href))
            
    print(f"Found {len(job_links)} links containing '/job/'")
    for txt, href in job_links[:10]:
        print(f"  - '{txt}': {href}")

if __name__ == "__main__":
    inspect_careerjet()
