from datetime import date
import re
from typing import Any
from urllib.parse import quote

import requests

from config import REQUEST_TIMEOUT_SECONDS, SCOPUS_ABSTRACT_URL, SCOPUS_SEARCH_URL
from paper_model import NOT_AVAILABLE, Paper, normalize_value


def _quote_term(term: str) -> str:
    escaped = term.replace('"', '\\"')
    return f'"{escaped}"'


def build_scopus_query(keywords: list[str], year: int, keyword_operator: str) -> str:
    keyword_query = f" {keyword_operator} ".join(_quote_term(keyword) for keyword in keywords)
    return f"TITLE-ABS-KEY({keyword_query}) AND PUBYEAR = {year}"


def search_papers(
    api_key: str,
    keywords: list[str],
    keyword_operator: str,
    max_results: int,
    year: int,
) -> list[Paper]:
    query = build_scopus_query(keywords, year, keyword_operator)
    print(f"Scopus query: {query}")
    response = requests.get(
        SCOPUS_SEARCH_URL,
        headers={"X-ELS-APIKey": api_key, "Accept": "application/json"},
        params={"query": query, "count": max_results, "httpAccept": "application/json"},
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    try:
        response.raise_for_status()
        payload = response.json()
    except requests.HTTPError:
        _print_response_debug("Scopus API returned an error", response)
        raise
    except ValueError:
        _print_response_debug("Scopus API returned invalid JSON", response)
        raise
    entries = payload.get("search-results", {}).get("entry", [])

    print(f"Scopus returned entries: {len(entries)}")
    if entries and "error" in entries[0]:
        print(f"First Scopus entry error: {entries[0].get('error')}")

    papers = []
    skipped_entries = 0
    for entry in entries:
        if not _is_paper_entry(entry):
            skipped_entries += 1
            continue
        papers.append(_parse_entry(entry, api_key))
    if skipped_entries:
        print(f"Skipped non-paper Scopus entries: {skipped_entries}")
    return papers[:max_results]


def fetch_abstract_metadata_by_doi(api_key: str, doi: str) -> dict[str, str]:
    normalized_doi = normalize_value(doi)
    if normalized_doi == NOT_AVAILABLE:
        return {"abstract": NOT_AVAILABLE, "author_keywords": NOT_AVAILABLE}

    try:
        response = requests.get(
            f"{SCOPUS_ABSTRACT_URL}/{quote(normalized_doi, safe='')}",
            headers={"X-ELS-APIKey": api_key, "Accept": "application/json"},
            params={"httpAccept": "application/json"},
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError):
        return {"abstract": NOT_AVAILABLE, "author_keywords": NOT_AVAILABLE}

    return {
        "abstract": _extract_abstract_from_abstract_payload(payload),
        "author_keywords": _extract_author_keywords_from_abstract_payload(payload),
    }


def _extract_abstract_from_abstract_payload(payload: object) -> str:
    if not isinstance(payload, dict):
        return NOT_AVAILABLE
    response = payload.get("abstracts-retrieval-response")
    if not isinstance(response, dict):
        return NOT_AVAILABLE
    coredata = response.get("coredata")
    if isinstance(coredata, dict):
        return normalize_value(coredata.get("dc:description"))
    return NOT_AVAILABLE


def _extract_author_keywords_from_abstract_payload(payload: object) -> str:
    response = payload.get("abstracts-retrieval-response") if isinstance(payload, dict) else None
    if not isinstance(response, dict):
        return NOT_AVAILABLE

    keywords = _normalize_author_keywords(response.get("authkeywords"))
    if keywords != NOT_AVAILABLE:
        return keywords

    authkeywords = response.get("authkeywords")
    if isinstance(authkeywords, dict):
        keywords = _normalize_author_keywords(authkeywords.get("author-keyword"))
        if keywords != NOT_AVAILABLE:
            return keywords

    coredata = response.get("coredata")
    if isinstance(coredata, dict):
        keywords = _normalize_author_keywords(coredata.get("authkeywords"))
        if keywords != NOT_AVAILABLE:
            return keywords
    return NOT_AVAILABLE


def _normalize_author_keywords(value: object) -> str:
    if isinstance(value, str):
        return normalize_value([keyword.strip() for keyword in value.split("|") if keyword.strip()])
    if isinstance(value, list):
        keywords = []
        for item in value:
            if isinstance(item, dict):
                keyword = item.get("$") or item.get("_") or item.get("#text") or item.get("text")
            else:
                keyword = item
            normalized = normalize_value(keyword)
            if normalized != NOT_AVAILABLE:
                keywords.append(normalized)
        return normalize_value(keywords)
    return NOT_AVAILABLE


def _print_response_debug(message: str, response: requests.Response) -> None:
    print(f"{message}. status_code={response.status_code}")
    print(f"response preview: {response.text[:500]}")


def _is_paper_entry(entry: dict[str, Any]) -> bool:
    return "error" not in entry and normalize_value(entry.get("dc:title")) != NOT_AVAILABLE


def _parse_entry(entry: dict[str, Any], api_key: str) -> Paper:
    publication_date = normalize_value(entry.get("prism:coverDate"))
    doi = normalize_value(entry.get("prism:doi"))
    scopus_link = _extract_link(entry.get("link"), "scopus")
    paper_link = f"https://doi.org/{doi}" if doi != NOT_AVAILABLE else scopus_link
    abstract = normalize_value(entry.get("dc:description"))
    author_keywords = _normalize_author_keywords(entry.get("authkeywords"))

    if doi != NOT_AVAILABLE and (abstract == NOT_AVAILABLE or author_keywords == NOT_AVAILABLE):
        metadata = fetch_abstract_metadata_by_doi(api_key, doi)
        if abstract == NOT_AVAILABLE:
            abstract = metadata["abstract"]
        if author_keywords == NOT_AVAILABLE:
            author_keywords = metadata["author_keywords"]

    return Paper(
        title=entry.get("dc:title"),
        authors=_extract_authors(entry),
        journal=entry.get("prism:publicationName"),
        year=_extract_year(publication_date),
        publication_date=publication_date,
        abstract=abstract,
        author_keywords=author_keywords,
        doi=doi,
        scopus_link=scopus_link,
        paper_link=paper_link,
        journal_rank=NOT_AVAILABLE,
    )


def _extract_authors(entry: dict[str, Any]) -> str:
    authors = entry.get("author")
    if isinstance(authors, list):
        names = [author.get("authname") or author.get("ce:indexed-name") for author in authors if isinstance(author, dict)]
        return normalize_value(names)
    return normalize_value(entry.get("dc:creator"))


def _extract_link(links: object, preferred_ref: str) -> str:
    if not isinstance(links, list):
        return NOT_AVAILABLE

    fallback = NOT_AVAILABLE
    for link in links:
        if not isinstance(link, dict):
            continue
        href = normalize_value(link.get("@href"))
        if href == NOT_AVAILABLE:
            continue
        if fallback == NOT_AVAILABLE:
            fallback = href
        if link.get("@ref") == preferred_ref:
            return href
    return fallback


def _extract_year(publication_date: str) -> str:
    if publication_date == NOT_AVAILABLE:
        return NOT_AVAILABLE
    match = re.search(r"\b\d{4}\b", publication_date)
    return match.group(0) if match else NOT_AVAILABLE
