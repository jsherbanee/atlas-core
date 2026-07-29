from atlas_core.services.retry_policy import compute_backoff


def test_deterministic_backoff():
    d1, t1 = compute_backoff(1, base=5, multiplier=2.0, max_delay=1000, jitter=False)
    d2, t2 = compute_backoff(2, base=5, multiplier=2.0, max_delay=1000, jitter=False)
    assert d1 == 5
    assert d2 == 10
    assert t2 - t1 >= 5
