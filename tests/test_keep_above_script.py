from src.keep_above import KeepAbove


def test_script_is_bound_to_unique_title_and_restores_position():
    keep = KeepAbove()
    keep.set_window_title("gamohud-hud-unique-123")
    keep.set_position_provider(lambda: (640, 360))
    keep.set_geometry_bus("org.example.Gamohud")
    script = keep._script_text()

    assert 'indexOf("gamohud-hud-unique-123") === 0' in script
    assert "gamohud-overlay" not in script
    assert "frameGeometry" in script
    assert "captionChanged" in script
    assert "windowAdded" in script
    assert "w.moveable" not in script
    assert "640" in script and "360" in script
    assert "callDBus" in script
    assert "org.example.Gamohud" in script
    assert "Geometry" in script


def test_no_geometry_bus_means_no_reporting():
    keep = KeepAbove()
    keep.set_window_title("gamohud-hud-unique-456")
    keep.set_position_provider(lambda: None)
    script = keep._script_text()

    assert "callDBus" not in script
    assert "reportGeometry" not in script
    assert "frameGeometry" not in script
