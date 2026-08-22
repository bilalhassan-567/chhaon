import time

from app.services.rate_limit import RateLimiter


def test_allows_up_to_max_events():
    limiter = RateLimiter(max_events=3, window_seconds=60)
    assert limiter.allow("a") is True
    assert limiter.allow("a") is True
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False


def test_different_keys_have_independent_limits():
    limiter = RateLimiter(max_events=1, window_seconds=60)
    assert limiter.allow("a") is True
    assert limiter.allow("b") is True
    assert limiter.allow("a") is False


def test_old_events_expire_out_of_window():
    limiter = RateLimiter(max_events=1, window_seconds=0.05)
    assert limiter.allow("a") is True
    assert limiter.allow("a") is False
    time.sleep(0.1)
    assert limiter.allow("a") is True
