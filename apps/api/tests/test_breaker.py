from __future__ import annotations

from datetime import timedelta

from onboarding.core.breaker import CircuitBreaker

from .conftest import NOW


def test_closed_breaker_allows_calls() -> None:
    breaker = CircuitBreaker(threshold=2)

    assert breaker.allows(NOW)
    assert not breaker.is_open


def test_opens_after_the_threshold() -> None:
    breaker = CircuitBreaker(threshold=2)
    breaker = breaker.record_failure(NOW)
    assert breaker.allows(NOW)

    breaker = breaker.record_failure(NOW)

    assert breaker.is_open
    assert not breaker.allows(NOW)


def test_half_opens_after_the_cooldown() -> None:
    breaker = CircuitBreaker(threshold=1, cooldown=timedelta(seconds=30))
    breaker = breaker.record_failure(NOW)

    assert not breaker.allows(NOW + timedelta(seconds=29))
    assert breaker.allows(NOW + timedelta(seconds=30))


def test_success_resets_the_breaker() -> None:
    breaker = CircuitBreaker(threshold=1).record_failure(NOW).record_success()

    assert not breaker.is_open
    assert breaker.failures == 0
