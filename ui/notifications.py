from pathlib import Path
from PySide6.QtCore import QUrl
from PySide6.QtGui import QColor, QDesktopServices, QIcon, QPainter, QPixmap
from PySide6.QtWidgets import QSystemTrayIcon


def create_app_icon() -> QIcon:
    pixmap = QPixmap(64, 64)
    pixmap.fill(QColor(0, 0, 0, 0))
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    painter.setBrush(QColor(59, 130, 246))
    painter.setPen(QColor(255, 255, 255))
    painter.drawEllipse(4, 4, 56, 56)
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
