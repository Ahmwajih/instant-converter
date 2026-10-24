import math
from pathlib import Path
from typing import List
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QThread, Signal, QTimer
from PySide6.QtGui import QAction, QColor, QFont, QPainter, QPen, QRegion
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMenu,
    QSystemTrayIcon,
    QWidget,
)
from converter.detection import get_available_targets, is_supported
from converter.engine import convert_file
from ui.notifications import NotificationManager, create_app_icon, reveal_in_file_manager
from ui.radial_menu import RadialWheelRenderer


class ConversionWorker(QThread):
    succeeded = Signal(Path)
    failed = Signal(str)

    def __init__(self, source_path: Path, target_format: str) -> None:
        super().__init__()
        self.source_path = source_path
        self.target_format = target_format

    def run(self) -> None:
        try:
            out = convert_file(self.source_path, self.target_format)
            self.succeeded.emit(out)
        except Exception as exc:
            self.failed.emit(str(exc))


class FloatingDropOrb(QWidget):
    def __init__(self, initial_file: Path | None = None) -> None:
        super().__init__()
        self.setWindowTitle("Instant Converter")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)

        # Canvas large enough to host the radial wheel + bottom status pill
        self.setFixedSize(320, 360)
        self.orb_center = QPointF(160.0, 145.0)
        self.orb_radius = 44.0
        self.close_btn_center = QPointF(195.0, 108.0)
        self.close_btn_radius = 12.0
        self.pill_rect = QRect(15, 295, 290, 44)

        self.wheel = RadialWheelRenderer(inner_radius=50.0, outer_radius=132.0)

        # Interaction states
        self._press_global_pos: QPoint | None = None
        self._window_start_pos: QPoint | None = None
        self._is_dragging_window = False
        self._is_drag_hover = False
        self._is_busy = False

        self._menu_open = False
        self._options: List[str] = []
        self._hovered_slice = -1
        self._orb_hovered = False
        self._close_hovered = False
        self._pill_hovered = False

        self._pending_file: Path | None = None
        self._last_output_path: Path | None = None
        self._status_text = "Click Orb or Drop File"
        self._status_state = "idle"  # "idle" | "active" | "success" | "error"
        self._worker: ConversionWorker | None = None

        self.app_icon = create_app_icon()
        self.setWindowIcon(self.app_icon)

        # System Tray
        self.tray = QSystemTrayIcon(self.app_icon, self)
        self.tray.setToolTip("Instant Converter")
        self._context_menu = QMenu()

        open_action = QAction("Select File to Convert...", self)
        open_action.triggered.connect(self.prompt_file_dialog)
        self._context_menu.addAction(open_action)

        self.open_folder_action = QAction("Open Last Output Folder", self)
        self.open_folder_action.setEnabled(False)
        self.open_folder_action.triggered.connect(self._open_last_output_folder)
        self._context_menu.addAction(self.open_folder_action)

        self._context_menu.addSeparator()
        quit_action = QAction("Quit Instant Converter", self)
        quit_action.triggered.connect(QApplication.instance().quit)
        self._context_menu.addAction(quit_action)

        self.tray.setContextMenu(self._context_menu)
        self.tray.show()
        self.notifier = NotificationManager(self.tray)

        # Place near bottom-right of primary screen
        screen = QApplication.primaryScreen().availableGeometry()
        self.move(screen.right() - 340, screen.bottom() - 390)

        self._update_mask()

        if initial_file is not None:
            QTimer.singleShot(150, lambda: self.load_file(initial_file))

    def _update_mask(self) -> None:
        """Masks transparent areas so only visible widgets capture clicks."""
        if self._menu_open:
            r = int(self.wheel.outer_radius + 8)
            wheel_rect = QRect(
                int(self.orb_center.x() - r),
                int(self.orb_center.y() - r),
                r * 2,
                r * 2,
            )
            region = QRegion(wheel_rect, QRegion.RegionType.Ellipse)
        else:
            r = int(self.orb_radius + 6)
            orb_rect = QRect(
                int(self.orb_center.x() - r),
                int(self.orb_center.y() - r),
                r * 2,
                r * 2,
            )
            region = QRegion(orb_rect, QRegion.RegionType.Ellipse)
            close_rect = QRect(
                int(self.close_btn_center.x() - 14),
                int(self.close_btn_center.y() - 14),
                28,
                28,
            )
            region = region.united(QRegion(close_rect, QRegion.RegionType.Ellipse))

        region = region.united(QRegion(self.pill_rect))
        self.setMask(region)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # 1. Draw Radial Menu slices if a file is loaded
        if self._menu_open and self._options:
            self.wheel.draw(painter, self.orb_center, self._options, self._hovered_slice)

        # 2. Draw Center Orb
        if self._is_busy:
            bg_color = QColor(245, 158, 11, 240)
            border_color = QColor(253, 230, 138)
            center_label = "WAIT"
        elif self._is_drag_hover:
            bg_color = QColor(37, 99, 235, 245)
            border_color = QColor(191, 219, 254)
            center_label = "DROP"
        elif self._menu_open:
            bg_color = (
                QColor(239, 68, 68, 240)
                if self._orb_hovered
                else QColor(39, 39, 42, 245)
            )
            border_color = QColor(161, 161, 170)
            center_label = "CANCEL"
        else:
            bg_color = (
                QColor(37, 99, 235, 240)
                if self._orb_hovered
                else QColor(24, 24, 27, 235)
            )
            border_color = QColor(59, 130, 246, 240)
            center_label = "CONVERT"

        painter.setBrush(bg_color)
        painter.setPen(QPen(border_color, 3.0))
        painter.drawEllipse(self.orb_center, self.orb_radius, self.orb_radius)

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Sans Serif", 9, QFont.Weight.Bold))
        orb_text_rect = QRectF(
            self.orb_center.x() - self.orb_radius,
            self.orb_center.y() - self.orb_radius,
            self.orb_radius * 2,
            self.orb_radius * 2,
        )
        painter.drawText(orb_text_rect, Qt.AlignmentFlag.AlignCenter, center_label)

        # 3. Draw small Close ('x') badge when radial menu is closed
        if not self._menu_open:
            close_bg = (
                QColor(239, 68, 68, 245)
                if self._close_hovered
                else QColor(63, 63, 70, 230)
            )
            painter.setBrush(close_bg)
            painter.setPen(QPen(QColor(255, 255, 255, 180), 1.5))
            painter.drawEllipse(
                self.close_btn_center, self.close_btn_radius, self.close_btn_radius
            )
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
            close_rect = QRectF(
                self.close_btn_center.x() - self.close_btn_radius,
                self.close_btn_center.y() - self.close_btn_radius,
                self.close_btn_radius * 2,
                self.close_btn_radius * 2,
            )
            painter.drawText(close_rect, Qt.AlignmentFlag.AlignCenter, "✕")

        # 4. Draw Status Pill at the bottom
        if self._status_state == "success":
            pill_bg = (
                QColor(22, 163, 74, 245)
                if self._pill_hovered
                else QColor(21, 128, 61, 235)
            )
            pill_border = QColor(134, 239, 172)
        elif self._status_state == "error":
            pill_bg = QColor(185, 28, 28, 240)
            pill_border = QColor(252, 165, 165)
        elif self._status_state == "active":
            pill_bg = QColor(30, 58, 138, 235)
            pill_border = QColor(96, 165, 250)
        else:
            pill_bg = (
                QColor(39, 39, 42, 240)
                if self._pill_hovered
                else QColor(24, 24, 27, 225)
            )
            pill_border = QColor(82, 82, 91)

        painter.setBrush(pill_bg)
        painter.setPen(QPen(pill_border, 1.8))
        painter.drawRoundedRect(QRectF(self.pill_rect), 18.0, 18.0)

        painter.setPen(QColor(255, 255, 255))
        painter.setFont(QFont("Sans Serif", 9, QFont.Weight.DemiBold))
        painter.drawText(
            QRectF(self.pill_rect.adjusted(10, 0, -10, 0)),
            Qt.AlignmentFlag.AlignCenter,
            self._status_text,
        )

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            self._is_drag_hover = True
            self._status_text = "Release to Load File"
            self._status_state = "active"
            self.update()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        self._is_drag_hover = False
        if not self._menu_open:
            self._status_text = "Click Orb or Drop File"
            self._status_state = "idle"
        self.update()

    def dropEvent(self, event) -> None:
        self._is_drag_hover = False
        urls = event.mimeData().urls()
        if not urls:
            return
        file_path = Path(urls[0].toLocalFile())
        self.load_file(file_path)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_global_pos = event.globalPosition().toPoint()
            self._window_start_pos = self.frameGeometry().topLeft()
            self._is_dragging_window = False
        elif event.button() == Qt.MouseButton.RightButton:
            self._context_menu.popup(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()

        # Handle window dragging if left mouse button is held down
        if (
            self._press_global_pos is not None
            and event.buttons() & Qt.MouseButton.LeftButton
        ):
            delta = event.globalPosition().toPoint() - self._press_global_pos
            if delta.manhattanLength() > 6:
                self._is_dragging_window = True
                self.move(self._window_start_pos + delta)
            return

        # Hover states
        dist_orb = math.hypot(
            pos.x() - self.orb_center.x(), pos.y() - self.orb_center.y()
        )
        self._orb_hovered = dist_orb <= self.orb_radius

        dist_close = math.hypot(
            pos.x() - self.close_btn_center.x(), pos.y() - self.close_btn_center.y()
        )
        self._close_hovered = (not self._menu_open) and (
            dist_close <= self.close_btn_radius
        )

        self._pill_hovered = self.pill_rect.contains(pos.toPoint())

        if self._menu_open:
            new_slice = self.wheel.hit_test(self.orb_center, pos, self._options)
            if new_slice != self._hovered_slice:
                self._hovered_slice = new_slice
                if 0 <= new_slice < len(self._options):
                    fmt = self._options[new_slice]
                    self._status_text = f"Click to convert → {fmt}"
                elif self._pending_file:
                    self._status_text = f"{self._pending_file.name[:22]} → Pick format"

        self.update()

    def mouseReleaseEvent(self, event) -> None:
        if event.button() != Qt.MouseButton.LeftButton:
            return

        was_dragging = self._is_dragging_window
        self._press_global_pos = None
        self._is_dragging_window = False

        if was_dragging:
            return

        pos = event.position()

        # 1. Clicked Close ('x') button
        dist_close = math.hypot(
            pos.x() - self.close_btn_center.x(), pos.y() - self.close_btn_center.y()
        )
        if not self._menu_open and dist_close <= self.close_btn_radius:
            QApplication.instance().quit()
            return

        # 2. Clicked Status Pill
        if self.pill_rect.contains(pos.toPoint()):
            if self._status_state == "success" and self._last_output_path:
                reveal_in_file_manager(self._last_output_path)
            else:
                self.prompt_file_dialog()
            return

        # 3. Clicked Center Orb
        dist_orb = math.hypot(
            pos.x() - self.orb_center.x(), pos.y() - self.orb_center.y()
        )
        if dist_orb <= self.orb_radius:
            if self._menu_open:
                self.close_radial_menu()
            else:
                self.prompt_file_dialog()
            return

        # 4. Clicked a Radial Format Slice
        if self._menu_open:
            clicked_idx = self.wheel.hit_test(self.orb_center, pos, self._options)
            if 0 <= clicked_idx < len(self._options):
                chosen_format = self._options[clicked_idx]
                self._start_conversion(chosen_format)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape and self._menu_open:
            self.close_radial_menu()

    def close_radial_menu(self) -> None:
        self._menu_open = False
        self._options = []
        self._hovered_slice = -1
        self._pending_file = None
        self._status_text = "Click Orb or Drop File"
        self._status_state = "idle"
        self._update_mask()
        self.update()

    def prompt_file_dialog(self) -> None:
        if self._is_busy:
            return
        file_str, _ = QFileDialog.getOpenFileName(
            self,
            "Select File to Convert",
            str(Path.home()),
            "All Supported (*.png *.jpg *.jpeg *.webp *.bmp *.ico *.tiff *.gif "
            "*.pdf *.docx *.txt *.md *.html "
            "*.mp4 *.mkv *.webm *.avi *.mov *.mp3 *.wav *.flac *.ogg *.m4a);;"
            "Images (*.png *.jpg *.jpeg *.webp *.bmp *.ico *.tiff *.gif);;"
            "Documents (*.pdf *.docx *.txt *.md *.html);;"
            "Video & Audio (*.mp4 *.mkv *.webm *.avi *.mov *.mp3 *.wav *.flac *.ogg *.m4a)",
        )
        if file_str:
            self.load_file(Path(file_str))
    def load_file(self, file_path: Path) -> None:
        if not file_path.is_file():
            self._status_text = "Error: Not a valid file"
            self._status_state = "error"
            self.update()
            return

        if not is_supported(file_path):
            self._status_text = f"Unsupported: {file_path.suffix}"
            self._status_state = "error"
            self.notifier.notify_error(
                "Unsupported Format",
                f"Format '{file_path.suffix}' is not supported.",
            )
            self.update()
            return

        self._pending_file = file_path
        self._options = get_available_targets(file_path)
        self._hovered_slice = -1
        self._menu_open = True
        self._status_text = f"{file_path.name[:22]} → Pick format"
        self._status_state = "active"
        self._update_mask()
        self.update()

    def _start_conversion(self, target_format: str) -> None:
        if not self._pending_file or self._is_busy:
            return

        source_file = self._pending_file
        self._menu_open = False
        self._options = []
        self._is_busy = True
        self._status_text = f"Converting to {target_format}..."
        self._status_state = "active"
        self._update_mask()
        self.update()

        self._worker = ConversionWorker(source_file, target_format)
        self._worker.succeeded.connect(self._on_conversion_success)
        self._worker.failed.connect(self._on_conversion_error)
        self._worker.start()

    def _on_conversion_success(self, output_path: Path) -> None:
        self._is_busy = False
        self._last_output_path = output_path
        self.open_folder_action.setEnabled(True)
        self._status_text = f"✓ {output_path.name[:18]} (Click to open)"
        self._status_state = "success"
        self.notifier.notify_success(
            "Conversion Complete",
            f"Saved to {output_path}",
        )
        self.update()

    def _on_conversion_error(self, error_msg: str) -> None:
        self._is_busy = False
        self._status_text = "Conversion failed (Click to retry)"
        self._status_state = "error"
        self.notifier.notify_error("Conversion Failed", error_msg)
        self.update()

    def _open_last_output_folder(self) -> None:
        if self._last_output_path:
            reveal_in_file_manager(self._last_output_path)
