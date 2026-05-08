from dataclasses import dataclass

NOT_AVAILABLE = "Not available"


def normalize_value(value: object) -> str:
    if value is None:
        return NOT_AVAILABLE
    if isinstance(value, str):
        stripped = value.strip()
        return stripped if stripped else NOT_AVAILABLE
    if isinstance(value, (list, tuple, set)):
        items = [normalize_value(item) for item in value]
        available_items = [item for item in items if item != NOT_AVAILABLE]
        return "; ".join(available_items) if available_items else NOT_AVAILABLE
    return str(value).strip() or NOT_AVAILABLE


@dataclass
class Paper:
    title: str = NOT_AVAILABLE
    authors: str = NOT_AVAILABLE
    journal: str = NOT_AVAILABLE
    year: str = NOT_AVAILABLE
    publication_date: str = NOT_AVAILABLE
    abstract: str = NOT_AVAILABLE
    author_keywords: str = NOT_AVAILABLE
    doi: str = NOT_AVAILABLE
    scopus_link: str = NOT_AVAILABLE
    paper_link: str = NOT_AVAILABLE
    journal_rank: str = NOT_AVAILABLE
    journal_quality_score: float | None = None
    topic_relevance_score: float | None = None
    keyword_match_score: float | None = None
    total_score: float | None = None
    score_reason: str = NOT_AVAILABLE

    def __post_init__(self) -> None:
        self.title = normalize_value(self.title)
        self.authors = normalize_value(self.authors)
        self.journal = normalize_value(self.journal)
        self.year = normalize_value(self.year)
        self.publication_date = normalize_value(self.publication_date)
        self.abstract = normalize_value(self.abstract)
        self.author_keywords = normalize_value(self.author_keywords)
        self.doi = normalize_value(self.doi)
        self.scopus_link = normalize_value(self.scopus_link)
        self.paper_link = normalize_value(self.paper_link)
        self.journal_rank = normalize_value(self.journal_rank)
        self.score_reason = normalize_value(self.score_reason)
