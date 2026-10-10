"""Project settings: where files live and which API keys are available."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PACKAGE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = PACKAGE_DIR.parent  # q2-duplicate-questions/
REPO_DIR = PROJECT_DIR.parent  # repository root, where .env lives
DATA_DIR = PROJECT_DIR / "data"

# Keys are optional. Code that needs one asks for it here and fails with a clear message.
load_dotenv(REPO_DIR / ".env")


def api_key(name: str) -> str | None:
    """Return an API key from the environment, or None when it is not set."""
    value = os.environ.get(name, "").strip()
    return value or None
