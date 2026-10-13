import re
from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label, TextArea, Button, Input, Static, Tabs, Tab
from textual.containers import Horizontal, Vertical, Grid
from textual.screen import ModalScreen
from pathlib import Path
from textual import on
try:
    from src.games import find_steam_games
except Exception:
    def find_steam_games(): return []

MANGOHUD_DIRS = [
    Path.home() / ".config" / "MangoHud",
]


class NameInput(ModalScreen[str]):
    def compose(self) -> ComposeResult:
        with Grid():
            yield Static("Preset name (без .conf)", id="question")
            yield Input(placeholder="my_preset", id="name")
            yield Button("OK", variant="primary", id="ok")
            yield Button("Cancel", id="cancel")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "ok":
            name = self.query_one("#name", Input).value.strip()
            if name and not name.endswith(".conf"):
                name += ".conf"
            if name:
                self.dismiss(name)
                return
        self.dismiss("")

    @on(Input.Submitted)
    def on_input_submitted(self, event: Input.Submitted) -> None:
        name = event.value.strip()
        if name and not name.endswith(".conf"):
            name += ".conf"
        self.dismiss(name if name else "")


class ProfileSelect(ModalScreen[str]):
    def __init__(self, options):
        super().__init__()
        self.options = options

    def compose(self) -> ComposeResult:
        with Grid():
            yield Static("Game Mode profile", id="question")
            yield ListView(id="profile_list")
            yield Button("Cancel", id="cancel")

    def on_mount(self) -> None:
        try:
            lv = self.query_one("#profile_list", ListView)
            for o in self.options:
                lv.append(ListItem(Label(o)))
            lv.focus()
        except Exception:
            pass

    @on(ListView.Selected)
    def on_selected(self, event: ListView.Selected) -> None:
        if not event.item:
            return
        label = event.item.query_one(Label)
        name = str(label.renderable) if hasattr(label, "renderable") else ""
        self.dismiss(name)

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "cancel":
            self.dismiss("")


