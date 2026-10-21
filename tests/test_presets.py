from src.metrics import LAYOUT_PRESETS, METRICS, format_metric, metric_label, metric_unit


def test_every_preset_metric_is_known():
    for key, (label, desc, keys) in LAYOUT_PRESETS.items():
        assert label and desc, key
        assert keys, key
        for metric in keys:
            assert metric in METRICS, f"{key}: unknown metric {metric}"


def test_fps_low_metrics_registered():
    for key in ("fps", "fps_avg", "fps_1low", "fps_01low"):
        assert key in METRICS
        assert metric_unit(key) == ""


def test_format_metric_and_none():
    assert format_metric("fps", 59.6) == "60"
    assert format_metric("fps", None) is None
    assert format_metric("nope", 1) is None


def test_label_lookup_falls_back_to_key():
    assert metric_label("fps") == "FPS"
    assert metric_label("does_not_exist") == "does_not_exist"
