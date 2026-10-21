from src.update_check import is_newer, parse_version


def test_parse_version_strips_v():
    assert parse_version("v0.2.0") == (0, 2, 0)
    assert parse_version("0.2.0") == (0, 2, 0)
    assert parse_version("1.2.3") == (1, 2, 3)


def test_parse_version_ignores_suffix():
    assert parse_version("v1.0.0-beta") == (1, 0, 0)


def test_parse_version_empty():
    assert parse_version("") == ()
    assert parse_version("v") == ()


def test_is_newer():
    assert is_newer("v0.3.0", "0.2.0")
    assert not is_newer("v0.2.0", "0.2.0")
    assert not is_newer("v0.1.0", "0.2.0")
    assert is_newer("1.0.0", "0.9.9")
