import json
import os
import re
import time
from typing import Any, Callable

import requests
from dotenv import load_dotenv

from config import REQUEST_TIMEOUT_SECONDS, ROOT_DIR
from paper_model import NOT_AVAILABLE, Paper
from retrieval_config import RetrievalConfig


MODEL_SCORING_NOT_CONFIGURED = "Model scoring is not configured"
MODEL_RETRY_STATUS_CODES = {429, 502, 503, 504}
MODEL_MAX_ATTEMPTS = 3
MODEL_RETRY_DELAY_SECONDS = 2
MODEL_REQUEST_DELAY_SECONDS = 1


def score_and_sort_papers(
    papers: list[Paper],
    config: RetrievalConfig,
    temperature: float,
) -> list[Paper]:
    load_dotenv(ROOT_DIR / ".env")
    scoring_configured = _model_scoring_configured()

    for paper in papers:
        _score_paper(paper, config, scoring_configured, temperature)

    return sorted(papers, key=lambda paper: paper.total_score or 0, reverse=True)


def _model_scoring_configured() -> bool:
    return all(
        os.getenv(name, "").strip()
        for name in ("PAPER_SCORING_API_URL", "PAPER_SCORING_API_KEY", "PAPER_SCORING_MODEL")
    )


def _score_paper(
    paper: Paper,
    config: RetrievalConfig,
    scoring_configured: bool,
    temperature: float,
) -> None:
    score_failures = []
    try:
        paper.journal_quality_score = _score_journal_quality(paper.journal_rank, config)
    except Exception:
        paper.journal_quality_score = None
        score_failures.append("Journal quality scoring failed")

    if scoring_configured:
        try:
            model_scores = _score_model_components(config, paper.abstract, paper.author_keywords, temperature)
            paper.topic_relevance_score = model_scores["topic_relevance_score"]
            paper.keyword_match_score = model_scores["keyword_match_score"]
        except Exception as error:
            paper.topic_relevance_score = None
            paper.keyword_match_score = None
            score_failures.append(f"Model scoring request failed: {_safe_error_message(error)}")
    else:
        paper.topic_relevance_score = None
        paper.keyword_match_score = None

    component_scores = [
        paper.journal_quality_score,
        paper.topic_relevance_score,
        paper.keyword_match_score,
    ]
    available_scores = [score for score in component_scores if score is not None]
    paper.total_score = sum(available_scores) if available_scores else None

    paper.score_reason = _build_score_reason(paper, scoring_configured, score_failures)


def _score_journal_quality(journal_rank: str, config: RetrievalConfig) -> float | None:
    if journal_rank == NOT_AVAILABLE:
        return None

    rank_text = journal_rank.upper()
    candidates: list[float] = []
    rules: tuple[tuple[Callable[[str], bool], float], ...] = (
        (lambda text: "Q1" in text or _has_chinese_partition(text, "1"), config.journal_quality.q1_or_engineering_1),
        (lambda text: "Q2" in text or _has_chinese_partition(text, "2"), config.journal_quality.q2_or_engineering_2),
        (lambda text: "Q3" in text or _has_chinese_partition(text, "3"), config.journal_quality.q3_or_engineering_3),
    )

    for matcher, score in rules:
        if matcher(rank_text):
            candidates.append(score)

    if candidates:
        return max(candidates)
    if journal_rank.strip():
        return config.journal_quality.other_known_rank
    return None


def _has_chinese_partition(text: str, partition: str) -> bool:
    return bool(re.search(rf"工程技术\s*{partition}\s*区|{partition}\s*区", text))


def _score_model_components(
    config: RetrievalConfig,
    abstract: str,
    author_keywords: str,
    temperature: float,
) -> dict[str, float | None]:
    if abstract == NOT_AVAILABLE and author_keywords == NOT_AVAILABLE:
        return {"topic_relevance_score": None, "keyword_match_score": None}

    prompt = _build_scoring_prompt(config, abstract, author_keywords)
    scores = _call_model_for_scores(prompt, temperature)
    return {
        "topic_relevance_score": _clamp_optional_score(
            scores.get("topic_relevance_score"),
            config.score_weights.topic_relevance,
        ),
        "keyword_match_score": _clamp_optional_score(
            scores.get("keyword_match_score"),
            config.score_weights.keyword_match,
        ),
    }


def _build_scoring_prompt(config: RetrievalConfig, abstract: str, author_keywords: str) -> str:
    return (
        config.scoring_prompt.format(
            topic_relevance_max_score=config.score_weights.topic_relevance,
            keyword_match_max_score=config.score_weights.keyword_match,
            journal_quality_max_score=config.score_weights.journal_quality,
        )
        + "\n"
        + f"Topic: {config.topic}\n"
        + f"User keywords: {', '.join(config.keywords)}\n"
        + f"Abstract: {abstract}\n"
        + f"Author Keywords: {author_keywords}"
    )


