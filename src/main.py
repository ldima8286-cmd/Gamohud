from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label, TextArea, Button, Input, ModalScreen, Static
from textual.containers import Horizontal, Vertical, Grid
from pathlib import Path
from textual import on

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
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("Presets", id="title")
                yield ListView(id="presets")
                yield Button("Refresh", id="refresh")
                yield Button("New from current", id="new_from_current")
                yield Button("Apply", id="apply", variant="primary")
                yield Button("Rename", id="rename")
                yield Button("Delete", id="delete", variant="error")
            with Vertical(id="content"):
                yield Label("Preview / Editor", id="title")
                yield TextArea.code_editor(language="ini", id="editor")
        yield Footer()

    def on_mount(self) -> None:
        self.load_and_fill()

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
        lv = self.query_one("#presets", ListView)
        lv.clear()
        self.current_preset = None
        for d, f in self.load_presets():
            lv.append(ListItem(Label(f"{f.name}")))
        if self.load_presets():
            _, first = self.load_presets()[0]
            self.current_preset = first
            self.show_preset(first)
            lv.focus()

    def show_preset(self, path: Path):
        ta = self.query_one("#editor", TextArea)
        try:
            ta.load_text(path.read_text(encoding="utf-8", errors="replace"))
        except Exception as e:
            ta.load_text(f"# Error reading {path}: {e}")

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

    def on_button_pressed(self, event: Button.Pressed) -> None:
        bid = event.button.id
        if bid == "refresh":
            self.load_and_fill()
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


if __name__ == "__main__":
    MpmApp().run()
