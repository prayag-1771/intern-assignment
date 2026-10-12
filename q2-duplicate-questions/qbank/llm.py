"""Ask a hosted LLM (Groq or Gemini) a question and get JSON back.

Both services accept the same chat request format, so one small client covers both.

Every reply is saved in a cache file (one file per model), keyed by the exact request.
Asking the same thing again returns the saved reply without calling the service. That makes results
repeatable, stays inside the free rate limits, and lets the examples and tests run
on a machine with no API key.
"""

from __future__ import annotations

import hashlib
import json
import re
import time
from pathlib import Path

import requests

from .config import DATA_DIR, api_key

PROVIDERS = {
    "groq": ("https://api.groq.com/openai/v1/chat/completions", "GROQ_API_KEY"),
    "gemini": ("https://generativelanguage.googleapis.com/v1beta/openai/chat/completions", "GEMINI_API_KEY"),
}
CACHE_DIR = DATA_DIR / "llm_cache"

_RETRYABLE = (429, 500, 502, 503)
_ATTEMPTS = 8
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
        cache_path: Path | None = None,
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
        # One file per model, so several models can be run at once without overwriting each other.
        self._cache_path = cache_path or CACHE_DIR / f"{provider}__{model.replace('/', '__')}.json"
        self._cache = self._read_cache()
        self.calls_made = 0  # requests actually sent to the service, not counting cache hits
        self.seconds_waiting = 0.0  # time spent on those requests, including rate-limit waits
        self.seconds_answering = 0.0  # time of the successful requests alone: the model's real speed
        self.replies_fetched = 0  # replies received from the service (each may have taken several requests)

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
        if not self._cache_path.exists():
            return {}
        with open(self._cache_path, encoding="utf-8") as handle:
            return json.load(handle)

    def _write_cache(self) -> None:
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
        started = time.perf_counter()
        try:
            reply = self._send(key, body)
        finally:
            self.seconds_waiting += time.perf_counter() - started
        self.replies_fetched += 1
        return reply

    def _send(self, key: str, body: dict) -> str:
        problem = ""
        for attempt in range(_ATTEMPTS):
            last_attempt = attempt == _ATTEMPTS - 1
            self.calls_made += 1
            attempt_started = time.perf_counter()
            try:
                response = requests.post(self._url, headers={"Authorization": f"Bearer {key}"}, json=body, timeout=120)
            except requests.RequestException as error:
                # A timeout or dropped connection is usually brief, so it is worth another try.
                problem = f"network error: {type(error).__name__}"
                if last_attempt:
                    break
                time.sleep(_wait_seconds(None, attempt))
                continue
            if response.status_code == 200:
                self.seconds_answering += time.perf_counter() - attempt_started
                return response.json()["choices"][0]["message"]["content"] or ""
            problem = f"HTTP {response.status_code}: {response.text[:300]}"
            if response.status_code not in _RETRYABLE or last_attempt:
                break
            asked = _requested_wait(response)
            if asked is not None and asked > _LONGEST_WAIT_SECONDS:
                # A daily allowance is used up; waiting a minute will not help.
                problem = f"HTTP {response.status_code}: allowance used up, retry in about {asked / 3600:.1f} hours"
                break
            # A rate-limited service says how long to wait; otherwise back off a little longer each time.
            time.sleep(_wait_seconds(response, attempt))
        raise LLMUnavailable(f"{self.name}: {problem}")


def _requested_wait(response: requests.Response) -> float | None:
    """Seconds the service asks us to wait: Groq sends a retry-after header, Gemini a retryDelay in the body."""
    try:
        return float(response.headers.get("retry-after", ""))
    except ValueError:
        pass
    found = re.search(r'"retryDelay":\s*"(\d+(?:\.\d+)?)s"', response.text)
    return float(found.group(1)) if found else None


def _wait_seconds(response: requests.Response | None, attempt: int) -> float:
    asked = _requested_wait(response) if response is not None else None
    if asked is None:
        asked = 2.0**attempt
    return min(max(asked, 1.0), _LONGEST_WAIT_SECONDS)


def _parse_json(reply: str) -> dict:
    """Read the model's reply as JSON, tolerating a ```json fence around it."""
    text = reply.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[-1].rsplit("```", 1)[0]
    return json.loads(text)
