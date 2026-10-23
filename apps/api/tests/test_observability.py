from __future__ import annotations

from onboarding.app.observability import Metrics


def test_counter_labels_are_rendered_once_and_sorted() -> None:
    metrics = Metrics()
    metrics.inc("requests_total", labels={"status": "200", "method": "GET"})
    metrics.inc("requests_total", labels={"method": "GET", "status": "200"})
    metrics.inc("requests_total", labels={"method": "POST", "status": "200"}, value=2)

    rendered = metrics.render()

    assert rendered.count("# TYPE requests_total counter") == 1
    assert 'requests_total{method="GET",status="200"} 2' in rendered
    assert 'requests_total{method="POST",status="200"} 2' in rendered


def test_histogram_buckets_are_cumulative() -> None:
    metrics = Metrics()
    metrics.observe("stage_seconds", 0.003)
    metrics.observe("stage_seconds", 0.2)

    rendered = metrics.render()

    assert 'stage_seconds_bucket{le="0.005"} 1' in rendered
    assert 'stage_seconds_bucket{le="0.1"} 1' in rendered
    assert 'stage_seconds_bucket{le="0.25"} 2' in rendered
    assert 'stage_seconds_bucket{le="+Inf"} 2' in rendered
    assert "stage_seconds_count 2" in rendered


def test_label_values_are_escaped() -> None:
    metrics = Metrics()
    metrics.inc("events_total", labels={"reason": 'bad "quote"\\line'})

    assert 'reason="bad \\"quote\\"\\\\line"' in metrics.render()


def test_reset_drops_previous_series() -> None:
    metrics = Metrics()
    metrics.inc("events_total")
    metrics.reset()

    assert metrics.render() == ""