class MpmApp(App):
    CSS = """
    #sidebar {
        width: 30%;
        background: $panel;
        border-right: solid $accent;
    }
    #content {
        width: 70%;
    }
    #title {
        padding: 1 0 1 1;
        background: $boost;
        text-style: bold;
    }
    Button {
        margin: 0 1 1 1;
    }
    """

    current_preset: Path | None = None

    def compose(self) -> ComposeResult:
        yield Header(show_clock=True)
        with Tabs():
            yield Tab("Monitoring", id="tab_monitor")
            yield Tab("Presets", id="tab_presets")
            yield Tab("Games", id="tab_games")
            yield Tab("Game Mode", id="tab_gamemode")
            yield Tab("Dashboard", id="tab_dashboard")
        with Vertical(id="monitor_view"):
            yield Label("Real-time Monitor", id="title_monitor")
            yield Label("CPU: --%", id="stat_cpu")
            yield Label("RAM: --/-- GB (--%)", id="stat_ram")
            yield Label("Swap: --%", id="stat_swap")
            yield Label("Temp: --°C", id="stat_temp")
        with Horizontal(id="presets_view") as pv:
            pv.styles.display = "none"
            with Vertical(id="sidebar"):
                yield Label("Presets", id="title")
                yield Input(placeholder="Filter...", id="filter")
                yield ListView(id="presets")
                yield Button("Refresh", id="refresh")
                yield Button("New from current", id="new_from_current")
                yield Button("Apply", id="apply", variant="primary")
                yield Button("Rename", id="rename")
                yield Button("Delete", id="delete", variant="error")
            with Vertical(id="content"):
                yield Label("Preview / Editor", id="title")
                yield TextArea.code_editor(language="ini", id="editor")
        with Vertical(id="games_view") as gv:
            gv.styles.display = "none"
            yield Label("Games (WIP)", id="title")
            yield ListView(id="games_list")
            yield Button("Bind preset to selected", id="bind_preset")
            yield Button("Bind Game Mode profile", id="bind_gm")
            yield Button("Launch with preset", id="launch_game")
            yield Button("Launch with preset + Game Mode", id="launch_full")
        with Vertical(id="gamemode_view") as gm:
            gm.styles.display = "none"
            yield Label("Game Mode Profiles", id="title_gamemode")
            yield ListView(id="gm_list")
            yield Button("New profile", id="gm_new")
            yield Button("Delete profile", id="gm_del")
            yield Button("Run with profile", id="gm_run")
        with Vertical(id="dashboard_view") as db:
            db.styles.display = "none"
            yield Label("Dashboard", id="title_dash")
            yield Label("Active MangoHud.conf:", id="title_active")
            yield TextArea.code_editor(language="ini", read_only=True, id="active_conf")
        yield Footer()

    def on_mount(self) -> None:
        self.load_and_fill()
        self.load_gm()
        self.set_interval(1.0, self.update_monitor)
        self.update_monitor()

    def all_preset_dirs(self):
        dirs = []
        for d in MANGOHUD_DIRS:
            if d.exists():
                dirs.append(d)
        # Flatpak
        var_app = Path.home() / ".var" / "app"
        if var_app.exists():
            for p in var_app.iterdir():
                d = p / "config" / "MangoHud"
                if d.exists() and d not in dirs:
                    dirs.append(d)
        # ensure default exists
        MANGOHUD_DIRS[0].mkdir(parents=True, exist_ok=True)
        if MANGOHUD_DIRS[0] not in dirs:
            dirs.append(MANGOHUD_DIRS[0])
        return dirs

    def load_presets(self):
        presets = []
        for d in self.all_preset_dirs():
            for f in d.glob("*.conf"):
                if f.is_file():
                    presets.append((d, f))
        presets.sort(key=lambda x: x[1].name.lower())
        return presets

    def load_and_fill(self):
        self.apply_filter()
        lv = self.query_one("#presets", ListView)
        if lv.children:
            lv.index = 0
            # trigger selection logic


    def show_preset(self, path: Path):
        ta = self.query_one("#editor", TextArea)
        try:
            ta.load_text(path.read_text(encoding="utf-8", errors="replace"))
        except Exception as e:
            ta.load_text(f"# Error reading {path}: {e}")


    def apply_filter(self):
        filt = self.query_one("#filter", Input).value.lower().strip()
        lv = self.query_one("#presets", ListView)
        lv.clear()
        for _, f in self.load_presets():
            if not filt or filt in f.name.lower():
                lv.append(ListItem(Label(f.name)))
        if filt:
            # select first if exists
            pass

    @on(Input.Changed, "#filter")
    def on_filter_changed(self, event: Input.Changed) -> None:
        self.apply_filter()

    @on(ListView.Selected)
    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not event.item:
            return
        label = event.item.query_one(Label)
        name = label.renderable
        if isinstance(name, str):
            for _, f in self.load_presets():
                if f.name == name:
                    self.current_preset = f
                    self.show_preset(f)
                    break


    # handle games buttons
    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "bind_preset":
            self.bind_preset_to_game()
            return
        if bid == "bind_gm":
            self.bind_gm_to_game()
            return
        if bid == "launch_game":
            self.launch_game_with_preset()
            return
        if bid == "launch_full":
            self.launch_game_with_preset(use_gamemode=True)
            return
        # fallback to existing
        if bid == "gm_new":
            self.gm_new()
            return
        if bid == "gm_del":
            self.gm_del()
            return
        if bid == "gm_run":
            self.gm_run()
            return
        if bid == "refresh":
            self.load_and_fill()
            return
        elif bid == "apply":
            self.apply_preset()
        elif bid == "delete":
            self.delete_preset()
        elif bid == "new_from_current":
            self.new_from_current()
        elif bid == "rename":
            self.rename_preset()


    def apply_preset(self):
        if not self.current_preset:
            return
        try:
            target_dir = MANGOHUD_DIRS[0]
            target_dir.mkdir(parents=True, exist_ok=True)
            content = self.query_one("#editor", TextArea).text
            (target_dir / "MangoHud.conf").write_text(content, encoding="utf-8")
        except Exception:
            pass

    def delete_preset(self):
        if not self.current_preset:
            return
        try:
            if self.current_preset.exists():
                self.current_preset.unlink()
            self.load_and_fill()
        except Exception:
            pass

    def new_from_current(self):
        def on_name(n):
            if not n:
                return
            target = MANGOHUD_DIRS[0]
            target.mkdir(parents=True, exist_ok=True)
            p = target / n
            try:
                content = self.query_one("#editor", TextArea).text
                p.write_text(content, encoding="utf-8")
            except Exception:
                p.write_text("", encoding="utf-8")
            self.load_and_fill()
        self.push_screen(NameInput(), on_name)

    def rename_preset(self):
        if not self.current_preset:
            return
        def on_name(n):
            if not n or not self.current_preset:
                return
            try:
                newp = self.current_preset.parent / n
                self.current_preset.rename(newp)
                self.current_preset = newp
                self.load_and_fill()
            except Exception:
                pass
        self.push_screen(NameInput(), on_name)


    def update_monitor(self):
        try:
            from src.monitor import get_stats
            st = get_stats()
            self.query_one("#stat_cpu").update(f"CPU: {st['cpu']}%")
            self.query_one("#stat_ram").update(f"RAM: {st['ram_used']}/{st['ram_total']} GB ({st['ram_percent']}%)")
            self.query_one("#stat_swap").update(f"Swap: {st['swap_percent']}%")
            self.query_one("#stat_temp").update(f"Temp: {st['temp']}°C" if st['temp'] is not None else "Temp: N/A")
        except Exception:
            pass

    @on(Tabs.TabActivated)
    def on_tabs_tab_activated(self, event: Tabs.TabActivated) -> None:
        tid = event.tab.id
        self.query_one("#monitor_view").styles.display = "block" if tid == "tab_monitor" else "none"
        self.query_one("#presets_view").styles.display = "block" if tid == "tab_presets" else "none"
        self.query_one("#games_view").styles.display = "block" if tid == "tab_games" else "none"
        self.query_one("#gamemode_view").styles.display = "block" if tid == "tab_gamemode" else "none"
        self.query_one("#dashboard_view").styles.display = "block" if tid == "tab_dashboard" else "none"
        if tid == "tab_games":
            self.load_games()

    def load_games(self):
        lv = self.query_one("#games_list", ListView)
        lv.clear()
        for g in find_steam_games():
            lv.append(ListItem(Label(f"{g.name} [{g.launcher}] {g.appid}")))

    def _get_selected_game(self):
        lv = self.query_one("#games_list", ListView)
        if lv.index is not None and lv.children:
            item = lv.children[lv.index]
            label = item.query_one(Label)
            return str(label.renderable) if hasattr(label, 'renderable') else ""


    def _get_selected_gm(self):
        try:
            lv = self.query_one("#gm_list", ListView)
            if lv.index is not None and 0 <= lv.index < len(lv.children):
                item = lv.children[lv.index]
                label = item.query_one(Label)
                return str(label.renderable) if hasattr(label, 'renderable') else ""
        except Exception:
            pass
        return ""

    def bind_preset_to_game(self):
        sel = self._get_selected_game()
        if not sel:
            return
        m = re.search(r'(\d+)$', sel)
        appid = m.group(1) if m else sel
        if self.current_preset:
            binds = load_bindings()
            old = next((b for b in binds if b.game_key == appid), None)
            binds = [b for b in binds if not (b.game_key == appid)]
            binds.append(Binding(
                game_key=appid,
                launcher='steam',
                preset=self.current_preset.name,
                gamemode_profile=old.gamemode_profile if old else "",
            ))
            save_bindings(binds)

    def bind_gm_to_game(self):
        sel = self._get_selected_game()
        if not sel:
            return
        m = re.search(r'(\d+)$', sel)
        appid = m.group(1) if m else sel
        try:
            from src.gamemode import load_profiles
            names = [p.name for p in load_profiles()]
        except Exception:
            names = []
        options = ["(none)"] + names

        def on_pick(name):
            if not name:
                return
            profile = "" if name == "(none)" else name
            binds = load_bindings()
            old = next((b for b in binds if b.game_key == appid), None)
            binds = [b for b in binds if not (b.game_key == appid)]
            binds.append(Binding(
                game_key=appid,
                launcher='steam',
                preset=old.preset if old else "",
                gamemode_profile=profile,
            ))
            save_bindings(binds)

        self.push_screen(ProfileSelect(options), on_pick)

    def apply_preset_by_name(self, name):
        p = MANGOHUD_DIRS[0] / name
        if not p.exists():
            for _, f in self.load_presets():
                if f.name == name:
                    p = f
                    break
        if not p.exists():
            return False
        try:
            target = MANGOHUD_DIRS[0] / "MangoHud.conf"
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text(p.read_text(encoding='utf-8', errors='replace'), encoding='utf-8')
            return True
        except Exception:
            return False

    def launch_game_with_preset(self, use_gamemode=False):
        sel = self._get_selected_game()
        if not sel:
            return
        m = re.search(r'(\d+)$', sel)
        appid = m.group(1) if m else sel
        b = get_binding(appid)
        preset_name = ""
        gm_name = ""
        if b:
            preset_name = b.preset or ""
            gm_name = b.gamemode_profile or ""
        if preset_name:
            self.apply_preset_by_name(preset_name)

        import subprocess, os
        cmd = ['steam', f'steam://rungameid/{appid}']
        env = dict(os.environ)

        profile = None
        if use_gamemode and gm_name:
            try:
                from src.gamemode import load_profiles, build_env, run_kill, find_gamemoderun
                profile = next((p for p in load_profiles() if p.name == gm_name), None)
                if profile:
                    env = build_env(profile, env)
                    run_kill(profile)
                    gm = find_gamemoderun()
                    if gm and profile.gamemode:
                        cmd = [gm] + cmd
            except Exception:
                pass

        try:
            subprocess.Popen(cmd, env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            pass

    def gm_new(self):
        def on_name(n):
            if not n:
                return
            from src.gamemode import GMProfile, save_profiles, load_profiles
            ps = load_profiles()
            ps.append(GMProfile(name=n, gamemode=True))
            save_profiles(ps)
            self.load_gm()
        self.push_screen(NameInput(), on_name)

    def gm_del(self):
        sel = self._get_selected_gm()
        if not sel:
            return
        try:
            from src.gamemode import load_profiles, save_profiles
            ps = [p for p in load_profiles() if p.name != sel]
            save_profiles(ps)
            self.load_gm()
        except Exception:
            pass

    def gm_run(self):
        sel = self._get_selected_gm()
        if not sel:
            return
        try:
            from src.gamemode import load_profiles, run_profile, GMProfile
            ps = {p.name: p for p in load_profiles()}
            p = ps.get(sel)
            if not p:
                return
            # run an empty no-op command but with gamemode env/kill/restore? or just run shell with gamemode
            import subprocess
            run_profile(p, "echo 'gamemode profile run'", wait=False)
        except Exception:
            pass

    def load_gm(self):
        try:
            lv = self.query_one("#gm_list", ListView)
            lv.clear()
            from src.gamemode import load_profiles
            for p in load_profiles():
                lv.append(ListItem(Label(p.name)))
        except Exception:
            pass


if __name__ == "__main__":
    MpmApp().run()
