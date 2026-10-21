from src.profiles.model import AppProfile, OverlayProfile, default_overlay_profiles
from src.profiles.store import ProfileStore


def test_overlay_profile_roundtrip_ignores_unknown():
    p = OverlayProfile(name="x", metrics=["fps"])
    data = p.to_dict()
    data["bogus"] = 123
    restored = OverlayProfile.from_dict(data)
    assert restored.name == "x"
    assert restored.metrics == ["fps"]


def test_app_profile_roundtrip():
    p = AppProfile(name="a", match=["*x*"], env={"A": "1"})
    assert AppProfile.from_dict(p.to_dict()).env == {"A": "1"}


def test_default_overlay_profiles_have_names():
    names = {p.name for p in default_overlay_profiles()}
    assert {"default", "minimal", "full"} <= names


def test_store_save_and_load(tmp_path):
    path = tmp_path / "profiles.yaml"
    store = ProfileStore(path)
    store.upsert_overlay(OverlayProfile(name="mine", metrics=["fps_1low"]))
    store.active_overlay = "mine"
    store.save()

    reloaded = ProfileStore(path)
    got = reloaded.get_overlay("mine")
    assert got is not None
    assert got.metrics == ["fps_1low"]
    assert reloaded.active_overlay == "mine"


def test_store_delete_overlay_falls_back(tmp_path):
    store = ProfileStore(tmp_path / "p.yaml")
    store.overlay_profiles = [OverlayProfile(name="only")]
    store.delete_overlay("only")
    assert store.overlay_profiles
