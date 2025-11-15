import requests
from ingest_common import save_raw


REMOTIVE_URL = "https://remotive.com/api/remote-jobs"


def fetch_remotive():
    """
    Fetch job listings from the Remotive API.
    The API returns a dictionary with a 'jobs' list.
    """

    headers = {"User-Agent": "job-agg-pipeline/1.0"}

    response = requests.get(REMOTIVE_URL, headers=headers)
    response.raise_for_status()

    payload = response.json()  # This is a dict with key: "jobs"

    # Save to Bronze layer
    save_raw("remotive", payload)

    return payload


if __name__ == "__main__":
    print("Fetching Remotive jobs...")
    data = fetch_remotive()

    # If payload contains jobs list
    if isinstance(data, dict) and "jobs" in data:
        print("Fetched:", len(data["jobs"]), "jobs")
    else:
        print("Fetched data successfully")
