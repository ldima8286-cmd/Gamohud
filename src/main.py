from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label, TextArea, Button
from textual.containers import Horizontal, Vertical
from pathlib import Path
from textual import events

MANGOHUD_DIR = Path.home() / ".config" / "MangoHud"
MANGOHUD_CONF = MANGOHUD_DIR / "MangoHud.conf"


class PresetList(ListView):
    pass


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
                yield PresetList(id="presets")
                yield Button("Refresh", id="refresh")
                yield Button("New from current", id="new_from_current")
                yield Button("Apply", id="apply", variant="primary")
                yield Button("Delete", id="delete", variant="error")
            with Vertical(id="content"):
                yield Label("Preview", id="title")
                yield TextArea.code_editor(language="ini", read_only=True, id="preview")
        yield Footer()

    def on_mount(self) -> None:
        self.load_and_fill()

    def load_presets(self):
        if not MANGOHUD_DIR.exists():
            return []
        files = [f for f in MANGOHUD_DIR.glob("*.conf") if f.is_file()]
        files = sorted(files, key=lambda p: p.name.lower())
        return files

    def load_and_fill(self):
        lv = self.query_one("#presets", PresetList)
        lv.clear()
        for p in self.load_presets():
            lv.append(ListItem(Label(p.name)))
        if self.load_presets():
            first = self.load_presets()[0]
            self.current_preset = first
            self.show_preview(first)
            lv.focus()

    def show_preview(self, path: Path):
        ta = self.query_one("#preview", TextArea)
        try:
            ta.load_text(path.read_text(encoding="utf-8", errors="replace"))
        except Exception as e:
            ta.load_text(f"# Error reading {path}: {e}")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        if not event.item:
            return
        label = event.item.query_one(Label)
        name = label.renderable
        if isinstance(name, str):
            self.current_preset = MANGOHUD_DIR / name
            self.show_preview(self.current_preset)

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

    def apply_preset(self):
        if not self.current_preset:
            return
        try:
            MANGOHUD_DIR.mkdir(parents=True, exist_ok=True)
            if self.current_preset.exists():
                content = self.current_preset.read_text(encoding="utf-8", errors="replace")
                MANGOHUD_CONF.write_text(content, encoding="utf-8")
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
        try:
            MANGOHUD_DIR.mkdir(parents=True, exist_ok=True)
            if MANGOHUD_CONF.exists():
                content = MANGOHUD_CONF.read_text(encoding="utf-8", errors="replace")
            else:
                content = "# MangoHud preset\n"
            name = f"preset_{len(list(self.load_presets())) + 1}.conf"
            p = MANGOHUD_DIR / name
            i = 1
            while p.exists():
                i += 1
                p = MANGOHUD_DIR / f"preset_{len(list(self.load_presets())) + i}.conf"
            p.write_text(content, encoding="utf-8")
            self.load_and_fill()
        except Exception:
            pass


if __name__ == "__main__":
    MpmApp().run()
