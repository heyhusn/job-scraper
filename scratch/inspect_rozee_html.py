import requests
from bs4 import BeautifulSoup
import json

def inspect():
    url = "https://www.rozee.pk/job/jsearch/q/software/c/lahore"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    
    # Let's inspect all <a> tags on the page and save details to a json file to avoid encoding crashes
    all_links = []
    for a in soup.find_all("a", href=True):
        all_links.append({
            "text": a.get_text(strip=True),
            "href": a["href"]
        })
        
    with open("scratch/rozee_links.json", "w", encoding="utf-8") as f:
        json.dump(all_links, f, indent=4)
        
    print(f"Total links dumped: {len(all_links)}")
    
    # Check for links containing 'job' or specific patterns
    matched_links = [l for l in all_links if "job" in l["href"].lower()]
    print(f"Total links with 'job' in URL: {len(matched_links)}")
    for l in matched_links[:20]:
        # Clean print for ascii console
        text_clean = l["text"].encode("ascii", "ignore").decode("ascii")
        print(f"- Title: {text_clean} | Href: {l['href']}")

if __name__ == "__main__":
    inspect()
