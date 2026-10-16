import sys
import os
from pathlib import Path

if getattr(sys, "frozen", False):
    base = Path(sys._MEIPASS)
    if str(base) not in sys.path:
        sys.path.insert(0, str(base))
else:
    root = str(Path(__file__).resolve().parent.parent)
    if root not in sys.path:
        sys.path.insert(0, root)


def main():
    if "--tui" in sys.argv:
        from src.main import MpmApp
        MpmApp().run()
        return 0
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    from src.gui import main as gui_main
    return gui_main()


if __name__ == "__main__":
    raise SystemExit(main())
