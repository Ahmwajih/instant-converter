import os
import shutil
import subprocess
import sys
from pathlib import Path
from PySide6.QtCore import Qt, QPointF, QRectF, QUrl
from PySide6.QtGui import (
    QColor,
    QDesktopServices,
    QIcon,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
    QPolygonF,
)
from PySide6.QtWidgets import QSystemTrayIcon

_PYINSTALLER_POLLUTED_VARS = (
    "LD_LIBRARY_PATH",
    "LD_PRELOAD",
    "QT_PLUGIN_PATH",
    "QML2_IMPORT_PATH",
    "QT_QPA_PLATFORM_PLUGIN_PATH",
    "GIO_MODULE_DIR",
    "GIO_EXTRA_MODULES",
    "GSETTINGS_SCHEMA_DIR",
    "GTK_PATH",
    "GTK_EXE_PREFIX",
    "GTK_DATA_PREFIX",
    "GDK_PIXBUF_MODULE_FILE",
    "GDK_PIXBUF_MODULEDIR",
    "PYTHONPATH",
    "PYTHONHOME",
)


def get_clean_env() -> dict[str, str]:
    """Removes all PyInstaller bundle environment variables so OS file managers never lag."""
    env = os.environ.copy()
    for var in _PYINSTALLER_POLLUTED_VARS:
        env.pop(var, None)
    orig_ld = env.pop("LD_LIBRARY_PATH_ORIG", "")
    if orig_ld:
        env["LD_LIBRARY_PATH"] = orig_ld
    return env


def _resolve_asset_icon() -> Path | None:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    candidate = base_dir / "assets" / "icon.png"
    return candidate if candidate.exists() else None


def create_app_icon() -> QIcon:
    asset_png = _resolve_asset_icon()
    if asset_png is not None:
        return QIcon(str(asset_png))

    size = 128
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    painter.setBrush(QColor(24, 24, 27))
    painter.setPen(QPen(QColor(63, 63, 70), 3))
    painter.drawEllipse(4, 4, size - 8, size - 8)

    slice_rect = QRectF(12, 12, size - 24, size - 24)
    colors = [
        (8, 74, QColor(59, 130, 246)),
        (98, 74, QColor(139, 92, 246)),
        (188, 74, QColor(16, 185, 129)),
        (278, 74, QColor(6, 182, 212)),
    ]
    painter.setPen(Qt.PenStyle.NoPen)
    for start_deg, span_deg, color in colors:
        path = QPainterPath()
        path.moveTo(size / 2, size / 2)
        path.arcTo(slice_rect, start_deg, span_deg)
        path.closeSubpath()
        painter.setBrush(color)
        painter.drawPath(path)

    painter.setBrush(QColor(24, 24, 27))
    painter.setPen(QPen(QColor(96, 165, 250), 2.5))
    painter.drawEllipse(36, 36, size - 72, size - 72)

    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255))
    painter.drawRoundedRect(QRectF(48, 54, 24, 6), 2, 2)
    painter.drawPolygon(QPolygonF([QPointF(68, 50), QPointF(81, 57), QPointF(68, 64)]))
    painter.drawRoundedRect(QRectF(56, 68, 24, 6), 2, 2)
    painter.drawPolygon(QPolygonF([QPointF(60, 64), QPointF(47, 71), QPointF(60, 78)]))

    painter.end()
    return QIcon(pixmap)


def reveal_in_file_manager(file_path: Path) -> None:
    """Opens the system file manager and selects the file in a detached, unpolluted session."""
    target = file_path.resolve()
    folder = target.parent if target.exists() and target.is_file() else target
    env = get_clean_env()

    try:
        if sys.platform.startswith("win"):
            if target.exists() and target.is_file():
                subprocess.Popen(["explorer.exe", f"/select,{target}"], env=env)
            else:
                subprocess.Popen(["explorer.exe", str(folder)], env=env)
            return

        if sys.platform.startswith("linux"):
            if shutil.which("nautilus") and target.exists() and target.is_file():
                subprocess.Popen(
                    ["nautilus", "--select", str(target)],
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return
            if shutil.which("xdg-open"):
                subprocess.Popen(
                    ["xdg-open", str(folder)],
                    env=env,
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                return
    except Exception:
        pass

    QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder)))


class NotificationManager:
    def __init__(self, tray_icon: QSystemTrayIcon) -> None:
        self.tray_icon = tray_icon

    def notify_success(self, title: str, message: str) -> None:
        if self.tray_icon.isVisible() and self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(
                title,
                message,
                QSystemTrayIcon.MessageIcon.Information,
                3500,
            )

    def notify_error(self, title: str, message: str) -> None:
        if self.tray_icon.isVisible() and self.tray_icon.supportsMessages():
            self.tray_icon.showMessage(
                title,
                message,
                QSystemTrayIcon.MessageIcon.Critical,
                4500,
            )
