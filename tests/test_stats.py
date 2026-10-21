from src.fps.stats import FPSStats, percentile


def test_percentile_basic():
    assert percentile([1, 2, 3, 4, 5], 50) == 3.0
    assert percentile([1, 2, 3, 4, 5], 0) == 1.0
    assert percentile([1, 2, 3, 4, 5], 100) == 5.0


def test_percentile_empty_and_single():
    assert percentile([], 50) == 0.0
    assert percentile([42], 50) == 42.0


def test_stats_ignores_none_and_nonpositive():
    s = FPSStats(window=10)
    s.add(None)
    s.add(0)
    s.add(-5)
    s.add("nope")
    assert len(s) == 0
    assert s.summary() == {}


def test_stats_summary():
    s = FPSStats(window=100)
    for v in [60] * 9 + [10]:
        s.add(v)
    summary = s.summary()
    assert summary["fps_avg"] == 55.0
    assert summary["fps_1low"] <= summary["fps_avg"]
    assert summary["fps_01low"] <= summary["fps_1low"]


def test_stats_window_is_bounded():
    s = FPSStats(window=5)
    for v in range(1, 21):
        s.add(v)
    assert len(s) == 5
    assert s.summary()["fps_avg"] == 18.0


def test_stats_reset():
    s = FPSStats()
    s.add(60)
    s.reset()
    assert len(s) == 0
