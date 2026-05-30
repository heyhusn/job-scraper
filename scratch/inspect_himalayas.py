import requests
import json

def inspect_himalayas_keys():
    url = "https://himalayas.app/jobs/api/search?q=intern&limit=1"
    response = requests.get(url)
    data = response.json()
    job = data["jobs"][0] if data.get("jobs") else {}
    print("Himalayas keys:")
    print(json.dumps(job, indent=2))

if __name__ == "__main__":
    inspect_himalayas_keys()
