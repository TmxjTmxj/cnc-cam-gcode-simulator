"""Resource path helpers compatible with source and PyInstaller builds."""

from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative_path: str | Path) -> Path:
    """Return an absolute path for bundled resources in source or PyInstaller mode."""
    if hasattr(sys, "_MEIPASS"):
        base_path = Path(getattr(sys, "_MEIPASS"))
    else:
        base_path = Path(__file__).resolve().parents[1]
    return base_path / Path(relative_path)

TEXT_FALLBACK_ENCODINGS = ("utf-8-sig", "utf-8", "gb18030", "gbk", "latin-1")


def read_text_with_fallback(path: str | Path) -> str:
    """Read text files produced by common CNC editors on Chinese Windows systems."""
    file_path = Path(path)
    last_error: UnicodeDecodeError | None = None
    for encoding in TEXT_FALLBACK_ENCODINGS:
        try:
            return file_path.read_text(encoding=encoding)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return file_path.read_text(encoding="utf-8")

