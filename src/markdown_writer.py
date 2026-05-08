import json
from datetime import datetime
from pathlib import Path

from paper_model import Paper


def write_markdown(
    papers: list[Paper],
    topic: str,
    keywords: list[str],
    year: int,
    results_dir: Path,
) -> Path:
    results_dir.mkdir(parents=True, exist_ok=True)
    output_stem = f"papers_{datetime.now().strftime('%Y%m%d_%H%M')}"
    markdown_path = results_dir / f"{output_stem}.md"
    json_path = results_dir / f"{output_stem}.json"
    markdown_path.write_text(
        _build_markdown(papers, topic, keywords, year),
        encoding="utf-8",
    )
    json_path.write_text(
        json.dumps(_build_json_data(papers, topic, keywords, year), ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return markdown_path


def _build_markdown(
    papers: list[Paper],
    topic: str,
    keywords: list[str],
    year: int,
) -> str:
    lines = [
        "# Paper Search Results",
        "",
        f"Topic: {topic}",
        f"Keywords: {', '.join(keywords)}",
        f"Year: {year}",
        f"Total papers: {len(papers)}",
        "",
        "---",
        "",
    ]

    for index, paper in enumerate(papers, start=1):
        lines.extend(
            [
                f"## {index}. {paper.title}",
                "",
                (
                    f"- Scores: Total: {_format_score(paper.total_score)}"
                    f" | Journal Quality: {_format_score(paper.journal_quality_score)}"
                    f" | Topic Relevance: {_format_score(paper.topic_relevance_score)}"
                    f" | Keyword Match: {_format_score(paper.keyword_match_score)}"
                ),
                f"- Journal: {paper.journal} | Journal Rank: {paper.journal_rank}",
                f"- Authors: {paper.authors} | DOI: {paper.doi} | Year: {paper.year}",
                "",
                "### Abstract",
                "",
                paper.abstract,
                "",
                "### Keywords",
                "",
                paper.author_keywords,
                "",
                f"- Scopus Link: {paper.scopus_link}",
                f"- Paper Link: {paper.paper_link}",
                "",
                "---",
                "",
            ]
        )

    return "\n".join(lines)


def _format_score(score: float | None) -> str:
    return "Not scored" if score is None else f"{score:g}"


def _build_json_data(
    papers: list[Paper],
    topic: str,
    keywords: list[str],
    year: int,
) -> dict[str, object]:
    return {
        "topic": topic,
        "keywords": keywords,
        "year": year,
        "total_papers": len(papers),
        "papers": [_paper_to_dict(paper) for paper in papers],
    }


def _paper_to_dict(paper: Paper) -> dict[str, object]:
    return {
        "title": paper.title,
        "authors": paper.authors,
        "author_keywords": paper.author_keywords,
        "journal": paper.journal,
        "journal_rank": paper.journal_rank,
        "journal_quality_score": paper.journal_quality_score,
        "topic_relevance_score": paper.topic_relevance_score,
        "keyword_match_score": paper.keyword_match_score,
        "total_score": paper.total_score,
        "score_reason": paper.score_reason,
        "year": paper.year,
        "publication_date": paper.publication_date,
        "doi": paper.doi,
        "scopus_link": paper.scopus_link,
        "paper_link": paper.paper_link,
        "abstract": paper.abstract,
    }
