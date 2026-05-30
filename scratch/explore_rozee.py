import requests
from bs4 import BeautifulSoup
import re

def explore():
    url = "https://www.rozee.pk/job/jsearch/q/software/c/lahore"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    
    print("--- Searching for potential job container divs ---")
    
    # Let's search for divs with classes containing 'job' or 'jbox' or similar
    for div in soup.find_all("div", class_=True):
        classes = div.get("class", [])
        classes_str = " ".join(classes)
        if any(keyword in classes_str.lower() for keyword in ["job", "jbox", "jlist", "listing"]):
            # Check if this div contains a link to a job detail
            a_tags = div.find_all("a", href=True)
            job_links = [a.get("href") for a in a_tags if "/job/detail/" in a.get("href")]
            if job_links:
                print(f"Div classes: {classes} | Contained job links: {job_links[:2]}")
                # Print a bit of text from the div
                print(f"  Text preview: {div.get_text(strip=True)[:150]}")
                print("-" * 50)
                
    # Also let's just find all a tags that contain '/job/detail/'
    print("\n--- Finding all direct job detail links ---")
    detail_links = soup.find_all("a", href=lambda href: href and "/job/detail/" in href)
    print(f"Found {len(detail_links)} detail links")
    for link in detail_links[:10]:
        title = link.get_text(strip=True)
        href = link.get("href")
        print(f"Link Text: {title} | Href: {href}")

if __name__ == "__main__":
    explore()
