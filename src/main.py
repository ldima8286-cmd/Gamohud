from textual.app import App, ComposeResult
from textual.widgets import Header, Footer, ListView, ListItem, Label, TextArea, Tabs, Tab, Static
from textual.containers import Horizontal, Vertical
from pathlib import Path
from textual.reactive import reactive
import os

MANGOHUD_DIR = Path.home() / ".config" / "MangoHud"

class PresetList(ListView):
    pass

class MpmApp(App):
    CSS = """
    Screen {
        background: $surface;
    }
    #sidebar {
        width: 30%;
        min-width: 20;
        max-width: 40%;
        background: $panel;
        border: solid $primary;
    }
    #content {
        width: 70%;
        background: $surface;
        border: solid $primary;
    }
    """

    def compose(self) -> ComposeResult:
        yield Header()
        with Horizontal():
            with Vertical(id="sidebar"):
                yield Label("Presets", id="presets-title")
                yield PresetList()
            with Vertical(id="content"):
                yield Label("Preview", id="preview-title")
                yield TextArea.code_editor(language="ini", read_only=True)
        yield Footer()

    def on_mount(self) -> None:
        lv = self.query_one(PresetList)
        lv.clear()
        presets = self.load_presets()
        for p in presets:
            lv.append(ListItem(Label(p.name)))
        if presets:
            self.show_preview(presets[0])

    def load_presets(self):
        if not MANGOHUD_DIR.exists():
            return []
        return sorted([f for f in MANGOHUD_DIR.glob("*.conf") if f.is_file()])

    def show_preview(self, path: Path):
        ta = self.query_one(TextArea)
        try:
            ta.load_text(path.read_text(encoding="utf-8", errors="replace"))
        except Exception as e:
            ta.load_text(f"# Error reading {path.name}: {e}")

if __name__ == "__main__":
    MpmApp().run()
