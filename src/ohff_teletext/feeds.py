from __future__ import annotations

import json
from typing import Any
from urllib.request import urlopen


SPOTS_URL = "https://spots.wwff.co/static/spots.json"
AGENDAS_URL = "https://spots.wwff.co/static/agendas.json"


def fetch_json(url: str) -> list[dict[str, Any]]:
    with urlopen(url, timeout=20) as response:
        payload = json.load(response)
    if not isinstance(payload, list):
        raise ValueError(f"{url} did not return a JSON list")
    return [item for item in payload if isinstance(item, dict)]


def fetch_spots(url: str = SPOTS_URL) -> list[dict[str, Any]]:
    return fetch_json(url)


def fetch_agendas(url: str = AGENDAS_URL) -> list[dict[str, Any]]:
    return fetch_json(url)
