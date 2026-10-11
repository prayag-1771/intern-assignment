"""Ask a hosted LLM (Groq or Gemini) a question and get JSON back.

Both services accept the same chat request format, so one small client covers both.

Every reply is saved in a cache file, keyed by the exact request. Asking the same
thing again returns the saved reply without calling the service. That makes results
repeatable, stays inside the free rate limits, and lets the examples and tests run
on a machine with no API key.
"""

from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path

import requests

from .config import DATA_DIR, api_key

PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "GEMINI_API_KEY"),
}
DEFAULT_CACHE = DATA_DIR / "llm_cache.json"

_RETRYABLE = (429, 500, 502, 503)
_ATTEMPTS = 6
_LONGEST_WAIT_SECONDS = 60.0


class LLMUnavailable(RuntimeError):
    """The reply is not in the cache and the service cannot be reached (no key, or it keeps failing)."""


class ChatModel:
    """One LLM on one service, answering in JSON, with every reply cached on disk."""

    def __init__(
        self,
        provider: str,
        model: str,
        temperature: float = 0.0,
        cache_path: Path | None = DEFAULT_CACHE,
        extra: dict | None = None,
    ):
        if provider not in PROVIDERS:
            raise ValueError(f"Unknown provider {provider!r}; choose one of {sorted(PROVIDERS)}.")
        self.provider = provider
        self.model = model
        self.name = f"{provider}/{model}"
        self._url, self._key_name = PROVIDERS[provider]
        self._temperature = temperature
        self._extra = extra or {}
        self._cache_path = cache_path
        self._cache = self._read_cache()
        self.calls_made = 0  # requests actually sent to the service, not counting cache hits

    def ask_json(self, system: str, user: str) -> dict:
        """Send one instruction and one message; return the model's JSON reply as a dict."""
        key = self._cache_key(system, user)
        if key not in self._cache:
            self._cache[key] = self._request(system, user)
            self._write_cache()
        return _parse_json(self._cache[key])

    def _cache_key(self, system: str, user: str) -> str:
        request = [self.provider, self.model, self._temperature, self._extra, system, user]
        return hashlib.sha256(json.dumps(request, ensure_ascii=False, sort_keys=True).encode("utf-8")).hexdigest()

    def _read_cache(self) -> dict[str, str]:
        if self._cache_path is None or not self._cache_path.exists():
            return {}
        with open(self._cache_path, encoding="utf-8") as handle:
            return json.load(handle)

    def _write_cache(self) -> None:
        if self._cache_path is None:
            return
        self._cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self._cache_path, "w", encoding="utf-8") as handle:
            json.dump(self._cache, handle, ensure_ascii=False, indent=1, sort_keys=True)

    def _request(self, system: str, user: str) -> str:
        key = api_key(self._key_name)
        if key is None:
            raise LLMUnavailable(f"{self.name}: this request is not cached and {self._key_name} is not set.")
        body = {
            "model": self.model,
            "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
            "temperature": self._temperature,
            "response_format": {"type": "json_object"},
            **self._extra,
        }
        for attempt in range(_ATTEMPTS):
            response = requests.post(self._url, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=120)
            self.calls_made += 1
            if response.status_code == 200:
                return response.json()["choices"][0]["message"]["content"] or ""
            if response.status_code not in _RETRYABLE or attempt == _ATTEMPTS - 1:
                break
            # A rate-limited service says how long to wait; otherwise back off a little longer each time.
            time.sleep(_wait_seconds(response, attempt))
        raise LLMUnavailable(f"{self.name}: HTTP {response.status_code}: {response.text[:300]}")


def _wait_seconds(response: requests.Response, attempt: int) -> float:
    try:
        asked = float(response.headers.get("retry-after", ""))
    except ValueError:
        asked = 2.0**attempt
    return min(max(asked, 1.0), _LONGEST_WAIT_SECONDS)


def _parse_json(reply: str) -> dict:
    """Read the model's reply as JSON, tolerating a ```json fence around it."""
    text = reply.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    return json.loads(text)
