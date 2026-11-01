"""Settings, shared constants, the learner profile, and client creation.

Nothing in this module needs Streamlit to be installed, so the engine and the
tests can import it on their own.
"""
from __future__ import annotations

import os
from dataclasses import asdict, dataclass

try:  # python-dotenv is optional so the tests can run without it
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - only hit when the package is missing
    pass

# --------------------------------------------------------------------------
# Limits shared by the UI, the validator, and the import/export code
# --------------------------------------------------------------------------
MIN_HOURS_PER_WEEK = 2
MAX_HOURS_PER_WEEK = 30
MIN_WEEKS = 2
MAX_WEEKS = 24
DEFAULT_HOURS_PER_WEEK = 10
DEFAULT_WEEKS = 8

LEVELS = ("Beginner", "Intermediate", "Advanced")
LEARNING_STYLES = (
    "Balanced: theory + practice",
    "Project-based",
    "Video-first",
    "Reading-first",
)
RESOURCE_LANGUAGES = ("English", "Telugu + English", "Hindi + English")
ACTIVITY_TYPES = ("learn", "practice", "project", "review")

# --------------------------------------------------------------------------
# PDF / retrieval settings
# --------------------------------------------------------------------------
EMBEDDING_MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
PDF_CHUNK_SIZE = 900
PDF_CHUNK_OVERLAP = 150
RETRIEVAL_TOP_K = 4
RETRIEVAL_MIN_SCORE = 0.15
MAX_PDF_MB = 15

DEFAULT_MODEL = "gemini-3.1-flash-lite"
_PLACEHOLDER_KEYS = {"", "YOUR_NEW_GEMINI_API_KEY", "YOUR_GEMINI_API_KEY", "your_api_key_here"}


class ConfigError(ValueError):
    """Raised when required configuration is missing or unusable."""


def get_setting(name: str, default: str | None = None) -> str | None:
    """Read a setting from Streamlit secrets first, then the environment/.env."""
    try:
        import streamlit as st

        value = st.secrets.get(name)
        if value:
            return str(value)
    except Exception:
        pass
    return os.getenv(name, default)


@dataclass(frozen=True)
class Settings:
    api_key: str
    model: str = DEFAULT_MODEL
    # Roadmaps are returned as JSON, and Gemini "thinking" tokens count against
    # this limit, so it is deliberately generous.
    max_output_tokens: int = 16000
    temperature: float = 0.4


def _int_setting(name: str, default: int) -> int:
    raw = get_setting(name)
    try:
        return int(raw) if raw else default
    except (TypeError, ValueError):
        return default


def load_settings() -> Settings:
    api_key = (get_setting("GEMINI_API_KEY") or "").strip()
    if api_key in _PLACEHOLDER_KEYS:
        raise ConfigError(
            "GEMINI_API_KEY is missing. Add it to Streamlit Cloud > App settings > "
            "Secrets, or to your local .env file (see .env.example)."
        )
    return Settings(
        api_key=api_key,
        model=(get_setting("GEMINI_MODEL", DEFAULT_MODEL) or DEFAULT_MODEL).strip(),
        max_output_tokens=_int_setting("GEMINI_MAX_OUTPUT_TOKENS", 16000),
    )


def create_client(settings: Settings | None = None):
    """Create the Gemini client. Returns (client, settings)."""
    settings = settings or load_settings()
    try:
        from google import genai
    except ImportError as exc:  # pragma: no cover - depends on the environment
        raise ConfigError(
            "The google-genai package is not installed. Run: pip install -r requirements.txt"
        ) from exc
    return genai.Client(api_key=settings.api_key), settings


# --------------------------------------------------------------------------
# Learner profile
# --------------------------------------------------------------------------
@dataclass
class LearnerProfile:
    goal: str
    current_skills: str = "Not specified"
    level: str = LEVELS[0]
    hours_per_week: int = DEFAULT_HOURS_PER_WEEK
    duration_weeks: int = DEFAULT_WEEKS
    learning_style: str = LEARNING_STYLES[0]
    learning_language: str = RESOURCE_LANGUAGES[0]

    @property
    def total_hours(self) -> int:
        return int(self.hours_per_week) * int(self.duration_weeks)

    def problems(self) -> list[str]:
        """Return human-readable input problems (empty list means valid)."""
        found = []
        if not (self.goal or "").strip():
            found.append("Please enter your career goal.")
        if self.level not in LEVELS:
            found.append(f"Level must be one of: {', '.join(LEVELS)}.")
        if not MIN_HOURS_PER_WEEK <= int(self.hours_per_week) <= MAX_HOURS_PER_WEEK:
            found.append(
                f"Study hours per week must be between {MIN_HOURS_PER_WEEK} and {MAX_HOURS_PER_WEEK}."
            )
        if not MIN_WEEKS <= int(self.duration_weeks) <= MAX_WEEKS:
            found.append(f"Duration must be between {MIN_WEEKS} and {MAX_WEEKS} weeks.")
        return found

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "LearnerProfile":
        """Tolerant loader used when importing a saved progress file."""

        def clamp(value, low, high, default):
            try:
                return max(low, min(high, int(value)))
            except (TypeError, ValueError):
                return default

        data = data if isinstance(data, dict) else {}
        level = data.get("level")
        return cls(
            goal=str(data.get("goal") or "").strip(),
            current_skills=str(data.get("current_skills") or "Not specified").strip(),
            level=level if level in LEVELS else LEVELS[0],
            hours_per_week=clamp(
                data.get("hours_per_week"), MIN_HOURS_PER_WEEK, MAX_HOURS_PER_WEEK, DEFAULT_HOURS_PER_WEEK
            ),
            duration_weeks=clamp(data.get("duration_weeks"), MIN_WEEKS, MAX_WEEKS, DEFAULT_WEEKS),
            learning_style=str(data.get("learning_style") or LEARNING_STYLES[0]),
            learning_language=str(data.get("learning_language") or RESOURCE_LANGUAGES[0]),
        )
