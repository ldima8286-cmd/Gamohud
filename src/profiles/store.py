"""Load / save overlay and application profiles as YAML."""
from __future__ import annotations

import os
from pathlib import Path

from src.platform_utils import config_dir

from .model import (
    AppProfile,
    OverlayProfile,
    default_app_profiles,
    default_overlay_profiles,
)

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


def profiles_path() -> Path:
    return config_dir("gamohud") / "profiles.yaml"


class ProfileStore:
    def __init__(self, path: Path | None = None):
        self.path = Path(path) if path else profiles_path()
        self.overlay_profiles: list[OverlayProfile] = []
        self.app_profiles: list[AppProfile] = []
        self.active_overlay: str = "default"
        self.global_fps_backend: str = "vulkan_layer"
        self.load()

    def load(self) -> None:
        data = {}
        if self.path.exists():
            try:
                text = self.path.read_text(encoding="utf-8")
                if yaml is not None:
                    data = yaml.safe_load(text) or {}
            except Exception:
                data = {}

        self.overlay_profiles = [
            OverlayProfile.from_dict(d) for d in data.get("overlay_profiles", [])
        ] or default_overlay_profiles()
        self.app_profiles = [
            AppProfile.from_dict(d) for d in data.get("app_profiles", [])
        ]
        self.active_overlay = data.get("active_overlay", self.overlay_profiles[0].name)
        self.global_fps_backend = data.get("global_fps_backend", "vulkan_layer")
        if not self.app_profiles:
            self.app_profiles = default_app_profiles()

    def save(self) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "active_overlay": self.active_overlay,
            "global_fps_backend": self.global_fps_backend,
            "overlay_profiles": [p.to_dict() for p in self.overlay_profiles],
            "app_profiles": [p.to_dict() for p in self.app_profiles],
        }
        if yaml is not None:
            text = yaml.safe_dump(data, sort_keys=False, allow_unicode=True)
        else:  # pragma: no cover
            import json
            text = json.dumps(data, indent=2, ensure_ascii=False)
        self.path.write_text(text, encoding="utf-8")

    def get_overlay(self, name: str | None) -> OverlayProfile | None:
        if not name:
            return None
        for p in self.overlay_profiles:
            if p.name == name:
                return p
        return None

    def active_overlay_profile(self) -> OverlayProfile:
        return self.get_overlay(self.active_overlay) or self.overlay_profiles[0]

    def upsert_overlay(self, profile: OverlayProfile) -> None:
        for i, p in enumerate(self.overlay_profiles):
            if p.name == profile.name:
                self.overlay_profiles[i] = profile
                return
        self.overlay_profiles.append(profile)

    def delete_overlay(self, name: str) -> None:
        self.overlay_profiles = [p for p in self.overlay_profiles if p.name != name]
        if not self.overlay_profiles:
            self.overlay_profiles = default_overlay_profiles()
        if self.active_overlay == name:
            self.active_overlay = self.overlay_profiles[0].name

    def upsert_app(self, profile: AppProfile) -> None:
        for i, p in enumerate(self.app_profiles):
            if p.name == profile.name:
                self.app_profiles[i] = profile
                return
        self.app_profiles.append(profile)

    def delete_app(self, name: str) -> None:
        self.app_profiles = [p for p in self.app_profiles if p.name != name]
