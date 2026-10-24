import os
import sys
from pathlib import Path

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
    app.setQuitOnLastWindowClosed(True)

    initial_file = None
    if len(sys.argv) > 1:
        candidate = Path(sys.argv[1]).expanduser().resolve()
        if candidate.is_file():
            initial_file = candidate

    orb = FloatingDropOrb(initial_file=initial_file)
    orb.show()

    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
