from __future__ import annotations

from onboarding.api.ratelimit import AuthFailureLimiter


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


def limiter() -> tuple[AuthFailureLimiter, FakeClock]:
    clock = FakeClock()
    return AuthFailureLimiter(max_failures=3, window_s=60, block_s=30, clock=clock), clock


def test_repeated_failures_block_the_peer() -> None:
    subject, clock = limiter()

    subject.fail("1.2.3.4")
    subject.fail("1.2.3.4")
    assert not subject.blocked("1.2.3.4")
    subject.fail("1.2.3.4")

    assert subject.blocked("1.2.3.4")
    assert not subject.blocked("5.6.7.8")

    clock.now += 31
    assert not subject.blocked("1.2.3.4")


def test_a_success_forgets_the_failures() -> None:
    subject, _ = limiter()

    subject.fail("peer")
    subject.fail("peer")
    subject.succeed("peer")
    subject.fail("peer")

    assert not subject.blocked("peer")


def test_failures_outside_the_window_do_not_count() -> None:
    subject, clock = limiter()

    subject.fail("peer")
    subject.fail("peer")
    clock.now += 61
    subject.fail("peer")

    assert not subject.blocked("peer")


def test_reset_clears_every_bucket() -> None:
    subject, _ = limiter()

    subject.fail("peer")
    subject.fail("peer")
    subject.fail("peer")
    subject.reset()

    assert not subject.blocked("peer")
