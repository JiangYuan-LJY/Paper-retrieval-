import sys

import requests

from config import ConfigError, RESULTS_DIR, load_settings
from easyscholar_client import EasyScholarClient
from markdown_writer import write_markdown
from paper_scoring import score_and_sort_papers
from retrieval_config import load_retrieval_config
from scopus_client import search_papers


def contains_chinese(text: str) -> bool:
    return any("一" <= character <= "鿿" for character in text)


def warn_if_chinese_input(keywords: list[str]) -> None:
    if any(contains_chinese(keyword) for keyword in keywords):
        print("Warning: Scopus search works best with English keywords. Chinese keywords may reduce results or cause API query issues.")


def main() -> int:
    try:
        settings = load_settings()
        retrieval_config = load_retrieval_config()
    except ConfigError as error:
        print(f"Configuration error: {error}")
        return 1

    warn_if_chinese_input(retrieval_config.keywords)

    try:
        papers = search_papers(
            api_key=settings.scopus_api_key,
            keywords=retrieval_config.keywords,
            keyword_operator=retrieval_config.keyword_operator,
            max_results=retrieval_config.max_results,
            year=retrieval_config.year,
        )
    except requests.RequestException as error:
        print(f"Scopus API request failed: {error}")
        return 1
    except ValueError as error:
        print(f"Failed to parse Scopus API response: {error}")
        return 1

    easyscholar = EasyScholarClient(settings.easyscholar_secret_key)
    for paper in papers:
        paper.journal_rank = easyscholar.get_journal_rank(paper.journal)

    papers = score_and_sort_papers(
        papers=papers,
        config=retrieval_config,
        temperature=settings.paper_scoring_temperature,
    )

    output_path = write_markdown(
        papers=papers,
        topic=retrieval_config.topic,
        keywords=retrieval_config.keywords,
        year=retrieval_config.year,
        results_dir=RESULTS_DIR,
    )
    print(f"Saved results to: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
