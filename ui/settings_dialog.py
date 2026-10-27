import shutil
import tempfile
from pathlib import Path
from typing import Sequence
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSlider,
    QVBoxLayout,
)
from converter.detection import DOCUMENT_FORMATS
from converter.documents import convert_document
from ui.pdf_studio_dialog import PDFStudioDialog


class ConversionSettingsDialog(QDialog):
    """Floating Live Modification, Batch Mode Selector (Separate vs Combine) & PDF Studio launcher."""

    def __init__(
        self,
        file_paths: Sequence[Path] | Path,
        target_format: str,
        parent=None,
    ) -> None:
        super().__init__(None)  # Top-level window avoids orb mask clipping on Ubuntu/Windows
        self.setWindowModality(Qt.WindowModality.ApplicationModal)

        if isinstance(file_paths, Path):
            self.file_paths = [file_paths]
        else:
            self.file_paths = list(file_paths)

        self.file_path = self.file_paths[0]
        self.target_format = target_format.upper()
        self.edited_pdf_path: Path | None = None

        self.setWindowTitle(f"Configure → {self.target_format}")
        self.resize(430, 380)
        self.setMinimumWidth(380)
        self.setStyleSheet(
            "QDialog { background-color: #18181b; color: #f4f4f5; border: 1px solid #3f3f46; border-radius: 10px; }"
            "QLabel { color: #e4e4e7; font-size: 12px; }"
            "QCheckBox, QRadioButton { color: #f4f4f5; font-size: 12px; spacing: 6px; }"
            "QComboBox, QLineEdit { background-color: #27272a; color: #ffffff; border: 1px solid #52525b; border-radius: 5px; padding: 5px; }"
            "QPushButton#primary { background-color: #2563eb; color: white; border-radius: 6px; padding: 8px 14px; font-weight: bold; }"
            "QPushButton#primary:hover { background-color: #1d4ed8; }"
            "QPushButton#studio { background-color: #7c3aed; color: white; border-radius: 6px; padding: 9px 12px; font-weight: bold; }"
            "QPushButton#studio:hover { background-color: #6d28d9; }"
            "QPushButton#secondary { background-color: #27272a; color: #d4d4d8; border-radius: 6px; padding: 8px 12px; }"
        )

        self.options = {
            "custom_live": True,
            "batch_mode": "combine" if self.target_format in {"MERGE-PDF", "ZIP"} else "separate",
            "quality": 82,
            "scale": 1.0,
            "crf": 26,
            "dpi": 300,
            "strip_meta": True,
            "redact_pii": True,
            "redact_terms": "",
            "pdf_password": "",
            "zip_password": "",
            "edited_pdf_path": None,
        }

        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(18, 18, 18, 18)

        count = len(self.file_paths)
        total_bytes = sum(p.stat().st_size for p in self.file_paths if p.exists())
        size_kb = total_bytes / 1024.0
        size_str = f"{size_kb / 1024.0:.2f} MB" if size_kb >= 1024 else f"{size_kb:.1f} KB"

        title_str = f"{count} files selected" if count > 1 else self.file_path.name[:36]
        header = QLabel(
            f"<b style='font-size:14px;color:#ffffff;'>{title_str}</b><br>"
            f"<span style='color:#93c5fd;'>Target: {self.target_format}</span> · "
            f"<span style='color:#a1a1aa;'>Total Size: {size_str}</span>"
        )
        layout.addWidget(header)

        # --- MULTI-FILE BATCH CHOICE (SEPARATE VS COMBINE) ---
        if count > 1:
            batch_box = QFrame()
            batch_box.setStyleSheet("QFrame { background-color: #27272a; border: 1px solid #3f3f46; border-radius: 8px; padding: 6px; }")
            b_layout = QVBoxLayout(batch_box)
            b_layout.setSpacing(6)
            b_layout.addWidget(QLabel("<b>Multi-File Output Mode:</b>"))

            self.rb_separate = QRadioButton(f"📄 Convert Separately ({count} individual .{self.target_format.lower()} files)")
            self.rb_combine = QRadioButton(f"📚 Combine All into 1 File (1 merged .{self.target_format.lower()} file)")

            if self.options["batch_mode"] == "combine":
                self.rb_combine.setChecked(True)
            else:
                self.rb_separate.setChecked(True)

            self.batch_group = QButtonGroup(self)
            self.batch_group.addButton(self.rb_separate)
            self.batch_group.addButton(self.rb_combine)
            self.rb_separate.toggled.connect(self._on_batch_mode_toggled)

            b_layout.addWidget(self.rb_separate)
            b_layout.addWidget(self.rb_combine)
            layout.addWidget(batch_box)

        ext = self.file_path.suffix.lower().lstrip(".")

        # --- CUSTOM INTERACTIVE PDF & DOCUMENT STUDIO BUTTON ---
        if ext in DOCUMENT_FORMATS or self.target_format in {"PDF", "EDIT-PDF", "DOCX"}:
            self.btn_studio = QPushButton("✏️ Custom: Preview & Edit PDF (Add/Remove Pages & Lines)...")
            self.btn_studio.setObjectName("studio")
            self.btn_studio.clicked.connect(self._open_custom_pdf_studio)
            layout.addWidget(self.btn_studio)

            self.studio_status = QLabel("<i>Inspect full PDF, add/delete pages or edit lines before finalizing.</i>")
            self.studio_status.setWordWrap(True)
            self.studio_status.setStyleSheet("color: #a1a1aa; font-size: 11px;")
            layout.addWidget(self.studio_status)

        # Quality Slider
        if ext in {"png", "jpg", "jpeg", "webp", "avif", "heic", "pdf"} or self.target_format == "COMPRESS":
            q_row = QHBoxLayout()
            self.q_label = QLabel("Quality / Compression (82%):")
            self.q_slider = QSlider(Qt.Orientation.Horizontal)
            self.q_slider.setRange(15, 100)
            self.q_slider.setValue(82)
            self.q_slider.valueChanged.connect(self._on_quality_changed)
            q_row.addWidget(self.q_label)
            q_row.addWidget(self.q_slider)
            layout.addLayout(q_row)

        # Resolution Scale
        if ext in {"png", "jpg", "jpeg", "webp", "avif", "heic", "mp4", "mov", "mkv", "webm", "avi"}:
            s_row = QHBoxLayout()
            s_row.addWidget(QLabel("Dimensions Scale:"))
            self.s_combo = QComboBox()
            self.s_combo.addItems(["100% (Original)", "75% Scale", "50% Scale", "25% Thumbnail"])
            self.s_combo.currentIndexChanged.connect(
                lambda i: self.options.update({"scale": [1.0, 0.75, 0.5, 0.25][i]})
            )
            s_row.addWidget(self.s_combo)
            layout.addLayout(s_row)

        # Video CRF Preset
        if ext in {"mp4", "mov", "mkv", "webm", "avi", "wmv"}:
            v_row = QHBoxLayout()
            v_row.addWidget(QLabel("Video Bitrate Preset:"))
            self.v_combo = QComboBox()
            self.v_combo.addItems(["Balanced (CRF 26)", "High Quality (CRF 20)", "Max Shrink (CRF 32)"])
            self.v_combo.currentIndexChanged.connect(
                lambda i: self.options.update({"crf": [26, 20, 32][i]})
            )
            v_row.addWidget(self.v_combo)
            layout.addLayout(v_row)

        # PDF Render DPI
        if ext == "pdf" and self.target_format in {"PNG", "JPG", "ALL-PNG"}:
            d_row = QHBoxLayout()
            d_row.addWidget(QLabel("Render DPI:"))
            self.d_combo = QComboBox()
            self.d_combo.addItems(["300 DPI (Print Quality)", "150 DPI (Standard Web)", "600 DPI (Ultra HD)"])
            self.d_combo.currentIndexChanged.connect(
                lambda i: self.options.update({"dpi": [300, 150, 600][i]})
            )
            d_row.addWidget(self.d_combo)
            layout.addLayout(d_row)

        # PDF Redaction Controls
        if self.target_format == "ZIP":
            layout.addWidget(QLabel("<b>ZIP Password Protection (Optional AES-256):</b>"))
            self.zip_pw_input = QLineEdit()
            self.zip_pw_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.zip_pw_input.setPlaceholderText("Leave empty for normal ZIP, or enter password...")
            self.zip_pw_input.textChanged.connect(lambda t: self.options.update({"zip_password": t}))
            layout.addWidget(self.zip_pw_input)

        if self.target_format == "LOCK-PDF":
            layout.addWidget(QLabel("<b>AES-256 PDF Password Protection:</b>"))
            self.pw_input = QLineEdit()
            self.pw_input.setEchoMode(QLineEdit.EchoMode.Password)
            self.pw_input.setPlaceholderText("Enter password to encrypt PDF...")
            self.pw_input.textChanged.connect(lambda t: self.options.update({"pdf_password": t}))
            layout.addWidget(self.pw_input)

        if self.target_format == "REDACT":
            self.cb_pii = QCheckBox("Auto-redact Emails, Phone Numbers & IBANs")
            self.cb_pii.setChecked(True)
            self.cb_pii.toggled.connect(lambda c: self.options.update({"redact_pii": c}))
            layout.addWidget(self.cb_pii)

            layout.addWidget(QLabel("Custom words to black out (comma-separated):"))
            self.redact_input = QLineEdit()
            self.redact_input.setPlaceholderText("e.g. SecretProject, John Doe, +49 157...")
            self.redact_input.textChanged.connect(lambda t: self.options.update({"redact_terms": t}))
            layout.addWidget(self.redact_input)

        # Privacy Metadata Checkbox
        self.cb_meta = QCheckBox("Strip EXIF / GPS / Author Metadata")
        self.cb_meta.setChecked(True)
        self.cb_meta.toggled.connect(lambda c: self.options.update({"strip_meta": c}))
        layout.addWidget(self.cb_meta)

        # Buttons
        btn_row = QHBoxLayout()
        btn_cancel = QPushButton("Cancel")
        btn_cancel.setObjectName("secondary")
        btn_cancel.clicked.connect(self.reject)

        btn_run = QPushButton(f"Finalize → {self.target_format}")
        btn_run.setObjectName("primary")
        btn_run.clicked.connect(self.accept)

        btn_row.addWidget(btn_cancel)
        btn_row.addWidget(btn_run)
        layout.addLayout(btn_row)

    def _on_batch_mode_toggled(self) -> None:
        self.options["batch_mode"] = "separate" if self.rb_separate.isChecked() else "combine"

    def _on_quality_changed(self, val: int) -> None:
        self.q_label.setText(f"Quality / Compression ({val}%):")
        self.options["quality"] = val

    def _open_custom_pdf_studio(self) -> None:
        working_pdf = self.edited_pdf_path

        if working_pdf is None or not working_pdf.exists():
            tmp_dir = Path(tempfile.mkdtemp(prefix="instant_studio_"))
            draft_pdf = tmp_dir / "draft_preview.pdf"
            try:
                if len(self.file_paths) > 1 and self.options.get("batch_mode") == "combine":
                    from converter.batch import combine_files_to_single_output
                    combined = combine_files_to_single_output(self.file_paths, "PDF")
                    shutil.move(str(combined), str(draft_pdf))
                elif self.file_path.suffix.lower() == ".pdf":
                    shutil.copy2(self.file_path, draft_pdf)
                else:
                    convert_document(self.file_path, draft_pdf, "pdf")
            except Exception as exc:
                QMessageBox.critical(self, "Preview Error", f"Could not build PDF preview:\n{exc}")
                return
            working_pdf = draft_pdf

        studio = PDFStudioDialog(working_pdf, self.target_format)
        if studio.exec() == PDFStudioDialog.DialogCode.Accepted and studio.saved_output_path:
            self.edited_pdf_path = studio.saved_output_path
            self.options["edited_pdf_path"] = studio.saved_output_path
            self.studio_status.setText(
                "<span style='color:#4ade80;font-weight:bold;'>✓ Custom Page/Line edits saved and ready!</span>"
            )

    def get_settings(self) -> dict:
        return self.options
