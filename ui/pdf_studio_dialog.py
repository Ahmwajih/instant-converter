import os
import tempfile
from pathlib import Path
from PySide6.QtCore import Qt, QRectF, Signal
from PySide6.QtGui import QBrush, QColor, QImage, QKeySequence, QPainter, QPen, QPixmap, QShortcut
from PySide6.QtWidgets import (
    QDialog,
    QDoubleSpinBox,
    QFileDialog,
    QGraphicsPixmapItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsView,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSlider,
    QSplitter,
    QVBoxLayout,
    QWidget,
)
from converter.pdf_editor import PDFDocumentSession


class DraggableLineBox(QGraphicsRectItem):
    """Interactive overlay box for a PDF text line: click to select, double-click to edit, drag to move."""

    def __init__(self, index: int, info: dict, scale: float, studio: "PDFStudioDialog") -> None:
        x0, y0, x1, y1 = info["bbox"]
        super().__init__(0, 0, (x1 - x0) * scale, (y1 - y0) * scale)
        self.index = index
        self.info = info
        self.scale_factor = scale
        self.studio = studio
        self._start_pos = QRectF(x0 * scale, y0 * scale, (x1 - x0) * scale, (y1 - y0) * scale).topLeft()

        self.setPos(self._start_pos)
        self.setAcceptHoverEvents(True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsMovable, True)
        self.setFlag(QGraphicsRectItem.GraphicsItemFlag.ItemIsSelectable, True)
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        self.setToolTip(f"Line #{index + 1}: {info['text']}\n• Click to edit\n• Double-click to inline edit\n• Drag to move on page")
        self._apply_style(selected=False, hovered=False)

    def _apply_style(self, selected: bool, hovered: bool) -> None:
        if selected:
            self.setPen(QPen(QColor(37, 99, 235), 2.0))
            self.setBrush(QBrush(QColor(37, 99, 235, 50)))
        elif hovered:
            self.setPen(QPen(QColor(96, 165, 250), 1.4, Qt.PenStyle.DashLine))
            self.setBrush(QBrush(QColor(59, 130, 246, 28)))
        else:
            self.setPen(QPen(QColor(161, 161, 170, 70), 0.8, Qt.PenStyle.DotLine))
            self.setBrush(QBrush(Qt.GlobalColor.transparent))

    def hoverEnterEvent(self, event) -> None:
        if self.studio.selected_line_idx != self.index:
            self._apply_style(selected=False, hovered=True)
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        if self.studio.selected_line_idx != self.index:
            self._apply_style(selected=False, hovered=False)
        super().hoverLeaveEvent(event)

    def mousePressEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.ClosedHandCursor)
        self._start_pos = self.pos()
        self.studio.select_line_from_canvas(self.index)
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        self.setCursor(Qt.CursorShape.OpenHandCursor)
        super().mouseReleaseEvent(event)
        new_pos = self.pos()
        if (new_pos - self._start_pos).manhattanLength() > 4.0:
            pdf_x0 = new_pos.x() / self.scale_factor
            pdf_y0 = new_pos.y() / self.scale_factor
            self.studio.move_line_from_canvas(self.index, pdf_x0, pdf_y0)

    def mouseDoubleClickEvent(self, event) -> None:
        self.studio.inline_edit_line(self.index)
        super().mouseDoubleClickEvent(event)


class ZoomablePDFView(QGraphicsView):
    """Smooth zoomable & pannable PDF canvas supporting Ctrl+Wheel zoom and point clicks."""

    zoom_changed = Signal(int)
    empty_point_clicked = Signal(float, float)

    def __init__(self, scene: QGraphicsScene, base_dpi: int = 135, parent=None) -> None:
        super().__init__(scene, parent)
        self.base_dpi = base_dpi
        self._zoom_pct = 100
        self.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setStyleSheet("background-color: #09090b; border: 1px solid #3f3f46; border-radius: 6px;")

    def set_zoom_percent(self, pct: int) -> None:
        pct = max(40, min(300, pct))
        self._zoom_pct = pct
        self.resetTransform()
        factor = pct / 100.0
        self.scale(factor, factor)
        self.zoom_changed.emit(pct)

    def wheelEvent(self, event) -> None:
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            delta = 15 if event.angleDelta().y() > 0 else -15
            self.set_zoom_percent(self._zoom_pct + delta)
            event.accept()
            return
        super().wheelEvent(event)

    def mousePressEvent(self, event) -> None:
        item = self.itemAt(event.position().toPoint())
        if isinstance(item, QGraphicsPixmapItem) and event.button() == Qt.MouseButton.LeftButton:
            scene_pt = self.mapToScene(event.position().toPoint())
            scale = 72.0 / float(self.base_dpi)
            self.empty_point_clicked.emit(scene_pt.x() * scale, scene_pt.y() * scale)
        super().mousePressEvent(event)


