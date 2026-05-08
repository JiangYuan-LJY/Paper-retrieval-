from dataclasses import dataclass
from typing import Any

import yaml

from config import ConfigError, ROOT_DIR


CONFIG_PATH = ROOT_DIR / "Get_Paper.yaml"


@dataclass(frozen=True)
class ScoreWeights:
    journal_quality: float
    topic_relevance: float
    keyword_match: float


@dataclass(frozen=True)
class JournalQualityConfig:
    q1_or_engineering_1: float
    q2_or_engineering_2: float
    q3_or_engineering_3: float
    other_known_rank: float


@dataclass(frozen=True)
class RetrievalConfig:
    topic: str
    keywords: list[str]
    keyword_operator: str
    max_results: int
    year: int
    scoring_prompt: str
    score_weights: ScoreWeights
    journal_quality: JournalQualityConfig


def load_retrieval_config() -> RetrievalConfig:
    if not CONFIG_PATH.exists():
        raise ConfigError(f"Missing config file: {CONFIG_PATH}")

    try:
        data = yaml.safe_load(CONFIG_PATH.read_text(encoding="utf-8"))
    except yaml.YAMLError as error:
        raise ConfigError(f"Invalid YAML in config file {CONFIG_PATH}: {error}") from error

    if not isinstance(data, dict):
        raise ConfigError("Config file must contain a YAML object.")

    return RetrievalConfig(
        topic=_required_text(data, "topic"),
        keywords=_required_keywords(data, "keywords"),
        keyword_operator=_required_keyword_operator(data, "keyword_operator"),
        max_results=_required_positive_int(data, "max_results"),
        year=_required_year(data, "year"),
        scoring_prompt=_required_text(data, "scoring_prompt"),
        score_weights=_load_score_weights(_required_object(data, "score_weights")),
        journal_quality=_load_journal_quality(_required_object(data, "journal_quality")),
    )


def _required_object(data: dict[str, Any], field_name: str) -> dict[str, Any]:
    if field_name not in data:
        raise ConfigError(f"Missing required config field: {field_name}")
    value = data[field_name]
    if not isinstance(value, dict):
        raise ConfigError(f"Config field {field_name} must be an object.")
    return value


def _required_text(data: dict[str, Any], field_name: str) -> str:
    if field_name not in data:
        raise ConfigError(f"Missing required config field: {field_name}")
    value = data[field_name]
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"Config field {field_name} must be a non-empty string.")
    return value.strip()


def _required_keywords(data: dict[str, Any], field_name: str) -> list[str]:
    if field_name not in data:
        raise ConfigError(f"Missing required config field: {field_name}")
    value = data[field_name]
    if not isinstance(value, list):
        raise ConfigError(f"Config field {field_name} must be a list of non-empty strings.")
    keywords = []
    for keyword in value:
        if not isinstance(keyword, str) or not keyword.strip():
            raise ConfigError(f"Config field {field_name} must contain only non-empty strings.")
        keywords.append(keyword.strip())
    if not keywords:
        raise ConfigError(f"Config field {field_name} must contain at least one keyword.")
    return keywords


def _required_keyword_operator(data: dict[str, Any], field_name: str) -> str:
    value = _required_text(data, field_name).upper()
    if value not in {"AND", "OR"}:
        raise ConfigError(f"Config field {field_name} must be either AND or OR.")
    return value


def _required_positive_int(data: dict[str, Any], field_name: str) -> int:
    if field_name not in data:
        raise ConfigError(f"Missing required config field: {field_name}")
    value = data[field_name]
    if not isinstance(value, int) or isinstance(value, bool) or value <= 0:
        raise ConfigError(f"Config field {field_name} must be a positive integer.")
    return value


def _required_year(data: dict[str, Any], field_name: str) -> int:
    year = _required_positive_int(data, field_name)
    if year < 1000 or year > 9999:
        raise ConfigError(f"Config field {field_name} must use YYYY format.")
    return year


def _load_score_weights(data: dict[str, Any]) -> ScoreWeights:
    return ScoreWeights(
        journal_quality=_required_number(data, "journal_quality"),
        topic_relevance=_required_number(data, "topic_relevance"),
        keyword_match=_required_number(data, "keyword_match"),
    )


def _load_journal_quality(data: dict[str, Any]) -> JournalQualityConfig:
    return JournalQualityConfig(
        q1_or_engineering_1=_required_number(data, "q1_or_engineering_1"),
        q2_or_engineering_2=_required_number(data, "q2_or_engineering_2"),
        q3_or_engineering_3=_required_number(data, "q3_or_engineering_3"),
        other_known_rank=_required_number(data, "other_known_rank"),
    )


def _required_number(data: dict[str, Any], field_name: str) -> float:
    if field_name not in data:
        raise ConfigError(f"Missing required config field: {field_name}")
    value = data[field_name]
    if not isinstance(value, (int, float)) or isinstance(value, bool) or value < 0:
        raise ConfigError(f"Config field {field_name} must be a non-negative number.")
    return float(value)
