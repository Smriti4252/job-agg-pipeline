# Fetch Remotive and persist raw JSON into Bronze (and DB).

import time
import random
from pathlib import Path
from typing import List, Dict
import requests
from ingest_common import persist_raw

API_URL = "https://remotive.com/api/remote-jobs"
SOURCE = "remotive"


def _fetch_remotive() -> List[Dict]:
    for attempt in range(3):
        try:
            r = requests.get(API_URL, timeout=20)
            r.raise_for_status()
            payload = r.json()
            return payload.get("jobs", [])
        except Exception as e:
            print(f"Remotive fetch failed ({attempt+1}/3): {e}")
            time.sleep(1 + random.random())
    return []


def _normalize(job: Dict) -> Dict:
    return {
        "id": str(job.get("id")),
        "title": job.get("title"),
        "company_name": job.get("company_name"),
        "candidate_required_location": job.get("candidate_required_location"),
        "remote": True,
        "url": job.get("url"),
        "description": job.get("description"),
        "publication_date": job.get("publication_date"),
        "salary": job.get("salary"),
        "tags": job.get("tags") or []
    }


def run():
    print("→ Fetching Remotive...")
    rows = _fetch_remotive()
    if not rows:
        print("   No results from Remotive.")
        return

    prepared = [_normalize(r) for r in rows]
    r = persist_raw(prepared, SOURCE, write_db=True)
    print(f"   Saved {len(prepared)} jobs → {r['path']} (db_id={r.get('db_id')})")


if __name__ == "__main__":
    run()
