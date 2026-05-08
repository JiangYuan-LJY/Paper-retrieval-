import time
from typing import Any
from urllib.parse import quote

import requests

from config import EASYSCHOLAR_API_URL, EASYSCHOLAR_DELAY_SECONDS, REQUEST_TIMEOUT_SECONDS
from paper_model import NOT_AVAILABLE, normalize_value


class EasyScholarClient:
    def __init__(self, secret_key: str) -> None:
        self.secret_key = secret_key
        self._cache: dict[str, str] = {}

    def get_journal_rank(self, journal: str) -> str:
        journal_name = normalize_value(journal)
        if journal_name == NOT_AVAILABLE:
            return NOT_AVAILABLE
        if journal_name in self._cache:
            return self._cache[journal_name]

        time.sleep(EASYSCHOLAR_DELAY_SECONDS)
        try:
            url = (
                f"{EASYSCHOLAR_API_URL}"
                f"?secretKey={quote(self.secret_key, safe='')}"
                f"&publicationName={quote(journal_name, safe='')}"
            )
            response = requests.get(
                url,
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload = response.json()
            rank = _extract_rank(payload)
        except (requests.RequestException, ValueError):
            rank = NOT_AVAILABLE

        self._cache[journal_name] = rank
        return rank


def _extract_rank(payload: Any) -> str:
    if not isinstance(payload, dict):
        return NOT_AVAILABLE

    candidates = []
    data = payload.get("data")
    if isinstance(data, dict):
        candidates.extend(_rank_candidates_from_dict(data))
        official_rank = data.get("officialRank")
        if isinstance(official_rank, dict):
            select_rank = official_rank.get("select")
            if isinstance(select_rank, dict):
                candidates.extend(_rank_candidates_from_dict(select_rank))
            all_rank = official_rank.get("all")
            if isinstance(all_rank, dict):
                candidates.extend(_rank_candidates_from_dict(all_rank))
    elif isinstance(data, list):
        for item in data:
            if isinstance(item, dict):
                candidates.extend(_rank_candidates_from_dict(item))

    candidates.extend(_rank_candidates_from_dict(payload))
    available = [normalize_value(candidate) for candidate in candidates]
    available = [candidate for candidate in available if candidate != NOT_AVAILABLE]
    return "; ".join(dict.fromkeys(available)) if available else NOT_AVAILABLE


def _rank_candidates_from_dict(item: dict[str, Any]) -> list[Any]:
    keys = (
        "rank",
        "journalRank",
        "partition",
        "subZone",
        "zone",
        "sci",
        "sciif",
        "sciUp",
        "sciUpTop",
        "sciBase",
        "eii",
        "jci",
        "esi",
        "jcr",
        "jcrZone",
        "cas",
        "casZone",
        "ccf",
    )
    return [item.get(key) for key in keys if key in item]
