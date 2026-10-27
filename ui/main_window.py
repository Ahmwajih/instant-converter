from datetime import datetime
import json
import math
import shutil
from pathlib import Path
from typing import List, Sequence
from PySide6.QtCore import Qt, QPoint, QPointF, QRect, QRectF, QThread, Signal, QTimer
from PySide6.QtGui import QAction, QColor, QCursor, QFont, QKeySequence, QPainter, QPen, QRegion, QShortcut
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QMenu,
    QSystemTrayIcon,
    QWidget,
)
from converter.batch import combine_files_to_single_output
from converter.detection import get_available_targets, is_supported, resolve_output_path
from converter.engine import convert_file
from ui.notifications import NotificationManager, create_app_icon, reveal_in_file_manager
from ui.radial_menu import RadialWheelRenderer
from ui.settings_dialog import ConversionSettingsDialog


class ConversionWorker(QThread):
    succeeded = Signal(Path, str)
    failed = Signal(str)

    def __init__(
        self,
        source_paths: Sequence[Path],
        target_format: str,
        settings: dict | None = None,
    ) -> None:
        super().__init__()
        self.source_paths = list(source_paths)
        self.target_format = target_format
        self.settings = settings or {}

    def run(self) -> None:
        try:
            first = self.source_paths[0]
            action = self.target_format.upper()
            batch_mode = self.settings.get("batch_mode", "separate")
            edited_pdf = self.settings.get("edited_pdf_path")

            if edited_pdf and Path(edited_pdf).exists():
                tgt_ext = "pdf" if action in {"EDIT-PDF", "MERGE-PDF", "REDACT", "LOCK-PDF"} else self.target_format.lower().lstrip(".")
                suffix = "_combined" if (len(self.source_paths) > 1 and batch_mode == "combine") else "_edited"
                final_dest = resolve_output_path(first, tgt_ext, suffix_tag=suffix if tgt_ext == "pdf" else "")
                if tgt_ext == "pdf" and action != "LOCK-PDF":
                    shutil.copy2(edited_pdf, final_dest)
                    last_out = final_dest
                else:
                    last_out = convert_file(Path(edited_pdf), self.target_format, output_path=final_dest, settings=self.settings)
                self.succeeded.emit(last_out, f"✓ {last_out.name[:18]} (Open)")
                return

            if len(self.source_paths) > 1 and (batch_mode == "combine" or action in {"MERGE-PDF", "ZIP"}):
                combined_out = combine_files_to_single_output(
                    self.source_paths, self.target_format, settings=self.settings
                )
                self.succeeded.emit(
                    combined_out,
                    f"✓ Combined {len(self.source_paths)} → {combined_out.name[:14]}",
                )
                return

            last_out = None
            for src in self.source_paths:
                last_out = convert_file(src, self.target_format, settings=self.settings)

            assert last_out is not None
            if len(self.source_paths) > 1:
                summary = f"✓ {len(self.source_paths)} files → .{self.target_format.lower()} (Open)"
            else:
                orig_sz = first.stat().st_size
                new_sz = last_out.stat().st_size if last_out.exists() else orig_sz
                if action == "COMPRESS" and orig_sz > 0 and new_sz < orig_sz:
                    saved_pct = int((1.0 - (new_sz / orig_sz)) * 100)
                    summary = f"✓ Saved -{saved_pct}% ({last_out.name[:14]})"
                else:
                    summary = f"✓ {last_out.name[:18]} (Open)"

            self.succeeded.emit(last_out, summary)
        except Exception as exc:
            self.failed.emit(str(exc))


