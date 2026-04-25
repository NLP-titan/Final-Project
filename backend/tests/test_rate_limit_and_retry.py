"""Rate limiter and retry helper."""
import pytest

from app.middleware.rate_limit import _SlidingWindow
from app.utils.retry import retry_call


def test_retry_eventually_succeeds():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise RuntimeError("transient")
        return "ok"

    result = retry_call(flaky, attempts=4, base_delay=0.0, max_delay=0.0)
    assert result == "ok"
    assert calls["n"] == 3


def test_retry_gives_up_after_attempts():
    def always_fails():
        raise ValueError("nope")

    with pytest.raises(ValueError):
        retry_call(always_fails, attempts=2, base_delay=0.0, max_delay=0.0)


def test_sliding_window_blocks_when_full():
    win = _SlidingWindow()
    for _ in range(3):
        ok, _, _ = win.hit("k", limit=3)
        assert ok
    ok, _, retry_after = win.hit("k", limit=3)
    assert not ok
    assert retry_after > 0


def test_chat_rate_limit_returns_429(client, user_headers, monkeypatch):
    from app.config import settings

    # Tighten the chat limit just for this test.
    monkeypatch.setattr(settings, "rate_limit_chat_per_minute", 2)

    # Reset the in-memory window so previous tests don't bleed in.
    from app.middleware.rate_limit import reset_rate_limit_for_tests

    reset_rate_limit_for_tests()

    conv = client.post("/api/conversations", headers=user_headers, json={}).json()
    conv_id = conv["id"]
    payload = {"content": "Is paracetamol covered?"}
    assert (
        client.post(
            f"/api/conversations/{conv_id}/messages", headers=user_headers, json=payload
        ).status_code
        == 200
    )
    assert (
        client.post(
            f"/api/conversations/{conv_id}/messages", headers=user_headers, json=payload
        ).status_code
        == 200
    )
    # 3rd hit should be over the limit
    resp = client.post(
        f"/api/conversations/{conv_id}/messages", headers=user_headers, json=payload
    )
    assert resp.status_code == 429
    assert "Retry-After" in {k.title() for k in resp.headers.keys()} or "retry-after" in resp.headers
