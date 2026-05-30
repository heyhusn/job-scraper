import requests

def test_himalayas():
    url = "https://himalayas.app/jobs/api/search?q=intern"
    print(f"Fetching Himalayas API: {url}")
    try:
        response = requests.get(url, timeout=10)
        print(f"Himalayas Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            jobs = data.get("jobs", [])
            print(f"Himalayas returned {len(jobs)} jobs.")
            for i, job in enumerate(jobs[:3]):
                print(f"  {i+1}. Title: {job.get('title')} | Company: {job.get('company', {}).get('name')} | URL: {job.get('applicationLink')}")
    except Exception as e:
        print(f"Himalayas error: {e}")

def test_remotive():
    url = "https://remotive.com/api/remote-jobs?search=intern"
    print(f"\nFetching Remotive API: {url}")
    try:
        response = requests.get(url, timeout=10)
        print(f"Remotive Status: {response.status_code}")
        if response.status_code == 200:
            data = response.json()
            jobs = data.get("jobs", [])
            print(f"Remotive returned {len(jobs)} jobs.")
            for i, job in enumerate(jobs[:3]):
                print(f"  {i+1}. Title: {job.get('title')} | Company: {job.get('company_name')} | URL: {job.get('url')}")
    except Exception as e:
        print(f"Remotive error: {e}")

if __name__ == "__main__":
    test_himalayas()
    test_remotive()
