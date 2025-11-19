# Fetch RemoteOK and persist raw JSON into Bronze (and DB).

import time
import random
from datetime import datetime
from pathlib import Path
from typing import List, Dict
import requests
from ingest_common import persist_raw

API_URL = "https://remoteok.com/api"
SOURCE = "remoteok"


def _fetch_remoteok() -> List[Dict]:
    """Fetch RemoteOK; skip the header row they include."""
    for attempt in range(3):
        try:
            r = requests.get(API_URL, timeout=15)
            r.raise_for_status()
            payload = r.json()
            if isinstance(payload, list) and len(payload) > 1:
                return [p for p in payload[1:] if isinstance(p, dict)]
            return []
        except Exception as e:
            print(f"RemoteOK fetch failed ({attempt+1}/3): {e}")
            time.sleep(1 + random.random())
    return []


def _normalize_for_debug(item: Dict) -> Dict:
    """Keep the raw shape minimal but predictable in Bronze files."""
    return {
        "id": str(item.get("id")),
        "position": item.get("position") or item.get("title"),
        "company": item.get("company"),
        "location": item.get("location"),
        "remote": True,
        "url": item.get("url") or item.get("apply_url"),
        "description": item.get("description"),
        "date": item.get("date") or item.get("created_at"),
        "salary": item.get("salary"),
        "tags": item.get("tags") or []
    }


def run():
    print("→ Fetching RemoteOK...")
    rows = _fetch_remoteok()
    if not rows:
        print("   No results from RemoteOK.")
        return

    # Optionally normalize slightly before saving so Bronze is consistent
    prepared = [_normalize_for_debug(r) for r in rows]
    r = persist_raw(prepared, SOURCE, write_db=True)
    print(f"   Saved {len(prepared)} jobs → {r['path']} (db_id={r.get('db_id')})")


if __name__ == "__main__":
    run()
