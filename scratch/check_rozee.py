import requests
from bs4 import BeautifulSoup

def inspect_all_links():
    url = "https://www.rozee.pk/job/jsearch/q/software/c/lahore"
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    response = requests.get(url, headers=headers)
    soup = BeautifulSoup(response.text, "html.parser")
    
    print(f"Page Title: {soup.title.text if soup.title else 'No Title'}")
    
    # Save all text to see what is on the page
    text = soup.get_text()
    print("--- Word counts on the page ---")
    print(f"Total characters: {len(text)}")
    
    # Check for keywords like "No Jobs Found" or search results
    keywords = ["no jobs", "found", "lahore", "software", "intern", "developer", "results"]
    for kw in keywords:
        count = text.lower().count(kw.lower())
        print(f"Keyword '{kw}': {count} occurrences")
        
    print("\n--- Printing first 20 links found ---")
    links = soup.find_all("a", href=True)
    print(f"Total links: {len(links)}")
    for i, link in enumerate(links[:30]):
        print(f"{i}: Text: '{link.text.strip()}' | Href: '{link.get('href')}'")

if __name__ == "__main__":
    inspect_all_links()
