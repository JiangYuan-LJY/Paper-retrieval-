from dataclasses import dataclass
import os
from pathlib import Path

from dotenv import load_dotenv


class ConfigError(RuntimeError):
    pass


ROOT_DIR = Path(__file__).resolve().parents[1]
RESULTS_DIR = ROOT_DIR / "results"
SCOPUS_SEARCH_URL = "https://api.elsevier.com/content/search/scopus"
SCOPUS_ABSTRACT_URL = "https://api.elsevier.com/content/abstract/doi"
EASYSCHOLAR_API_URL = "https://www.easyscholar.cc/open/getPublicationRank"
REQUEST_TIMEOUT_SECONDS = 20
EASYSCHOLAR_DELAY_SECONDS = 0.5
DEFAULT_MAX_RESULTS = 20


@dataclass(frozen=True)
class Settings:
    scopus_api_key: str
    easyscholar_secret_key: str
    paper_scoring_temperature: float


def load_settings() -> Settings:
    load_dotenv(ROOT_DIR / ".env")
    scopus_api_key = os.getenv("SCOPUS_API_KEY", "").strip()
    easyscholar_secret_key = os.getenv("EASYSCHOLAR_SECRET_KEY", "").strip()
    paper_scoring_temperature = _load_paper_scoring_temperature()

    missing = []
    if not scopus_api_key:
        missing.append("SCOPUS_API_KEY")
    if not easyscholar_secret_key:
        missing.append("EASYSCHOLAR_SECRET_KEY")
    if missing:
        names = ", ".join(missing)
        raise ConfigError(f"Missing required environment variable(s): {names}. Please set them in a local .env file.")

    return Settings(
        scopus_api_key=scopus_api_key,
        easyscholar_secret_key=easyscholar_secret_key,
        paper_scoring_temperature=paper_scoring_temperature,
    )


def _load_paper_scoring_temperature() -> float:
    raw_value = os.getenv("PAPER_SCORING_TEMPERATURE", "0").strip()
    if not raw_value:
        return 0
    try:
        temperature = float(raw_value)
    except ValueError as error:
        raise ConfigError("PAPER_SCORING_TEMPERATURE must be a number.") from error
    if temperature < 0:
        raise ConfigError("PAPER_SCORING_TEMPERATURE must be greater than or equal to 0.")
    return temperature
