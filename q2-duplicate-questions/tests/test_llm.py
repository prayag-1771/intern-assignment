"""The LLM client, tested against a fake service so no key or network is needed."""

import json

import pytest

from qbank import llm
from qbank.llm import ChatModel, LLMUnavailable


class FakeResponse:
    def __init__(self, status_code=200, content='{"label": "different"}', headers=None):
        self.status_code = status_code
        self.headers = headers or {}
        self.text = content
        self._content = content

    def json(self):
        return {"choices": [{"message": {"content": self._content}}]}


@pytest.fixture
def service(monkeypatch):
    """Replace the network call with a queue of prepared replies, and never really sleep."""
    replies, sent = [], []

    def fake_post(url, headers, json, timeout):
        sent.append({"url": url, "body": json})
        return replies.pop(0)

    monkeypatch.setattr(llm.requests, "post", fake_post)
    monkeypatch.setattr(llm.time, "sleep", lambda seconds: None)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")
    return replies, sent


def test_reply_is_parsed_and_the_request_carries_both_messages(service, tmp_path):
    replies, sent = service
    replies.append(FakeResponse())
    model = ChatModel("groq", "some-model", cache_path=tmp_path / "cache.json")

    assert model.ask_json("You are a judge.", "Compare A and B.") == {"label": "different"}
    assert sent[0]["url"].startswith("https://api.groq.com/")
    assert [m["content"] for m in sent[0]["body"]["messages"]] == ["You are a judge.", "Compare A and B."]
    assert sent[0]["body"]["temperature"] == 0.0


def test_same_request_is_answered_from_the_cache_even_by_a_new_client(service, tmp_path):
    replies, sent = service
    replies.append(FakeResponse())
    cache = tmp_path / "cache.json"

    ChatModel("groq", "some-model", cache_path=cache).ask_json("s", "u")
    again = ChatModel("groq", "some-model", cache_path=cache)

    assert again.ask_json("s", "u") == {"label": "different"}
    assert len(sent) == 1 and again.calls_made == 0


def test_cached_reply_needs_no_key(service, tmp_path, monkeypatch):
    replies, _ = service
    replies.append(FakeResponse())
    cache = tmp_path / "cache.json"
    ChatModel("groq", "some-model", cache_path=cache).ask_json("s", "u")

    monkeypatch.delenv("GROQ_API_KEY")
    offline = ChatModel("groq", "some-model", cache_path=cache)

    assert offline.ask_json("s", "u") == {"label": "different"}
    with pytest.raises(LLMUnavailable, match="GROQ_API_KEY is not set"):
        offline.ask_json("s", "a question that was never asked")


def test_rate_limited_request_is_retried(service, tmp_path):
    replies, sent = service
    replies.extend([FakeResponse(429, "slow down", {"retry-after": "2"}), FakeResponse()])

    model = ChatModel("groq", "some-model", cache_path=tmp_path / "cache.json")

    assert model.ask_json("s", "u") == {"label": "different"}
    assert len(sent) == 2


def test_a_timeout_is_retried_and_a_lasting_one_becomes_unavailable(service, tmp_path, monkeypatch):
    replies, sent = service
    outcomes = [llm.requests.Timeout("slow"), FakeResponse()]

    def flaky_post(url, headers, json, timeout):
        sent.append(json)
        result = outcomes.pop(0)
        if isinstance(result, Exception):
            raise result
        return result

    monkeypatch.setattr(llm.requests, "post", flaky_post)
    assert ChatModel("groq", "some-model", cache_path=tmp_path / "a.json").ask_json("s", "u") == {"label": "different"}
    assert len(sent) == 2

    def always_times_out(url, headers, json, timeout):
        raise llm.requests.ConnectionError("down")

    monkeypatch.setattr(llm.requests, "post", always_times_out)
    with pytest.raises(LLMUnavailable, match="network error: ConnectionError"):
        ChatModel("groq", "some-model", cache_path=tmp_path / "b.json").ask_json("s", "u")


def test_a_used_up_daily_allowance_is_not_retried(service, tmp_path):
    replies, sent = service
    quota_body = '[{"error": {"code": 429, "details": [{"retryDelay": "59767s"}]}}]'
    replies.append(FakeResponse(429, quota_body))

    with pytest.raises(LLMUnavailable, match="allowance used up, retry in about 16.6 hours"):
        ChatModel("groq", "some-model", cache_path=tmp_path / "cache.json").ask_json("s", "u")
    assert len(sent) == 1


def test_a_refused_request_raises_instead_of_being_cached(service, tmp_path):
    replies, _ = service
    replies.append(FakeResponse(401, "bad key"))
    cache = tmp_path / "cache.json"

    with pytest.raises(LLMUnavailable, match="HTTP 401"):
        ChatModel("groq", "some-model", cache_path=cache).ask_json("s", "u")
    assert not cache.exists()


def test_reply_wrapped_in_a_code_fence_is_still_read(service, tmp_path, monkeypatch):
    replies, sent = service
    replies.append(FakeResponse(content='```json\n{"label": "variant"}\n```'))
    monkeypatch.setenv("GEMINI_API_KEY", "test-key")

    model = ChatModel("gemini", "some-model", cache_path=tmp_path / "cache.json")

    assert model.ask_json("s", "u") == {"label": "variant"}
    assert sent[0]["url"].startswith("https://generativelanguage.googleapis.com/")


def test_cache_file_is_plain_json(service, tmp_path):
    replies, _ = service
    replies.append(FakeResponse())
    cache = tmp_path / "cache.json"

    ChatModel("groq", "some-model", cache_path=cache).ask_json("s", "u")

    saved = json.loads(cache.read_text(encoding="utf-8"))
    assert list(saved.values()) == ['{"label": "different"}']
