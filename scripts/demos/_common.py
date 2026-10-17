import json
import os

import httpx

BASE_URL = os.environ.get("CORVID_API_BASE_URL", "http://localhost:8000")


def client() -> httpx.Client:
    return httpx.Client(base_url=BASE_URL, timeout=30)


def header(title: str) -> None:
    print(f"\n{'=' * 70}\n{title}\n{'=' * 70}")


def show(label: str, payload) -> None:
    print(f"\n-- {label} --")
    print(json.dumps(payload, indent=2, default=str))