def _call_model_for_scores(prompt: str, temperature: float) -> dict[str, Any]:
    api_url = os.getenv("PAPER_SCORING_API_URL", "").strip()
    api_key = os.getenv("PAPER_SCORING_API_KEY", "").strip()
    model = os.getenv("PAPER_SCORING_MODEL", "").strip()
    if not api_url or not api_key or not model:
        return {"topic_relevance_score": None, "keyword_match_score": None}

    last_error: Exception | None = None
    for attempt in range(1, MODEL_MAX_ATTEMPTS + 1):
        try:
            time.sleep(MODEL_REQUEST_DELAY_SECONDS)
            response = requests.post(
                _normalize_model_api_url(api_url),
                headers=_build_model_headers(api_key),
                json={
                    "model": model,
                    "messages": [
                        {
                            "role": "system",
                            "content": "You score academic papers. Return only valid JSON. Do not include markdown.",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": temperature,
                },
                timeout=REQUEST_TIMEOUT_SECONDS,
            )
            response.raise_for_status()
            payload = response.json()
            return _extract_scores_from_model_payload(payload)
        except requests.HTTPError as error:
            last_error = error
            status_code = error.response.status_code if error.response is not None else None
            if status_code not in MODEL_RETRY_STATUS_CODES or attempt == MODEL_MAX_ATTEMPTS:
                raise
            time.sleep(MODEL_RETRY_DELAY_SECONDS)
        except (requests.Timeout, requests.ConnectionError) as error:
            last_error = error
            if attempt == MODEL_MAX_ATTEMPTS:
                raise
            time.sleep(MODEL_RETRY_DELAY_SECONDS)

    if last_error is not None:
        raise last_error
    return {"topic_relevance_score": None, "keyword_match_score": None}


def _normalize_model_api_url(api_url: str) -> str:
    normalized = api_url.rstrip("/")
    if normalized.endswith("/v1/chat/completions"):
        return normalized
    return f"{normalized}/v1/chat/completions"


def _build_model_headers(api_key: str) -> dict[str, str]:
    return {
        "Accept": "application/json",
        "Authorization": api_key,
        "Content-Type": "application/json",
    }


def _extract_scores_from_model_payload(payload: dict[str, Any]) -> dict[str, Any]:
    content = payload["choices"][0]["message"]["content"]
    parsed = json.loads(_strip_json_fences(content))
    return {
        "topic_relevance_score": parsed.get("topic_relevance_score"),
        "keyword_match_score": parsed.get("keyword_match_score"),
    }


def _clamp_optional_score(score: object, max_score: float) -> float | None:
    if score is None:
        return None
    return _clamp_score(float(score), max_score)


def _strip_json_fences(content: str) -> str:
    stripped = content.strip()
    if stripped.startswith("```"):
        stripped = re.sub(r"^```(?:json)?\s*", "", stripped, flags=re.IGNORECASE)
        stripped = re.sub(r"\s*```$", "", stripped)
    return stripped.strip()


def _clamp_score(score: float, max_score: float) -> float:
    return min(max(score, 0), max_score)


def _safe_error_message(error: Exception) -> str:
    if isinstance(error, requests.HTTPError) and error.response is not None:
        return f"HTTP {error.response.status_code}"
    if isinstance(error, requests.Timeout):
        return "request timeout"
    if isinstance(error, requests.ConnectionError):
        return "connection error"
    if isinstance(error, requests.RequestException):
        return "request error"
    if isinstance(error, json.JSONDecodeError):
        return "invalid JSON response"
    if isinstance(error, (KeyError, IndexError, TypeError)):
        return "unexpected response format"
    if isinstance(error, ValueError):
        return "invalid score value"
    return error.__class__.__name__


def _build_score_reason(paper: Paper, scoring_configured: bool, score_failures: list[str]) -> str:
    reasons = list(score_failures)
    if paper.journal_quality_score is None:
        reasons.append("Journal quality score unavailable")
    if paper.topic_relevance_score is None:
        reasons.append("Topic relevance score unavailable")
    if paper.keyword_match_score is None:
        reasons.append("Keyword match score unavailable")
    if not scoring_configured:
        reasons.append(MODEL_SCORING_NOT_CONFIGURED)
    if paper.total_score is None:
        reasons.append("Total score unavailable because no components were scored")
    return "; ".join(dict.fromkeys(reasons)) if reasons else "Scored successfully"
