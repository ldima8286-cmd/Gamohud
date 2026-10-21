import os
import sys
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
    argv = sys.argv[1:]
    if argv and argv[0] in ("run", "--run"):
        from src.run_wrapper import main as run_main
        return run_main(argv[1:])
    if argv and argv[0] in ("presentmon-helper", "--presentmon-helper"):
        from src.fps.presentmon_helper import main as pm_main
        return pm_main(argv[1:])
    os.environ.setdefault("QT_ENABLE_HIGHDPI_SCALING", "1")
    from src.gui import main as gui_main
    return gui_main()


if __name__ == "__main__":
    raise SystemExit(main())
