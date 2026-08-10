"""G-code editor widget with line numbers and basic syntax highlighting."""

from __future__ import annotations

import re

from PySide6.QtCore import QRect, QSize, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetricsF,
    QPainter,
    QTextCharFormat,
    QTextCursor,
)
from PySide6.QtWidgets import QPlainTextEdit, QTextEdit, QVBoxLayout, QWidget
from PySide6.QtGui import QSyntaxHighlighter


DEFAULT_GCODE = """G21
G90
G0 X0 Y0
G0 Z5

(Paste or import G-code here)
"""


class GCodeHighlighter(QSyntaxHighlighter):
    """Highlight common Fanuc-style G-code words without changing editor content."""

    def __init__(self, document) -> None:  # type: ignore[no-untyped-def]
        """Create syntax formats for motion, machine codes, parameters, and comments."""
        super().__init__(document)
        self._rules: list[tuple[re.Pattern[str], QTextCharFormat]] = [
            (re.compile(r"\bG0?[0123]\b|\bG17\b|\bG18\b|\bG21\b|\bG90\b", re.IGNORECASE), self._format("#60a5fa", True)),
            (re.compile(r"\bM0?[35]\b|\bM30\b", re.IGNORECASE), self._format("#c084fc", True)),
            (re.compile(r"\b[XYZIJKFS](?=[+-]?(?:\d|\.\d))", re.IGNORECASE), self._format("#22d3ee", True)),
            (re.compile(r";.*|\([^)]*\)"), self._format("#86efac", False)),
        ]

    def highlightBlock(self, text: str) -> None:
        """Apply all configured highlight rules to one text block."""
        for pattern, text_format in self._rules:
            for match in pattern.finditer(text):
                self.setFormat(match.start(), match.end() - match.start(), text_format)

    def _format(self, color: str, bold: bool) -> QTextCharFormat:
        """Build a reusable QTextCharFormat."""
        text_format = QTextCharFormat()
        text_format.setForeground(QColor(color))
        if bold:
            text_format.setFontWeight(QFont.Weight.DemiBold)
        return text_format


class LineNumberArea(QWidget):
    """Small side area that delegates line-number painting to the editor."""

    def __init__(self, editor: "GCodePlainTextEdit") -> None:
        """Keep a reference to the owning editor."""
        super().__init__(editor)
        self._editor = editor

    def sizeHint(self) -> QSize:
        """Return the width required by current line numbers."""
        return QSize(self._editor.line_number_area_width(), 0)

    def paintEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        """Paint line numbers for visible blocks."""
        self._editor.line_number_area_paint_event(event)


class GCodePlainTextEdit(QPlainTextEdit):
    """Plain text editor with CNC-friendly line numbers and current-line highlight."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Configure the editor surface and helper gutter."""
        super().__init__(parent)
        self._line_number_area = LineNumberArea(self)
        self._playback_line_number: int | None = None

        editor_font = QFont("Consolas", 10)
        editor_font.setStyleHint(QFont.StyleHint.Monospace)
        self.setFont(editor_font)
        self.setTabStopDistance(QFontMetricsF(editor_font).horizontalAdvance(" ") * 4)
        self.setLineWrapMode(QPlainTextEdit.LineWrapMode.NoWrap)
        self.setObjectName("gcodeEditor")
        self.setPlaceholderText("在此输入或导入 G代码...")

        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        self.update_line_number_area_width(0)
        self.highlight_current_line()
        self._highlighter = GCodeHighlighter(self.document())

    def line_number_area_width(self) -> int:
        """Calculate the gutter width from the current number of text blocks."""
        digits = len(str(max(1, self.blockCount())))
        return 24 + self.fontMetrics().horizontalAdvance("9") * digits

    def update_line_number_area_width(self, _: int) -> None:
        """Reserve viewport margin for the line-number gutter."""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect: QRect, dy: int) -> None:
        """Scroll or repaint the line-number gutter with the editor viewport."""
        if dy:
            self._line_number_area.scroll(0, dy)
        else:
            self._line_number_area.update(0, rect.y(), self._line_number_area.width(), rect.height())
        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event) -> None:  # type: ignore[no-untyped-def]
        """Keep the gutter aligned when the editor resizes."""
        super().resizeEvent(event)
        contents_rect = self.contentsRect()
        self._line_number_area.setGeometry(
            QRect(contents_rect.left(), contents_rect.top(), self.line_number_area_width(), contents_rect.height())
        )

    def line_number_area_paint_event(self, event) -> None:  # type: ignore[no-untyped-def]
        """Paint visible line numbers using a subdued engineering editor palette."""
        painter = QPainter(self._line_number_area)
        painter.fillRect(event.rect(), QColor("#1A1A1A"))
        painter.setPen(QColor("#9CA3AF"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        top = int(self.blockBoundingGeometry(block).translated(self.contentOffset()).top())
        bottom = top + int(self.blockBoundingRect(block).height())

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.drawText(
                    0,
                    top,
                    self._line_number_area.width() - 8,
                    self.fontMetrics().height(),
                    Qt.AlignmentFlag.AlignRight,
                    number,
                )
            block = block.next()
            top = bottom
            bottom = top + int(self.blockBoundingRect(block).height())
            block_number += 1

    def highlight_current_line(self) -> None:
        """Highlight the cursor line and preserve the playback line highlight."""
        self._refresh_extra_selections()

    def highlight_line(self, line_number: int) -> None:
        """Highlight a specific playback line by line number (1-based)."""
        if line_number <= 0:
            return
        block = self.document().findBlockByNumber(line_number - 1)
        if not block.isValid():
            return
        self._playback_line_number = line_number
        self._refresh_extra_selections()
        cursor = QTextCursor(block)
        self.setTextCursor(cursor)
        self.ensureCursorVisible()

    def _refresh_extra_selections(self) -> None:
        """Apply cursor and playback highlights together to avoid flicker."""
        if self.isReadOnly():
            return
        selections: list[QTextEdit.ExtraSelection] = []

        cursor_selection = QTextEdit.ExtraSelection()
        cursor_selection.format.setBackground(QColor("#FFFFFF"))
        cursor_selection.format.setForeground(QColor("#1A1E22"))
        cursor_selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
        cursor_selection.cursor = self.textCursor()
        cursor_selection.cursor.clearSelection()
        selections.append(cursor_selection)

        if self._playback_line_number is not None:
            block = self.document().findBlockByNumber(self._playback_line_number - 1)
            if block.isValid():
                playback_selection = QTextEdit.ExtraSelection()
                playback_selection.format.setBackground(QColor("#0F4EB8"))
                playback_selection.format.setProperty(QTextCharFormat.Property.FullWidthSelection, True)
                playback_selection.cursor = QTextCursor(block)
                playback_selection.cursor.clearSelection()
                selections.append(playback_selection)
        self.setExtraSelections(selections)


class GCodeEditorWidget(QWidget):
    """A focused editor panel for viewing and editing G-code."""

    def __init__(self, parent: QWidget | None = None) -> None:
        """Create the editor with CNC-friendly monospace styling."""
        super().__init__(parent)
        self._editor = GCodePlainTextEdit(self)
        self._editor.setPlainText(DEFAULT_GCODE)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._editor)

    def text(self) -> str:
        """Return the current editor text."""
        return self._editor.toPlainText()

    def set_text(self, content: str) -> None:
        """Replace the editor content."""
        self._editor.setPlainText(content)
