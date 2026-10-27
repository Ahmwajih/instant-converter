import os
import sys
from pathlib import Path

if "LD_LIBRARY_PATH_ORIG" not in os.environ:
    os.environ["LD_LIBRARY_PATH_ORIG"] = os.environ.get("LD_LIBRARY_PATH", "")

if sys.platform.startswith("linux") and "DISPLAY" in os.environ:
    os.environ.setdefault("QT_QPA_PLATFORM", "xcb")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from ui.main_window import FloatingDropOrb
from ui.notifications import create_app_icon


def main() -> int:
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    app.setApplicationName("instant-converter")
    app.setApplicationDisplayName("Instant Converter")
    app.setOrganizationName("InstantConverter")
    app.setDesktopFileName("instant-converter")
    app.setWindowIcon(create_app_icon())
    app.setQuitOnLastWindowClosed(False)

    # Support multiple files passed via OS Right-Click ("Send to Instant Converter") or CLI
    initial_files: list[Path] = []
    for arg in sys.argv[1:]:
        candidate = Path(arg).expanduser().resolve()
        if candidate.is_file():
            initial_files.append(candidate)

    orb = FloatingDropOrb(initial_files=initial_files)
    orb.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
