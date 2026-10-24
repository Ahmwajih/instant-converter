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


def _resolve_asset_icon() -> Path | None:
    base_dir = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parent.parent))
    candidate = base_dir / "assets" / "icon.png"
    return candidate if candidate.exists() else None


def create_app_icon() -> QIcon:
    asset_png = _resolve_asset_icon()
    if asset_png is not None:
        return QIcon(str(asset_png))

    # Fallback programmatic QPainter radial converter icon
    size = 128
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)

    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    # Outer badge
    painter.setBrush(QColor(24, 24, 27))
    painter.setPen(QPen(QColor(63, 63, 70), 3))
    painter.drawEllipse(4, 4, size - 8, size - 8)

    # 4 Radial slices
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

    # Inner hub
    painter.setBrush(QColor(24, 24, 27))
    painter.setPen(QPen(QColor(96, 165, 250), 2.5))
    painter.drawEllipse(36, 36, size - 72, size - 72)

    # Conversion arrows in center
    painter.setPen(Qt.PenStyle.NoPen)
    painter.setBrush(QColor(255, 255, 255))
    painter.drawRoundedRect(QRectF(48, 54, 24, 6), 2, 2)
    painter.drawPolygon(QPolygonF([QPointF(68, 50), QPointF(81, 57), QPointF(68, 64)]))
    painter.drawRoundedRect(QRectF(56, 68, 24, 6), 2, 2)
    painter.drawPolygon(QPolygonF([QPointF(60, 64), QPointF(47, 71), QPointF(60, 78)]))

    painter.end()
    return QIcon(pixmap)


def reveal_in_file_manager(file_path: Path) -> None:
    folder = file_path.parent if file_path.is_file() else file_path
    QDesktopServices.openUrl(QUrl.fromLocalFile(str(folder.resolve())))


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
