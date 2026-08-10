"""Demo image animation and non-blocking audio playback helpers."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import (
    QEasingCurve,
    QParallelAnimationGroup,
    QPropertyAnimation,
    QRect,
    QTimer,
    QUrl,
    Qt,
)
from PySide6.QtGui import QPixmap
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QLabel, QWidget

from core.resource_utils import resource_path


IMAGE_CANDIDATES = (
    Path("assets/武陆逊.png"),
    Path("assets/demo.png"),
)
AUDIO_CANDIDATES = (
    Path("assets/demo.mp3"),
    Path("assets/demo.wav"),
)


class DemoImagePopup(QWidget):
    """A short-lived frameless image popup with fade and scale animation."""

    def __init__(self, image_path: Path, anchor: QWidget) -> None:
        """Create the image popup near the right-side work area."""
        super().__init__(anchor.window(), Qt.WindowType.FramelessWindowHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setWindowOpacity(0.0)

        pixmap = QPixmap(str(image_path))
        self._label = QLabel(self)
        self._label.setObjectName("demoImageLabel")
        self._label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._label.setPixmap(
            pixmap.scaled(
                360,
                260,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
        )
        self._label.setStyleSheet(
            """
            QLabel#demoImageLabel {
                background: rgba(15, 23, 42, 220);
                border: 1px solid rgba(148, 163, 184, 180);
                border-radius: 12px;
                padding: 12px;
            }
            """
        )
        self.resize(self._label.pixmap().size().width() + 28, self._label.pixmap().size().height() + 28)
        self._label.setGeometry(0, 0, self.width(), self.height())

        self._anchor = anchor
        self._animation_group: QParallelAnimationGroup | None = None

    def play(self) -> None:
        """Show the popup and automatically close it after the animation."""
        end_rect = self._target_geometry()
        start_rect = QRect(
            end_rect.center().x() - int(end_rect.width() * 0.42),
            end_rect.center().y() - int(end_rect.height() * 0.42),
            int(end_rect.width() * 0.84),
            int(end_rect.height() * 0.84),
        )
        self.setGeometry(start_rect)
        self.show()
        self.raise_()

        opacity = QPropertyAnimation(self, b"windowOpacity", self)
        opacity.setDuration(520)
        opacity.setStartValue(0.0)
        opacity.setEndValue(0.96)
        opacity.setEasingCurve(QEasingCurve.Type.OutCubic)

        geometry = QPropertyAnimation(self, b"geometry", self)
        geometry.setDuration(620)
        geometry.setStartValue(start_rect)
        geometry.setEndValue(end_rect)
        geometry.setEasingCurve(QEasingCurve.Type.OutBack)

        self._animation_group = QParallelAnimationGroup(self)
        self._animation_group.addAnimation(opacity)
        self._animation_group.addAnimation(geometry)
        self._animation_group.start()

        QTimer.singleShot(2600, self._fade_out)

    def _target_geometry(self) -> QRect:
        """Place the popup over the anchor without covering the whole workspace."""
        anchor_rect = self._anchor.rect()
        center = self._anchor.mapToGlobal(anchor_rect.center())
        return QRect(
            center.x() - self.width() // 2 + 90,
            center.y() - self.height() // 2 - 20,
            self.width(),
            self.height(),
        )

    def _fade_out(self) -> None:
        """Fade out and close the popup."""
        fade = QPropertyAnimation(self, b"windowOpacity", self)
        fade.setDuration(520)
        fade.setStartValue(self.windowOpacity())
        fade.setEndValue(0.0)
        fade.setEasingCurve(QEasingCurve.Type.InCubic)
        fade.finished.connect(self.close)
        fade.start(QPropertyAnimation.DeletionPolicy.DeleteWhenStopped)


class DemoEffectController:
    """Find and play optional demo image/audio assets without blocking the UI."""

    def __init__(self, anchor: QWidget) -> None:
        """Create a controller rooted at the project directory."""
        self._anchor = anchor
        self._player = QMediaPlayer(anchor)
        self._audio_output = QAudioOutput(anchor)
        self._player.setAudioOutput(self._audio_output)
        self._audio_output.setVolume(0.75)
        self._popups: list[DemoImagePopup] = []

    def play(self) -> list[str]:
        """Play available demo effects and return non-fatal missing-asset messages."""
        return self.play_easter_egg()

    def play_easter_egg(self) -> list[str]:
        """Play the optional easter-egg image and audio assets."""
        messages: list[str] = []
        image_path = self._find_existing(IMAGE_CANDIDATES)
        audio_path = self._find_existing(AUDIO_CANDIDATES)

        if image_path is None:
            messages.append("未找到演示图片，已跳过动效")
        else:
            self._show_image(image_path)

        if audio_path is None:
            messages.append("未找到演示音频，已跳过播放")
        else:
            self._play_audio(audio_path)

        return messages

    def _find_existing(self, candidates: tuple[Path, ...]) -> Path | None:
        """Return the first existing demo asset path from known locations."""
        for candidate in candidates:
            path = resource_path(candidate)
            if path.is_file():
                return path
        return None

    def _show_image(self, image_path: Path) -> None:
        """Show one animated image popup."""
        popup = DemoImagePopup(image_path, self._anchor)
        self._popups.append(popup)
        popup.destroyed.connect(lambda: self._remove_popup(popup))
        popup.play()

    def _play_audio(self, audio_path: Path) -> None:
        """Play one audio file asynchronously."""
        self._player.stop()
        self._player.setSource(QUrl.fromLocalFile(str(audio_path)))
        self._player.play()

    def _remove_popup(self, popup: DemoImagePopup) -> None:
        """Drop closed popups from the retained reference list."""
        if popup in self._popups:
            self._popups.remove(popup)
