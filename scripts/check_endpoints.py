#!/usr/bin/env python3
import sys
import time
import requests

BASE = "http://127.0.0.1:8002"


def check_health():
    r = requests.get(f"{BASE}/health", timeout=5)
    if r.status_code != 200:
        raise RuntimeError(f"Health endpoint returned {r.status_code}")
    data = r.json()
    if data.get("status") != "ok":
        raise RuntimeError(f"Unexpected health payload: {data}")


def check_search(q="amil"):
    r = requests.get(f"{BASE}/search", params={"query": q}, timeout=10)
    if r.status_code != 200:
        raise RuntimeError(f"Search endpoint returned {r.status_code}")
    data = r.json()
    if not isinstance(data.get("results"), list):
        raise RuntimeError(f"Unexpected search payload: {data}")


if __name__ == "__main__":
    tries = 5
    for i in range(tries):
        try:
            check_health()
            check_search()
            print("OK: endpoints responsive and returning expected shapes")
            sys.exit(0)
        except Exception as e:
            print(f"Attempt {i+1}/{tries} failed: {e}")
            time.sleep(2)
    print("ERROR: endpoints failed after retries")
    sys.exit(2)
