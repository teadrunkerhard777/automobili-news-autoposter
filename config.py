"""Runtime configuration assembled from the project-specific layer."""

import os

from dotenv import load_dotenv

from project import settings as project_settings
from project.settings import (
    EVENT_DEDUP_SETTINGS,
    MAX_NEWS_PER_RUN,
    MIN_PUBLICATION_SCORE,
    NEWS_LOOKBACK_DAYS,
    POST_MODE,
)
from project.sources import SOURCES


# Environment-backed config must be loaded before module constants are built.
load_dotenv()

# Older child projects may not define diversity settings yet.
DIVERSITY_SETTINGS = getattr(project_settings, "DIVERSITY_SETTINGS", None)


def _read_boolean_env(name, default):
    """Read a boolean environment variable with a safe fallback."""

    value = os.getenv(name)

    if value is None:
        return default

    normalized = value.strip().casefold()

    if normalized in {"1", "true", "yes", "on"}:
        return True

    if normalized in {"0", "false", "no", "off"}:
        return False

    # An invalid value must never enable live publication accidentally.
    return default


# Local execution is safe unless production explicitly opts out.
DRY_RUN = _read_boolean_env("AUTOPOSTER_DRY_RUN", default=True)
