# Workflow

This document describes the runtime flow of the GET-Paper project.

## 1. Load Configuration

The program starts in `src/main.py`.

It first loads two kinds of configuration:

1. Environment settings from `.env` through `load_settings()` in `src/config.py`.
2. Retrieval and scoring settings from `Get_Paper.yaml` through `load_retrieval_config()` in `src/retrieval_config.py`.

Required environment variables:

- `SCOPUS_API_KEY`
- `EASYSCHOLAR_SECRET_KEY`

Optional model scoring variables:

- `PAPER_SCORING_API_URL`
- `PAPER_SCORING_API_KEY`
- `PAPER_SCORING_MODEL`
- `PAPER_SCORING_TEMPERATURE`

Required runtime config fields:

- `topic`
- `keywords`
- `keyword_operator`
- `max_results`
- `year`
- `scoring_prompt`
- `score_weights`
- `journal_quality`

If required configuration is missing or invalid, the program prints a configuration error and exits with code `1`.

## 2. Validate Keywords

After loading `Get_Paper.yaml`, `src/main.py` checks whether any configured keyword contains Chinese characters.

If Chinese keywords are detected, the program prints a warning because Scopus search works best with English keywords.

## 3. Retrieve Papers from Scopus

`src/main.py` calls `search_papers()` from `src/scopus_client.py`.

Inputs:

- Scopus API key from `.env`
- `keywords` from `Get_Paper.yaml`
- `keyword_operator` from `Get_Paper.yaml`
- `max_results` from `Get_Paper.yaml`
- `year` from `Get_Paper.yaml`

The Scopus query is built from keywords, the configured keyword operator, and year. `keyword_operator` controls whether keywords are joined with `AND` or `OR` inside `TITLE-ABS-KEY(...)`. The publication year filter always remains an `AND PUBYEAR = ...` constraint. The topic is not used for Scopus filtering.

The Scopus retrieval step extracts available metadata, including:

- title
- authors
- journal/source
- year
- publication date
- abstract
- author keywords
- DOI
- Scopus link
- paper link

If abstract or author keywords are missing and a DOI is available, the client attempts a Scopus Abstract Retrieval fallback.

## 4. Enrich Journal Rank with EasyScholar

After Scopus retrieval, `src/main.py` creates an `EasyScholarClient` from `src/easyscholar_client.py`.

For each paper, it calls:

```python
paper.journal_rank = easyscholar.get_journal_rank(paper.journal)
```

The EasyScholar client returns journal ranking text when available. Missing or failed rank lookups are represented as `Not available` rather than stopping the whole program.

## 5. Score Papers

After all paper metadata and journal ranks are available, `src/main.py` calls `score_and_sort_papers()` from `src/paper_scoring.py`.

Each paper is scored in three parts.

### Journal Quality

Journal quality is calculated locally from `paper.journal_rank` and the configured `journal_quality` values.

Default scoring rules:

- Q1 or Engineering/Technology 1st partition: 45
- Q2 or Engineering/Technology 2nd partition: 40
- Q3 or Engineering/Technology 3rd partition: 30
- Other known rank: 25

If more than one rule matches, the highest score is used.

### Topic Relevance

Topic relevance is scored by the configured model relay when model scoring variables are available.

The model compares:

- `topic` from `Get_Paper.yaml`
- paper abstract from Scopus metadata

If model scoring is not configured or the model request fails, this score becomes unavailable.

### Keyword Match

Keyword match is scored by the configured model relay when model scoring variables are available.

The model compares:

- `keywords` from `Get_Paper.yaml`
- paper author keywords from Scopus metadata

If model scoring is not configured or the model request fails, this score becomes unavailable.

## 6. Calculate Total Score

`total_score` is calculated as the sum of available scored components.

Examples:

- Journal Quality `45`, Topic Relevance `Not scored`, Keyword Match `Not scored` gives Total `45`.
- Journal Quality `45`, Topic Relevance `30`, Keyword Match `Not scored` gives Total `75`.
- If all components are unavailable, Total remains unavailable and is displayed as `Not scored`.

This keeps partial scoring useful when model scoring fails or when some paper fields are missing.

## 7. Sort Papers

After scoring, papers are sorted by `total_score` in descending order.

Missing totals are treated as `0` for sorting, so papers with available scores usually appear before papers with no scored components.

## 8. Write Output Files

`src/main.py` calls `write_markdown()` from `src/markdown_writer.py`.

The writer creates two files in `results/`:

- a Markdown report
- a JSON report

The Markdown report is intended for reading and review. It includes the title, scores, journal information, authors, DOI, year, abstract, keywords, and links.

The JSON report preserves structured paper data and score fields for later debugging or processing.

## 9. Error Handling Summary

- Missing required `.env` values: configuration error and exit code `1`.
- `Get_Paper.yaml`: configuration error and exit code `1`.
- Scopus request failure: request error and exit code `1`.
- Scopus response parsing failure: parse error and exit code `1`.
- EasyScholar rank lookup failure: rank becomes `Not available` where possible.
- Model scoring failure: model-dependent scores become unavailable, and the program continues.

## 10. Output Review

After the program finishes, review the generated files in `results/`.

Use the Markdown file for manual literature screening and the JSON file for structured post-processing.
