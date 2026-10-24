import math
from typing import List
from PySide6.QtCore import Qt, QPointF, QRectF
from PySide6.QtGui import QColor, QFont, QPainter, QPainterPath, QPen


class RadialWheelRenderer:
    """Renders and hit-tests the radial format slices around a center point."""

    def __init__(self, inner_radius: float = 50.0, outer_radius: float = 132.0) -> None:
        self.inner_radius = inner_radius
        self.outer_radius = outer_radius

    def hit_test(self, center: QPointF, pos: QPointF, options: List[str]) -> int:
        if not options:
            return -1
        dx = pos.x() - center.x()
        dy = pos.y() - center.y()
        dist = math.hypot(dx, dy)
        if dist < self.inner_radius or dist > self.outer_radius:
            return -1

        angle = (math.degrees(math.atan2(dy, dx)) + 90.0) % 360.0
        span = 360.0 / len(options)
        return int(angle // span)

    def draw(
        self,
        painter: QPainter,
        center: QPointF,
        options: List[str],
        hovered_index: int,
    ) -> None:
        count = len(options)
        if count == 0:
            return

        span_angle = 360.0 / count
        outer_rect = QRectF(
            center.x() - self.outer_radius,
            center.y() - self.outer_radius,
            self.outer_radius * 2,
            self.outer_radius * 2,
        )
        inner_rect = QRectF(
            center.x() - self.inner_radius,
            center.y() - self.inner_radius,
            self.inner_radius * 2,
            self.inner_radius * 2,
        )

        for i, label in enumerate(options):
            start_deg = i * span_angle - 90.0
            path = QPainterPath()
            start_rad = math.radians(start_deg)

            path.moveTo(
                center.x() + self.inner_radius * math.cos(start_rad),
                center.y() + self.inner_radius * math.sin(start_rad),
            )
            path.lineTo(
                center.x() + self.outer_radius * math.cos(start_rad),
                center.y() + self.outer_radius * math.sin(start_rad),
            )
            path.arcTo(outer_rect, -start_deg, -span_angle)

            end_rad = math.radians(start_deg + span_angle)
            path.lineTo(
                center.x() + self.inner_radius * math.cos(end_rad),
                center.y() + self.inner_radius * math.sin(end_rad),
            )
            path.arcTo(inner_rect, -(start_deg + span_angle), span_angle)
            path.closeSubpath()

            is_hovered = i == hovered_index
            fill_color = (
                QColor(37, 99, 235, 245) if is_hovered else QColor(24, 24, 27, 235)
            )
            border_color = (
                QColor(147, 197, 253, 255) if is_hovered else QColor(63, 63, 70, 220)
            )

            painter.setBrush(fill_color)
            painter.setPen(QPen(border_color, 2.0))
            painter.drawPath(path)

            mid_deg = start_deg + (span_angle / 2.0)
            mid_rad = math.radians(mid_deg)
            text_radius = (self.inner_radius + self.outer_radius) / 2.0
            tx = center.x() + text_radius * math.cos(mid_rad)
            ty = center.y() + text_radius * math.sin(mid_rad)

            painter.setFont(QFont("Sans Serif", 11, QFont.Weight.Bold))
            painter.setPen(QColor(255, 255, 255))
            text_rect = QRectF(tx - 38, ty - 14, 76, 28)
            painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, label)