class FloatingDropOrb(QWidget):
    def __init__(
        self,
        initial_file: Path | None = None,
        initial_files: Sequence[Path] | None = None,
    ) -> None:
        super().__init__()
        self.setWindowTitle("Instant Converter")
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
        )
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setAcceptDrops(True)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.setFixedSize(330, 395)
        self.orb_center = QPointF(165.0, 148.0)
        self.orb_radius = 44.0
        self.close_btn_center = QPointF(202.0, 110.0)
        self.close_btn_radius = 12.0

        # 3 Interactive Action Chips: Formats/Tools, Fast/Live Modif, and Clipboard Paste
        self.mode_btn_rect = QRect(15, 290, 108, 30)
        self.live_btn_rect = QRect(129, 290, 108, 30)
        self.paste_btn_rect = QRect(243, 290, 72, 30)
        self.pill_rect = QRect(15, 330, 300, 44)

        self.wheel = RadialWheelRenderer(inner_radius=50.0, outer_radius=134.0)

        self._press_global_pos: QPoint | None = None
        self._window_start_pos: QPoint | None = None
        self._is_dragging_window = False
        self._is_drag_hover = False
        self._is_busy = False

        self._wheel_mode = "convert"
        self._live_modif = False
        self._menu_open = False
        self._options: List[str] = []
        self._hovered_slice = -1
        self._orb_hovered = False
        self._close_hovered = False
        self._pill_hovered = False

        self._pending_files: List[Path] = []
        self._last_output_path: Path | None = None
        self._last_dir: str = str(Path.home())
        self._status_text = "Click, Drop, or Paste (Ctrl+V)"
        self._status_state = "idle"
        self._worker: ConversionWorker | None = None

        self.app_icon = create_app_icon()
        self.setWindowIcon(self.app_icon)

        # Keyboard shortcut: Ctrl+V pastes clipboard image/text/files directly onto the orb
        self._paste_shortcut = QShortcut(QKeySequence.StandardKey.Paste, self)
        self._paste_shortcut.activated.connect(self.paste_from_clipboard)

        self.tray = QSystemTrayIcon(self.app_icon, self)
        self.tray.setToolTip("Instant Converter v3.0")
        self._context_menu = QMenu()

        open_action = QAction("Select File(s) to Convert...", self)
        open_action.triggered.connect(self.prompt_file_dialog)
        self._context_menu.addAction(open_action)

        paste_action = QAction("Paste from Clipboard (Ctrl+V)", self)
        paste_action.triggered.connect(self.paste_from_clipboard)
        self._context_menu.addAction(paste_action)

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

        startup_list: list[Path] = []
        if initial_files:
            startup_list.extend(initial_files)
        elif initial_file:
            startup_list.append(initial_file)

        screen = QApplication.primaryScreen().availableGeometry()
        if startup_list:
            # When launched via OS Right-Click ("Send to Instant Converter"), appear near mouse cursor
            cursor_pt = QCursor.pos()
            x = max(screen.left() + 10, min(cursor_pt.x() - 165, screen.right() - 340))
            y = max(screen.top() + 10, min(cursor_pt.y() - 150, screen.bottom() - 405))
            self.move(x, y)
            QTimer.singleShot(120, lambda: self.load_files(startup_list))
        else:
            self.move(screen.right() - 350, screen.bottom() - 420)

        self._update_mask()

    def _update_mask(self) -> None:
        if self._menu_open:
            r = int(self.wheel.outer_radius + 10)
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

        region = region.united(QRegion(self.mode_btn_rect))
        region = region.united(QRegion(self.live_btn_rect))
        region = region.united(QRegion(self.paste_btn_rect))
        region = region.united(QRegion(self.pill_rect))
        self.setMask(region)

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        if self._menu_open and self._options:
            self.wheel.draw(painter, self.orb_center, self._options, self._hovered_slice)

        if self._is_busy:
            bg_color = QColor(245, 158, 11, 240)
            border_color = QColor(253, 230, 138)
            center_label = "WAIT"
        elif self._is_drag_hover:
            bg_color = QColor(37, 99, 235, 245)
            border_color = QColor(191, 219, 254)
            center_label = "DROP"
        elif self._menu_open:
            bg_color = QColor(239, 68, 68, 240) if self._orb_hovered else QColor(39, 39, 42, 245)
            border_color = QColor(161, 161, 170)
            center_label = "CANCEL"
        else:
            if self._wheel_mode == "tools":
                bg_color = QColor(124, 58, 237, 240) if self._orb_hovered else QColor(24, 24, 27, 235)
                border_color = QColor(167, 139, 250, 240)
                center_label = "TOOLS"
            else:
                bg_color = QColor(37, 99, 235, 240) if self._orb_hovered else QColor(24, 24, 27, 235)
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

        if not self._menu_open:
            close_bg = QColor(239, 68, 68, 245) if self._close_hovered else QColor(63, 63, 70, 230)
            painter.setBrush(close_bg)
            painter.setPen(QPen(QColor(255, 255, 255, 180), 1.5))
            painter.drawEllipse(self.close_btn_center, self.close_btn_radius, self.close_btn_radius)
            painter.setPen(QColor(255, 255, 255))
            painter.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))
            close_rect = QRectF(
                self.close_btn_center.x() - self.close_btn_radius,
                self.close_btn_center.y() - self.close_btn_radius,
                self.close_btn_radius * 2,
                self.close_btn_radius * 2,
            )
            painter.drawText(close_rect, Qt.AlignmentFlag.AlignCenter, "✕")

        painter.setFont(QFont("Sans Serif", 8, QFont.Weight.Bold))

        # Chip 1: Wheel Mode
        mode_bg = QColor(109, 40, 217, 235) if self._wheel_mode == "tools" else QColor(37, 99, 235, 235)
        painter.setBrush(mode_bg)
        painter.setPen(QPen(QColor(147, 197, 253, 180), 1.2))
        painter.drawRoundedRect(QRectF(self.mode_btn_rect), 11.0, 11.0)
        mode_txt = "🛠️ TOOLS" if self._wheel_mode == "tools" else "🔄 FORMATS"
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(self.mode_btn_rect), Qt.AlignmentFlag.AlignCenter, mode_txt)

        # Chip 2: Live Modif Toggle
        live_bg = QColor(217, 119, 6, 235) if self._live_modif else QColor(39, 39, 42, 230)
        painter.setBrush(live_bg)
        painter.setPen(QPen(QColor(251, 191, 36 if self._live_modif else 90), 1.2))
        painter.drawRoundedRect(QRectF(self.live_btn_rect), 11.0, 11.0)
        live_txt = "🎛️ Live: ON" if self._live_modif else "⚡ 1-Click"
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(self.live_btn_rect), Qt.AlignmentFlag.AlignCenter, live_txt)

        # Chip 3: Clipboard Paste Button
        painter.setBrush(QColor(16, 185, 129, 230))
        painter.setPen(QPen(QColor(110, 231, 183, 190), 1.2))
        painter.drawRoundedRect(QRectF(self.paste_btn_rect), 11.0, 11.0)
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(QRectF(self.paste_btn_rect), Qt.AlignmentFlag.AlignCenter, "📋 Paste")

        # Status Pill
        if self._status_state == "success":
            pill_bg = QColor(22, 163, 74, 245) if self._pill_hovered else QColor(21, 128, 61, 235)
            pill_border = QColor(134, 239, 172)
        elif self._status_state == "error":
            pill_bg = QColor(185, 28, 28, 240)
            pill_border = QColor(252, 165, 165)
        elif self._status_state == "active":
            pill_bg = QColor(30, 58, 138, 235)
            pill_border = QColor(96, 165, 250)
        else:
            pill_bg = QColor(39, 39, 42, 240) if self._pill_hovered else QColor(24, 24, 27, 225)
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

    def paste_from_clipboard(self) -> None:
        """Converts screenshots, copied images, JSON/Markdown/text snippets, or copied files from clipboard."""
        if self._is_busy:
            return
        cb = QApplication.clipboard()
        mime = cb.mimeData()
        out_dir = Path.home() / "Downloads"
        if not out_dir.exists():
            out_dir = Path.home()
        stamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if mime.hasUrls():
            files = [Path(u.toLocalFile()) for u in mime.urls() if Path(u.toLocalFile()).is_file()]
            if files:
                self.load_files(files)
                return

        if mime.hasImage():
            qimg = cb.image()
            if not qimg.isNull():
                clip_png = out_dir / f"Clipboard_{stamp}.png"
                qimg.save(str(clip_png), "PNG")
                self.load_files([clip_png])
                return

        if mime.hasText():
            raw_text = mime.text().strip()
            if raw_text:
                ext = "txt"
                if (raw_text.startswith("{") and raw_text.endswith("}")) or (
                    raw_text.startswith("[") and raw_text.endswith("]")
                ):
                    try:
                        json.loads(raw_text)
                        ext = "json"
                    except Exception:
                        pass
                elif raw_text.startswith("# ") or "\n## " in raw_text:
                    ext = "md"

                clip_file = out_dir / f"Clipboard_{stamp}.{ext}"
                clip_file.write_text(raw_text, encoding="utf-8")
                self.load_files([clip_file])
                return

        self._status_text = "Clipboard is empty"
        self._status_state = "error"
        self.update()

    def dragEnterEvent(self, event) -> None:
        if event.mimeData().hasUrls():
            self._is_drag_hover = True
            count = len(event.mimeData().urls())
            self._status_text = f"Drop {count} file(s)" if count > 1 else "Release to Load File"
            self._status_state = "active"
            self.update()
            event.acceptProposedAction()

    def dragLeaveEvent(self, event) -> None:
        self._is_drag_hover = False
        if not self._menu_open:
            self._status_text = "Click, Drop, or Paste (Ctrl+V)"
            self._status_state = "idle"
        self.update()

    def dropEvent(self, event) -> None:
        self._is_drag_hover = False
        urls = event.mimeData().urls()
        if not urls:
            return
        files = [Path(u.toLocalFile()) for u in urls if Path(u.toLocalFile()).is_file()]
        if files:
            self._last_dir = str(files[0].parent)
            self.load_files(files)

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            self._press_global_pos = event.globalPosition().toPoint()
            self._window_start_pos = self.frameGeometry().topLeft()
            self._is_dragging_window = False
        elif event.button() == Qt.MouseButton.RightButton:
            self._context_menu.popup(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event) -> None:
        pos = event.position()

        if self._press_global_pos is not None and event.buttons() & Qt.MouseButton.LeftButton:
            delta = event.globalPosition().toPoint() - self._press_global_pos
            if delta.manhattanLength() > 6:
                self._is_dragging_window = True
                self.move(self._window_start_pos + delta)
            return

        dist_orb = math.hypot(pos.x() - self.orb_center.x(), pos.y() - self.orb_center.y())
        self._orb_hovered = dist_orb <= self.orb_radius

        dist_close = math.hypot(pos.x() - self.close_btn_center.x(), pos.y() - self.close_btn_center.y())
        self._close_hovered = (not self._menu_open) and (dist_close <= self.close_btn_radius)
        self._pill_hovered = self.pill_rect.contains(pos.toPoint())

        if self._menu_open:
            new_slice = self.wheel.hit_test(self.orb_center, pos, self._options)
            if new_slice != self._hovered_slice:
                self._hovered_slice = new_slice
                if 0 <= new_slice < len(self._options):
                    fmt = self._options[new_slice]
                    self._status_text = f"Click → {fmt}"
                elif self._pending_files:
                    label = f"{len(self._pending_files)} files" if len(self._pending_files) > 1 else self._pending_files[0].name[:20]
                    self._status_text = f"{label} → Pick slice"

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
        pt = pos.toPoint()

        dist_close = math.hypot(pos.x() - self.close_btn_center.x(), pos.y() - self.close_btn_center.y())
        if not self._menu_open and dist_close <= self.close_btn_radius:
            QApplication.instance().quit()
            return

        if self.mode_btn_rect.contains(pt):
            self._wheel_mode = "tools" if self._wheel_mode == "convert" else "convert"
            if self._menu_open and self._pending_files:
                self.load_files(self._pending_files)
            else:
                self.update()
            return

        if self.live_btn_rect.contains(pt):
            self._live_modif = not self._live_modif
            self.update()
            return

        if self.paste_btn_rect.contains(pt):
            self.paste_from_clipboard()
            return

        if self.pill_rect.contains(pt):
            if self._status_state == "success" and self._last_output_path:
                reveal_in_file_manager(self._last_output_path)
            else:
                self.prompt_file_dialog()
            return

        dist_orb = math.hypot(pos.x() - self.orb_center.x(), pos.y() - self.orb_center.y())
        if dist_orb <= self.orb_radius:
            if self._menu_open:
                self.close_radial_menu()
            else:
                self.prompt_file_dialog()
            return

        if self._menu_open:
            clicked_idx = self.wheel.hit_test(self.orb_center, pos, self._options)
            if 0 <= clicked_idx < len(self._options):
                chosen_format = self._options[clicked_idx]
                self._start_conversion(chosen_format)

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape and self._menu_open:
            self.close_radial_menu()
        elif event.matches(QKeySequence.StandardKey.Paste):
            self.paste_from_clipboard()

    def close_radial_menu(self) -> None:
        self._menu_open = False
        self._options = []
        self._hovered_slice = -1
        self._pending_files = []
        self._status_text = "Click, Drop, or Paste (Ctrl+V)"
        self._status_state = "idle"
        self._update_mask()
        self.update()

    def prompt_file_dialog(self) -> None:
        if self._is_busy:
            return
        files, _ = QFileDialog.getOpenFileNames(
            None,
            "Select File(s) to Convert or Combine",
            self._last_dir,
            "All Files (*);;"
            "Documents & PDF (*.pdf *.docx *.doc *.rtf *.odt *.txt *.md *.html *.ppt *.pptx *.epub);;"
            "Images (*.png *.jpg *.jpeg *.webp *.svg *.heic *.avif *.bmp *.ico *.tiff *.gif);;"
            "Spreadsheets & Data (*.xlsx *.xls *.ods *.csv *.tsv *.json *.yaml *.yml *.toml *.xml);;"
            "Audio & Video (*.mp4 *.mov *.mkv *.webm *.avi *.mp3 *.m4a *.wav *.flac *.ogg *.opus)",
            "",
            QFileDialog.Option.DontUseNativeDialog,
        )
        if files:
            paths = [Path(f) for f in files]
            self._last_dir = str(paths[0].parent)
            self.load_files(paths)

    def load_files(self, file_paths: Sequence[Path]) -> None:
        valid = [p for p in file_paths if p.is_file() and is_supported(p)]
        if not valid:
            self._status_text = "Unsupported file format"
            self._status_state = "error"
            self.update()
            return

        self._pending_files = valid
        first = valid[0]
        targets = list(get_available_targets(first, mode=self._wheel_mode))

        if len(valid) > 1:
            if "PDF" not in targets and first.suffix.lower() == ".pdf":
                targets.insert(0, "PDF")
            if "ZIP" not in targets:
                targets.append("ZIP")

        self._options = targets
        self._hovered_slice = -1
        self._menu_open = True
        label = f"{len(valid)} files" if len(valid) > 1 else first.name[:20]
        self._status_text = f"{label} → Pick slice"
        self._status_state = "active"
        self._update_mask()
        self.update()

    def _start_conversion(self, target_format: str) -> None:
        if not self._pending_files or self._is_busy:
            return

        source_files = list(self._pending_files)
        self._menu_open = False
        self._options = []
        self._update_mask()
        self.update()

        settings: dict = {"batch_mode": "separate"}
        if (
            len(source_files) > 1
            or self._live_modif
            or target_format.upper() in {"COMPRESS", "REDACT", "EDIT-PDF", "LOCK-PDF", "ZIP"}
        ):
            dialog = ConversionSettingsDialog(source_files, target_format)
            if dialog.exec() != ConversionSettingsDialog.DialogCode.Accepted:
                self._status_text = "Cancelled"
                self._status_state = "idle"
                self.update()
                return
            settings = dialog.get_settings()

        self._is_busy = True
        self._status_text = f"Processing → {target_format}..."
        self._status_state = "active"
        self.update()

        self._worker = ConversionWorker(source_files, target_format, settings)
        self._worker.succeeded.connect(self._on_conversion_success)
        self._worker.failed.connect(self._on_conversion_error)
        self._worker.start()

    def _on_conversion_success(self, output_path: Path, summary_text: str) -> None:
        self._is_busy = False
        self._last_output_path = output_path
        self.open_folder_action.setEnabled(True)
        self._status_text = summary_text
        self._status_state = "success"
        self.notifier.notify_success("Complete", f"Saved to {output_path}")
        self.update()

    def _on_conversion_error(self, error_msg: str) -> None:
        self._is_busy = False
        self._status_text = "Failed (Click to retry)"
        self._status_state = "error"
        self.notifier.notify_error("Conversion Failed", error_msg)
        self.update()

    def _open_last_output_folder(self) -> None:
        if self._last_output_path:
            reveal_in_file_manager(self._last_output_path)
