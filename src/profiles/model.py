"""Profile models: overlay appearance profiles and per-application profiles."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from ..metrics import DEFAULT_METRICS

POSITIONS = [
    "top-left", "top-center", "top-right",
    "middle-left", "center", "middle-right",
    "bottom-left", "bottom-center", "bottom-right",
    "custom",
]


@dataclass
class OverlayProfile:
    name: str = "default"
    position: str = "top-left"
    x: int = 20
    y: int = 20
    margin: int = 16
    opacity: float = 0.85
    font_family: str = "monospace"
    font_size: int = 12
    font_bold: bool = True
    fg_color: str = "#ffffff"
    label_color: str = "#9ad1ff"
    accent_color: str = "#7CFC00"
    bg_color: str = "#000000"
    bg_opacity: float = 0.55
    border_radius: int = 8
    click_through: bool = True
    refresh_ms: int = 1000
    graph: bool = False
    metrics: list[str] = field(default_factory=lambda: list(DEFAULT_METRICS))

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "OverlayProfile":
        known = {f for f in cls.__dataclass_fields__}
        clean = {k: v for k, v in (data or {}).items() if k in known}
        return cls(**clean)


@dataclass
class AppProfile:
    name: str = ""
    match: list[str] = field(default_factory=list)
    overlay: str | None = None
    fps_backend: str | None = None
    gamemode: bool = False
    env: dict = field(default_factory=dict)
    command_prefix: list[str] = field(default_factory=list)
    cwd: str | None = None
    args: str = ""
    executable: str | None = None
    process_name: str | None = None
    gallium_hud: str | None = None
    gamescope_args: list[str] | None = None
    gamescope_stats_path: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "AppProfile":
        known = {f for f in cls.__dataclass_fields__}
        clean = {k: v for k, v in (data or {}).items() if k in known}
        return cls(**clean)


def default_overlay_profiles() -> list[OverlayProfile]:
    return [
        OverlayProfile(name="default"),
        OverlayProfile(
            name="minimal",
            position="top-right",
            metrics=["fps", "cpu_usage", "gpu_usage"],
        ),
        OverlayProfile(
            name="full",
            position="bottom-left",
            graph=True,
            metrics=[
                "fps", "frametime", "cpu_usage", "cpu_temp", "cpu_power",
                "gpu_usage", "gpu_temp", "gpu_power", "gpu_mem_usage",
                "ram_percent", "net_up", "net_down",
            ],
        ),
    ]


def default_app_profiles() -> list[AppProfile]:
    return [
        AppProfile(
            name="Steam game",
            match=["steam_app_*"],
            overlay="default",
            fps_backend="vulkan_layer",
        ),
        AppProfile(
            name="Lutris game",
            match=["wine*", "lutris*"],
            overlay="full",
            fps_backend="vulkan_layer",
            gamemode=True,
        ),
    ]
