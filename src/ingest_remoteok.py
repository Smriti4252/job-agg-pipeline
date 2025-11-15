import requests
from ingest_common import save_raw


REMOTEOK_URL = "https://remoteok.com/api"


def fetch_remoteok():
    """
    Fetch job listings from RemoteOK API.
    The API returns a list; sometimes the first entry contains metadata.
    """
    headers = {"User-Agent": "job-agg-pipeline/1.0"}

    response = requests.get(REMOTEOK_URL, headers=headers)
    response.raise_for_status()

    payload = response.json()

    # Save the raw JSON into Bronze
    save_raw("remoteok", payload)

    return payload


if __name__ == "__main__":
    print("Fetching RemoteOK jobs...")
    data = fetch_remoteok()
    print("Fetched:", len(data), "items")
