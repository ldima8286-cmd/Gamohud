from src.profiles.matcher import (
    find_profile,
    find_profile_by_window,
    match_name,
)
from src.profiles.model import AppProfile


def test_match_name_wildcards_and_case():
    assert match_name("Dota2.exe", ["dota*"])
    assert match_name("wine-preloader", ["wine*", "lutris*"])
    assert not match_name("", ["*"])
    assert not match_name("firefox", ["wine*"])


def test_find_profile_by_process_prefers_specific():
    profiles = [
        AppProfile(name="generic", match=["steam*"]),
        AppProfile(name="dota", match=["steam_app_dota"]),
    ]
    got = find_profile(profiles, ["steam_app_dota"])
    assert got is not None and got.name == "dota"


def test_find_profile_skips_empty_match():
    profiles = [AppProfile(name="empty", match=[])]
    assert find_profile(profiles, ["anything"]) is None


def test_find_profile_by_window():
    profiles = [AppProfile(name="dota", match=["*Dota 2*"])]
    assert find_profile_by_window(profiles, "Dota 2 — playing").name == "dota"
    assert find_profile_by_window(profiles, "Desktop") is None
    assert find_profile_by_window(profiles, None) is None
