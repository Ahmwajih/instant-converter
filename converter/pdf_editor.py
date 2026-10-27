from pathlib import Path
from typing import Any
import pymupdf


class PDFDocumentSession:
    """Manages live in-memory PDF page manipulation, Undo history, Drag/Move Lines, Font Resize & Stamps."""

    def __init__(self, pdf_path: Path) -> None:
        self.source_path = Path(pdf_path).resolve()
        raw_bytes = self.source_path.read_bytes()
        self.doc = pymupdf.open("pdf", raw_bytes)
        self._undo_stack: list[bytes] = []

    def _push_undo_snapshot(self) -> None:
        try:
            self._undo_stack.append(self.doc.tobytes())
            if len(self._undo_stack) > 20:
                self._undo_stack.pop(0)
        except Exception:
            pass

    def can_undo(self) -> bool:
        return len(self._undo_stack) > 0

    def undo(self) -> bool:
        if not self._undo_stack:
            return False
        prev_bytes = self._undo_stack.pop()
        self.doc.close()
        self.doc = pymupdf.open("pdf", prev_bytes)
        return True

    def page_count(self) -> int:
        return len(self.doc)

    def render_page_png_bytes(
        self,
        page_index: int,
        dpi: int = 135,
        highlight_bbox: tuple[float, float, float, float] | None = None,
    ) -> bytes:
        page = self.doc[page_index]
        pix = page.get_pixmap(dpi=dpi, alpha=False)
        return pix.tobytes("png")

    def get_page_lines(self, page_index: int) -> list[dict[str, Any]]:
        page = self.doc[page_index]
        text_dict = page.get_text("dict")
        lines_out: list[dict[str, Any]] = []

        for block in text_dict.get("blocks", []):
            if block.get("type") != 0:
                continue
            for line in block.get("lines", []):
                spans = line.get("spans", [])
                if not spans:
                    continue
                line_text = "".join(s.get("text", "") for s in spans).strip()
                if not line_text:
                    continue
                bbox = line.get("bbox", (50.0, 50.0, 500.0, 65.0))
                fontsize = float(spans[0].get("size", 11.0))
                lines_out.append(
                    {
                        "text": line_text,
                        "bbox": tuple(float(x) for x in bbox),
                        "size": round(fontsize, 1),
                    }
                )
        return lines_out

    def find_line_at_point(self, page_index: int, pdf_x: float, pdf_y: float) -> int:
        lines = self.get_page_lines(page_index)
        for idx, item in enumerate(lines):
            x0, y0, x1, y1 = item["bbox"]
            if (x0 - 8.0) <= pdf_x <= (x1 + 16.0) and (y0 - 4.0) <= pdf_y <= (y1 + 4.0):
                return idx
        return -1

    def _clear_bbox_safely(self, page: pymupdf.Page, bbox: tuple[float, float, float, float]) -> None:
        padded = pymupdf.Rect(bbox[0] - 1.0, bbox[1] - 1.0, bbox[2] + 2.0, bbox[3] + 1.0)
        try:
            page.add_redact_annot(padded, fill=(1, 1, 1))
            img_none = getattr(pymupdf, "PDF_REDACT_IMAGE_NONE", 0)
            page.apply_redactions(images=img_none)
        except Exception:
            page.draw_rect(padded, color=(1, 1, 1), fill=(1, 1, 1))

    def delete_line(self, page_index: int, bbox: tuple[float, float, float, float]) -> None:
        self._push_undo_snapshot()
        page = self.doc[page_index]
        self._clear_bbox_safely(page, bbox)

    def update_line(
        self,
        page_index: int,
        bbox: tuple[float, float, float, float],
        new_text: str,
        fontsize: float = 11.0,
        new_x: float | None = None,
        new_y: float | None = None,
    ) -> None:
        """Updates text, font size, or position (when dragged on the canvas) of a line."""
        self._push_undo_snapshot()
        page = self.doc[page_index]
        self._clear_bbox_safely(page, bbox)
        if new_text.strip():
            target_x = bbox[0] if new_x is None else max(10.0, new_x)
            baseline_y = (bbox[3] - max(1.5, fontsize * 0.15)) if new_y is None else max(15.0, new_y)
            page.insert_text(
                (target_x, baseline_y),
                new_text,
                fontsize=max(6.0, float(fontsize)),
                fontname="helv",
                color=(0.08, 0.08, 0.09),
            )

    def move_line(
        self,
        page_index: int,
        bbox: tuple[float, float, float, float],
        text: str,
        fontsize: float,
        new_x0: float,
        new_y0: float,
    ) -> None:
        """Moves an existing line to new (x0, y0) PDF coordinates when dragged on the canvas."""
        height = bbox[3] - bbox[1]
        new_baseline_y = new_y0 + height - max(1.5, fontsize * 0.15)
        self.update_line(page_index, bbox, text, fontsize=fontsize, new_x=new_x0, new_y=new_baseline_y)

    def add_line(
        self,
        page_index: int,
        text: str,
        y_pos: float | None = None,
        x_pos: float | None = None,
        fontsize: float = 11.0,
    ) -> None:
        if not text.strip():
            return
        self._push_undo_snapshot()
        page = self.doc[page_index]
        if y_pos is None:
            existing = self.get_page_lines(page_index)
            if existing:
                last_bbox = existing[-1]["bbox"]
                x_pos = last_bbox[0] if x_pos is None else x_pos
                y_pos = min(page.rect.height - 30.0, last_bbox[3] + fontsize + 6.0)
            else:
                x_pos = 50.0 if x_pos is None else x_pos
                y_pos = 72.0
        else:
            x_pos = 50.0 if x_pos is None else x_pos

        page.insert_text(
            (x_pos, y_pos),
            text,
            fontsize=max(6.0, float(fontsize)),
            fontname="helv",
            color=(0.08, 0.08, 0.09),
        )

    def add_watermark(self, text: str, all_pages: bool = True, page_index: int = 0) -> None:
        if not text.strip():
            return
        self._push_undo_snapshot()
        indices = range(len(self.doc)) if all_pages else [page_index]
        for idx in indices:
            page = self.doc[idx]
            r = page.rect
            page.insert_text(
                (r.width * 0.25, r.height * 0.50),
                text.strip().upper(),
                fontsize=34,
                fontname="helv",
                color=(0.78, 0.78, 0.82),
                rotate=0,
                overlay=True,
            )

    def add_signature_image(
        self,
        page_index: int,
        image_path: Path,
        center_x: float | None = None,
        center_y: float | None = None,
        width_pt: float = 135.0,
    ) -> None:
        self._push_undo_snapshot()
        page = self.doc[page_index]
        r = page.rect
        cx = center_x if center_x is not None else (r.width - 120.0)
        cy = center_y if center_y is not None else (r.height - 85.0)
        height_pt = width_pt * 0.45
        target_rect = pymupdf.Rect(
            max(10.0, cx - width_pt / 2.0),
            max(10.0, cy - height_pt / 2.0),
            min(r.width - 10.0, cx + width_pt / 2.0),
            min(r.height - 10.0, cy + height_pt / 2.0),
        )
        page.insert_image(target_rect, filename=str(image_path), keep_proportion=True, overlay=True)

    def add_blank_page(self, after_index: int | None = None) -> int:
        self._push_undo_snapshot()
        width, height = 595.0, 842.0
        if len(self.doc) > 0:
            rect = self.doc[0].rect
            width, height = rect.width, rect.height
        insert_at = -1 if after_index is None else min(len(self.doc), after_index + 1)
        self.doc.new_page(pno=insert_at, width=width, height=height)
        return len(self.doc) - 1 if insert_at == -1 else insert_at

    def append_external_file(self, external_path: Path) -> None:
        self._push_undo_snapshot()
        ext = external_path.suffix.lower().lstrip(".")
        if ext == "pdf":
            with pymupdf.open(str(external_path)) as other:
                self.doc.insert_pdf(other)
        else:
            with pymupdf.open(str(external_path)) as img_doc:
                pdf_bytes = img_doc.convert_to_pdf()
                with pymupdf.open("pdf", pdf_bytes) as img_pdf:
                    self.doc.insert_pdf(img_pdf)

    def remove_page(self, page_index: int) -> None:
        if len(self.doc) <= 1:
            raise ValueError("Cannot remove the only remaining page in the document.")
        self._push_undo_snapshot()
        self.doc.delete_page(page_index)

    def move_page(self, from_index: int, to_index: int) -> None:
        if 0 <= from_index < len(self.doc) and 0 <= to_index < len(self.doc):
            self._push_undo_snapshot()
            self.doc.move_page(from_index, to_index)

    def save_to(self, output_path: Path) -> Path:
        pdf_bytes = self.doc.tobytes(garbage=3, deflate=True)
        Path(output_path).write_bytes(pdf_bytes)
        return Path(output_path)

    def close(self) -> None:
        try:
            self.doc.close()
        except Exception:
            pass