class PDFStudioDialog(QDialog):
    """Interactive PDF Studio with Zoomable Canvas, Drag-to-Move Lines, Double-Click Inline Edit & Font Resize."""

    BASE_DPI = 135

    def __init__(self, pdf_path: Path, target_format: str, parent=None) -> None:
        super().__init__(None)
        self.setWindowFlags(
            Qt.WindowType.Window
            | Qt.WindowType.WindowMinimizeButtonHint
            | Qt.WindowType.WindowMaximizeButtonHint
            | Qt.WindowType.WindowCloseButtonHint
        )
        self.setWindowModality(Qt.WindowModality.ApplicationModal)
        self.session = PDFDocumentSession(pdf_path)
        self.target_format = target_format.upper()
        self.current_page = 0
        self.current_lines: list[dict] = []
        self.line_boxes: list[DraggableLineBox] = []
        self.selected_line_idx: int = -1
        self.last_clicked_pt: tuple[float, float] | None = None
        self.saved_output_path: Path | None = None

        self.setWindowTitle(f"Custom PDF Studio — Zoom, Drag Lines, Double-Click to Edit → {self.target_format}")
        self.resize(1180, 760)
        self.setMinimumSize(780, 520)
        self.setStyleSheet(
            "QDialog { background-color: #18181b; color: #f4f4f5; }"
            "QLabel { color: #e4e4e7; font-size: 12px; }"
            "QListWidget { background-color: #27272a; color: #f4f4f5; border: 1px solid #3f3f46; border-radius: 6px; padding: 4px; }"
            "QListWidget::item { padding: 6px; border-bottom: 1px solid #3f3f46; }"
            "QListWidget::item:selected { background-color: #2563eb; color: white; border-radius: 4px; }"
            "QLineEdit, QDoubleSpinBox { background-color: #27272a; color: #ffffff; border: 1px solid #52525b; border-radius: 5px; padding: 5px; }"
            "QPushButton { background-color: #27272a; color: #e4e4e7; border: 1px solid #3f3f46; border-radius: 6px; padding: 6px 10px; font-weight: 600; }"
            "QPushButton:hover { background-color: #3f3f46; }"
            "QPushButton#primary { background-color: #16a34a; color: white; border: none; padding: 9px 18px; font-weight: bold; }"
            "QPushButton#primary:hover { background-color: #15803d; }"
            "QPushButton#accent { background-color: #7c3aed; color: white; border: none; }"
            "QPushButton#accent:hover { background-color: #6d28d9; }"
            "QPushButton#danger { background-color: #991b1b; color: white; border: none; }"
            "QPushButton#danger:hover { background-color: #7f1d1d; }"
        )

        # Keyboard shortcuts for fast editing
        QShortcut(QKeySequence.StandardKey.Delete, self).activated.connect(self._delete_selected_line)
        QShortcut(QKeySequence.StandardKey.Undo, self).activated.connect(self._undo_last_action)
        QShortcut(QKeySequence("Ctrl++"), self).activated.connect(lambda: self.view.set_zoom_percent(self.zoom_slider.value() + 20))
        QShortcut(QKeySequence("Ctrl+-"), self).activated.connect(lambda: self.view.set_zoom_percent(self.zoom_slider.value() - 20))

        root_layout = QVBoxLayout(self)
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # --- LEFT PANEL: PAGES & STAMPS ---
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("<b>1. Pages (Add / Remove / Reorder)</b>"))

        self.page_list = QListWidget()
        self.page_list.currentRowChanged.connect(self._on_page_selected)
        left_layout.addWidget(self.page_list)

        page_btn_row1 = QHBoxLayout()
        btn_add_blank = QPushButton("+ Blank Page")
        btn_add_blank.clicked.connect(self._add_blank_page)
        btn_import_page = QPushButton("+ Merge PDF/Img")
        btn_import_page.clicked.connect(self._import_external_page)
        page_btn_row1.addWidget(btn_add_blank)
        page_btn_row1.addWidget(btn_import_page)
        left_layout.addLayout(page_btn_row1)

        page_btn_row2 = QHBoxLayout()
        btn_up = QPushButton("↑ Up")
        btn_up.clicked.connect(self._move_page_up)
        btn_down = QPushButton("↓ Down")
        btn_down.clicked.connect(self._move_page_down)
        btn_del_page = QPushButton("🗑️ Delete Page")
        btn_del_page.setObjectName("danger")
        btn_del_page.clicked.connect(self._delete_current_page)
        page_btn_row2.addWidget(btn_up)
        page_btn_row2.addWidget(btn_down)
        page_btn_row2.addWidget(btn_del_page)
        left_layout.addLayout(page_btn_row2)

        left_layout.addWidget(QLabel("<b>Stamp & Sign Tools:</b>"))
        stamp_row = QHBoxLayout()
        btn_sign = QPushButton("✒️ Sign / Stamp")
        btn_sign.setObjectName("accent")
        btn_sign.clicked.connect(self._stamp_signature_image)
        btn_watermark = QPushButton("💧 Watermark")
        btn_watermark.setObjectName("accent")
        btn_watermark.clicked.connect(self._stamp_watermark_text)
        stamp_row.addWidget(btn_sign)
        stamp_row.addWidget(btn_watermark)
        left_layout.addLayout(stamp_row)

        splitter.addWidget(left_widget)

        # --- CENTER PANEL: INTERACTIVE ZOOMABLE & DRAGGABLE PAGE CANVAS ---
        center_widget = QWidget()
        center_layout = QVBoxLayout(center_widget)
        center_layout.setContentsMargins(6, 0, 6, 0)

        # Top Zoom Toolbar
        zoom_bar = QHBoxLayout()
        self.canvas_hint = QLabel("<b>2. Interactive Page</b> (Click/Drag lines, Double-click to edit, Ctrl+Wheel to Zoom)")
        zoom_bar.addWidget(self.canvas_hint)
        zoom_bar.addStretch()

        btn_zoom_out = QPushButton("🔍 −")
        btn_zoom_out.setFixedWidth(44)
        btn_zoom_out.clicked.connect(lambda: self.view.set_zoom_percent(self.zoom_slider.value() - 20))

        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(40, 260)
        self.zoom_slider.setValue(100)
        self.zoom_slider.setFixedWidth(120)

        self.zoom_label = QLabel("100%")
        self.zoom_label.setFixedWidth(42)

        btn_zoom_in = QPushButton("🔍 +")
        btn_zoom_in.setFixedWidth(44)
        btn_zoom_in.clicked.connect(lambda: self.view.set_zoom_percent(self.zoom_slider.value() + 20))

        btn_zoom_fit = QPushButton("100%")
        btn_zoom_fit.setFixedWidth(50)
        btn_zoom_fit.clicked.connect(lambda: self.view.set_zoom_percent(100))

        zoom_bar.addWidget(btn_zoom_out)
        zoom_bar.addWidget(self.zoom_slider)
        zoom_bar.addWidget(self.zoom_label)
        zoom_bar.addWidget(btn_zoom_in)
        zoom_bar.addWidget(btn_zoom_fit)
        center_layout.addLayout(zoom_bar)

        self.scene = QGraphicsScene(self)
        self.view = ZoomablePDFView(self.scene, base_dpi=self.BASE_DPI)
        self.zoom_slider.valueChanged.connect(self.view.set_zoom_percent)
        self.view.zoom_changed.connect(self._on_view_zoom_changed)
        self.view.empty_point_clicked.connect(self._on_empty_point_clicked)
        center_layout.addWidget(self.view)

        splitter.addWidget(center_widget)

        # --- RIGHT PANEL: LINE TEXT & FONT SIZE EDITOR ---
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.addWidget(QLabel("<b>3. Page Lines (Text & Font Size)</b>"))

        self.line_list = QListWidget()
        self.line_list.currentRowChanged.connect(self._on_line_list_selected)
        self.line_list.itemDoubleClicked.connect(lambda _: self.inline_edit_line(self.line_list.currentRow()))
        right_layout.addWidget(self.line_list)

        edit_row = QHBoxLayout()
        edit_row.addWidget(QLabel("Text:"))
        self.line_edit = QLineEdit()
        self.line_edit.setPlaceholderText("Select or double-click any line on the page...")
        self.line_edit.returnPressed.connect(self._update_selected_line)
        edit_row.addWidget(self.line_edit)
        right_layout.addLayout(edit_row)

        size_row = QHBoxLayout()
        size_row.addWidget(QLabel("Font Size (pt):"))
        self.font_spin = QDoubleSpinBox()
        self.font_spin.setRange(6.0, 72.0)
        self.font_spin.setSingleStep(0.5)
        self.font_spin.setValue(11.0)
        size_row.addWidget(self.font_spin)
        size_row.addStretch()
        right_layout.addLayout(size_row)

        line_btn_row = QHBoxLayout()
        btn_update_line = QPushButton("✓ Apply Text/Size")
        btn_update_line.clicked.connect(self._update_selected_line)

        btn_add_line = QPushButton("+ Add Line")
        btn_add_line.clicked.connect(self._add_new_line)

        btn_del_line = QPushButton("🗑️ Delete Line")
        btn_del_line.setObjectName("danger")
        btn_del_line.clicked.connect(self._delete_selected_line)

        line_btn_row.addWidget(btn_update_line)
        line_btn_row.addWidget(btn_add_line)
        line_btn_row.addWidget(btn_del_line)
        right_layout.addLayout(line_btn_row)

        splitter.addWidget(right_widget)
        splitter.setSizes([230, 580, 340])
        root_layout.addWidget(splitter)

        # --- BOTTOM BAR: UNDO & FINALIZE ---
        bottom_bar = QHBoxLayout()
        self.btn_undo = QPushButton("↶ Undo (Ctrl+Z)")
        self.btn_undo.setEnabled(False)
        self.btn_undo.clicked.connect(self._undo_last_action)
        bottom_bar.addWidget(self.btn_undo)

        bottom_bar.addStretch()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.clicked.connect(self.reject)

        btn_finalize = QPushButton(f"✓ Save Edits & Continue → {self.target_format}")
        btn_finalize.setObjectName("primary")
        btn_finalize.clicked.connect(self._finalize_and_save)

        bottom_bar.addWidget(btn_cancel)
        bottom_bar.addWidget(btn_finalize)
        root_layout.addLayout(bottom_bar)

        self._refresh_page_list(select_index=0)

    def _on_view_zoom_changed(self, pct: int) -> None:
        self.zoom_slider.blockSignals(True)
        self.zoom_slider.setValue(pct)
        self.zoom_slider.blockSignals(False)
        self.zoom_label.setText(f"{pct}%")

    def _refresh_page_list(self, select_index: int = 0) -> None:
        self.page_list.blockSignals(True)
        self.page_list.clear()
        total = self.session.page_count()
        for i in range(total):
            lines = self.session.get_page_lines(i)
            snippet = lines[0]["text"][:22] if lines else "(Blank / Image Page)"
            self.page_list.addItem(QListWidgetItem(f"Page {i + 1} — {snippet}"))
        self.page_list.blockSignals(False)

        target_idx = max(0, min(select_index, total - 1))
        self.page_list.setCurrentRow(target_idx)
        self._load_page(target_idx)
        self.btn_undo.setEnabled(self.session.can_undo())

    def _load_page(self, page_index: int) -> None:
        if page_index < 0 or page_index >= self.session.page_count():
            return
        self.current_page = page_index
        self.selected_line_idx = -1
        self.current_lines = self.session.get_page_lines(page_index)

        # Rebuild Graphics Scene with base page + draggable line boxes
        self.scene.clear()
        self.line_boxes.clear()

        png_bytes = self.session.render_page_png_bytes(page_index, dpi=self.BASE_DPI)
        qimg = QImage.fromData(png_bytes, "PNG")
        pixmap = QPixmap.fromImage(qimg)
        bg_item = self.scene.addPixmap(pixmap)
        bg_item.setZValue(0)
        self.scene.setSceneRect(QRectF(pixmap.rect()))

        scale = float(self.BASE_DPI) / 72.0
        for idx, info in enumerate(self.current_lines):
            box = DraggableLineBox(idx, info, scale, self)
            box.setZValue(10)
            self.scene.addItem(box)
            self.line_boxes.append(box)

        self.line_list.blockSignals(True)
        self.line_list.clear()
        for idx, item in enumerate(self.current_lines):
            self.line_list.addItem(f"[{idx + 1}] {item['text']}")
        self.line_list.blockSignals(False)
        self.line_edit.clear()
        self.btn_undo.setEnabled(self.session.can_undo())

    def _on_page_selected(self, row: int) -> None:
        if row >= 0:
            self._load_page(row)

    def _on_empty_point_clicked(self, pdf_x: float, pdf_y: float) -> None:
        self.last_clicked_pt = (pdf_x, pdf_y)
        self.canvas_hint.setText(
            f"<b>Insertion Point Set</b> at ({int(pdf_x)}, {int(pdf_y)}) — Click '+ Add Line' or '✒️ Sign / Stamp'"
        )

    def select_line_from_canvas(self, idx: int) -> None:
        if 0 <= idx < len(self.current_lines):
            self.selected_line_idx = idx
            self.line_list.blockSignals(True)
            self.line_list.setCurrentRow(idx)
            self.line_list.blockSignals(False)
            self._highlight_box(idx)
            info = self.current_lines[idx]
            self.line_edit.setText(info["text"])
            self.font_spin.setValue(float(info["size"]))
            self.line_edit.setFocus()
            self.canvas_hint.setText(
                f"<b>Selected Line #{idx + 1}</b> — Type on right, drag box to move, or double-click box"
            )

    def _on_line_list_selected(self, row: int) -> None:
        if 0 <= row < len(self.current_lines):
            self.selected_line_idx = row
            self._highlight_box(row)
            info = self.current_lines[row]
            self.line_edit.setText(info["text"])
            self.font_spin.setValue(float(info["size"]))

    def _highlight_box(self, selected_idx: int) -> None:
        for i, box in enumerate(self.line_boxes):
            box._apply_style(selected=(i == selected_idx), hovered=False)

    def move_line_from_canvas(self, idx: int, new_pdf_x0: float, new_pdf_y0: float) -> None:
        if not (0 <= idx < len(self.current_lines)):
            return
        info = self.current_lines[idx]
        self.session.move_line(
            self.current_page,
            info["bbox"],
            info["text"],
            info["size"],
            new_pdf_x0,
            new_pdf_y0,
        )
        self._refresh_page_list(select_index=self.current_page)

    def inline_edit_line(self, idx: int) -> None:
        if not (0 <= idx < len(self.current_lines)):
            return
        info = self.current_lines[idx]
        new_text, ok = QInputDialog.getText(
            self,
            f"Edit Line #{idx + 1}",
            "Modify text (leave empty to delete line):",
            QLineEdit.EchoMode.Normal,
            info["text"],
        )
        if ok:
            if not new_text.strip():
                self.session.delete_line(self.current_page, info["bbox"])
            else:
                self.session.update_line(
                    self.current_page, info["bbox"], new_text, fontsize=self.font_spin.value()
                )
            self._refresh_page_list(select_index=self.current_page)

    def _update_selected_line(self) -> None:
        row = self.line_list.currentRow()
        if not (0 <= row < len(self.current_lines)):
            return
        info = self.current_lines[row]
        new_val = self.line_edit.text()
        new_sz = float(self.font_spin.value())
        if new_val != info["text"] or abs(new_sz - float(info["size"])) > 0.1:
            self.session.update_line(self.current_page, info["bbox"], new_val, fontsize=new_sz)
            self._refresh_page_list(select_index=self.current_page)
            self.line_list.setCurrentRow(min(row, self.line_list.count() - 1))

    def _delete_selected_line(self) -> None:
        row = self.line_list.currentRow()
        if not (0 <= row < len(self.current_lines)):
            return
        info = self.current_lines[row]
        self.session.delete_line(self.current_page, info["bbox"])
        self._refresh_page_list(select_index=self.current_page)

    def _add_new_line(self) -> None:
        text, ok = QInputDialog.getText(self, "Add New Line", "Enter text line to insert:")
        if ok and text.strip():
            x_pt = self.last_clicked_pt[0] if self.last_clicked_pt else None
            y_pt = self.last_clicked_pt[1] if self.last_clicked_pt else None
            self.session.add_line(
                self.current_page,
                text.strip(),
                y_pos=y_pt,
                x_pos=x_pt,
                fontsize=float(self.font_spin.value()),
            )
            self._refresh_page_list(select_index=self.current_page)

    def _stamp_signature_image(self) -> None:
        file_str, _ = QFileDialog.getOpenFileName(
            self,
            "Select Signature or Stamp Image (PNG / JPG)",
            str(Path.home()),
            "Images (*.png *.jpg *.jpeg *.webp *.bmp)",
            "",
            QFileDialog.Option.DontUseNativeDialog,
        )
        if not file_str:
            return
        cx = self.last_clicked_pt[0] if self.last_clicked_pt else None
        cy = self.last_clicked_pt[1] if self.last_clicked_pt else None
        self.session.add_signature_image(self.current_page, Path(file_str), center_x=cx, center_y=cy)
        self._refresh_page_list(select_index=self.current_page)

    def _stamp_watermark_text(self) -> None:
        text, ok = QInputDialog.getText(
            self, "Add Watermark", "Watermark text (e.g. CONFIDENTIAL, DRAFT, COPY):"
        )
        if ok and text.strip():
            self.session.add_watermark(text.strip(), all_pages=True, page_index=self.current_page)
            self._refresh_page_list(select_index=self.current_page)

    def _add_blank_page(self) -> None:
        new_idx = self.session.add_blank_page(after_index=self.current_page)
        self._refresh_page_list(select_index=new_idx)

    def _import_external_page(self) -> None:
        file_str, _ = QFileDialog.getOpenFileName(
            self,
            "Select PDF or Image to Append",
            str(Path.home()),
            "PDF & Images (*.pdf *.png *.jpg *.jpeg *.webp *.bmp)",
            "",
            QFileDialog.Option.DontUseNativeDialog,
        )
        if file_str:
            self.session.append_external_file(Path(file_str))
            self._refresh_page_list(select_index=self.session.page_count() - 1)

    def _delete_current_page(self) -> None:
        if self.session.page_count() <= 1:
            QMessageBox.warning(self, "Cannot Delete", "Document must contain at least 1 page.")
            return
        self.session.remove_page(self.current_page)
        self._refresh_page_list(select_index=max(0, self.current_page - 1))

    def _move_page_up(self) -> None:
        if self.current_page > 0:
            target = self.current_page - 1
            self.session.move_page(self.current_page, target)
            self._refresh_page_list(select_index=target)

    def _move_page_down(self) -> None:
        if self.current_page < self.session.page_count() - 1:
            target = self.current_page + 1
            self.session.move_page(self.current_page, target)
            self._refresh_page_list(select_index=target)

    def _undo_last_action(self) -> None:
        if self.session.undo():
            self._refresh_page_list(select_index=min(self.current_page, self.session.page_count() - 1))

    def _finalize_and_save(self) -> None:
        row = self.line_list.currentRow()
        if 0 <= row < len(self.current_lines):
            typed = self.line_edit.text()
            new_sz = float(self.font_spin.value())
            info = self.current_lines[row]
            if typed and (typed != info["text"] or abs(new_sz - float(info["size"])) > 0.1):
                self.session.update_line(self.current_page, info["bbox"], typed, fontsize=new_sz)

        fd, tmp_name = tempfile.mkstemp(prefix="instant_edited_", suffix=".pdf")
        os.close(fd)
        self.saved_output_path = self.session.save_to(Path(tmp_name))
        self.accept()

    def closeEvent(self, event) -> None:
        self.session.close()
        super().closeEvent(event)
