"""Brand components built on the style sheet roles (UI-CMP-01..04, UI-COL-04).

Every color comes from the theme: widgets only set the ``role``, ``variant``,
``kind`` and ``state`` properties read by ``theme/qss.py``. Callers pass
already translated text.
"""

from __future__ import annotations

from typing import Literal

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from rumia_configurator.gui.theme.fonts import section_label_font
from rumia_configurator.gui.theme.manager import theme_manager
from rumia_configurator.gui.theme.tokens import METRICS

ButtonVariant = Literal["primary", "secondary"]
ButtonSize = Literal["large", "normal", "bar", "compact"]
CalloutKind = Literal["info", "warning", "error"]
LedState = Literal["operational", "preop", "stopped", "absent"]


def refresh_style(widget: QWidget) -> None:
    """Re-evaluate the style sheet after a dynamic property changed."""
    style = widget.style()
    style.unpolish(widget)
    style.polish(widget)
    widget.update()


def make_button(
    text: str,
    variant: ButtonVariant = "secondary",
    size: ButtonSize = "normal",
    icon: str | None = None,
    parent: QWidget | None = None,
) -> QPushButton:
    """Push button: primary is Deep Teal, secondary white with a Line border."""
    button = QPushButton(text, parent)
    button.setProperty("variant", variant)
    if size != "normal":
        button.setProperty("buttonSize", size)
    if icon is not None:
        role = "on_primary" if variant == "primary" else "ink"
        theme_manager().bind_icon(button, icon, role)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def make_link(text: str, on_surface: bool = False, parent: QWidget | None = None) -> QPushButton:
    """Link-styled button; inside ``surface`` containers it is ink and underlined."""
    button = QPushButton(text, parent)
    button.setProperty("variant", "link")
    if on_surface:
        button.setProperty("onSurface", "true")
    button.setFlat(True)
    button.setCursor(Qt.CursorShape.PointingHandCursor)
    return button


def make_label(text: str, role: str | None = None, parent: QWidget | None = None) -> QLabel:
    """Label with an optional style sheet role (``title``, ``h2``, ``mono``…)."""
    label = QLabel(text, parent)
    if role is not None:
        label.setProperty("role", role)
    return label


class SectionLabel(QLabel):
    """Uppercase mono label above a group of fields."""

    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text.upper(), parent)
        self.setProperty("role", "section")
        self.setFont(section_label_font())

    def setText(self, text: str) -> None:  # noqa: N802 (Qt API)
        super().setText(text.upper())


class Badge(QLabel):
    """Small mono tag, e.g. RUMIA next to a recognized node."""

    def __init__(self, text: str, warning: bool = False, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setProperty("role", "badge")
        if warning:
            self.setProperty("kind", "warning")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)


class Card(QFrame):
    """White card with radius 10, Line border and an optional icon in a Surface circle."""

    def __init__(
        self, title: str | None = None, icon: str | None = None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "card")
        m = METRICS
        self.body = QVBoxLayout(self)
        self.body.setContentsMargins(m.space_xl, m.space_xl, m.space_xl, m.space_xl)
        self.body.setSpacing(m.space_l)
        self.title_label: QLabel | None = None
        if title is None and icon is None:
            return
        header = QHBoxLayout()
        header.setSpacing(m.space_m)
        if icon is not None:
            circle = QLabel(self)
            circle.setProperty("role", "card-icon")
            circle.setFixedSize(m.card_icon, m.card_icon)
            circle.setAlignment(Qt.AlignmentFlag.AlignCenter)
            theme_manager().bind_icon(circle, icon, "link", m.icon)
            header.addWidget(circle)
        if title is not None:
            self.title_label = make_label(title, "h2", self)
            header.addWidget(self.title_label)
        header.addStretch(1)
        self.body.addLayout(header)

    def set_title(self, title: str) -> None:
        """Change the title, e.g. after a language switch."""
        if self.title_label is None:
            raise RuntimeError("this card was created without a title")
        self.title_label.setText(title)


class Callout(QFrame):
    """Hint or warning with a colored bar on the left (UI-CMP-03).

    ``error`` callouts sit on ``bg`` with a red bar and red title, and always
    carry text: red is never the only signal.
    """

    def __init__(
        self,
        title: str,
        text: str = "",
        kind: CalloutKind = "info",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "callout")
        self.setProperty("kind", kind)
        m = METRICS
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.space_m + 2, m.space_m, m.space_m + 2, m.space_m)
        layout.setSpacing(m.space_xs)
        self.title_label = make_label(title, "callout-title", self)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)
        self.text_label = make_label(text, "small", self)
        self.text_label.setWordWrap(True)
        self.text_label.setVisible(bool(text))
        layout.addWidget(self.text_label)


class StatusLed(QWidget):
    """Colored dot followed by the state written out (UI-COL-04)."""

    def __init__(self, state: LedState, text: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(METRICS.space_s - 2)
        self.dot = QLabel(self)
        self.dot.setProperty("role", "led")
        self.dot.setFixedSize(METRICS.led, METRICS.led)
        layout.addWidget(self.dot, 0, Qt.AlignmentFlag.AlignVCenter)
        self.label = QLabel(self)
        layout.addWidget(self.label)
        layout.addStretch(1)
        self.set_state(state, text)

    @property
    def state(self) -> str:
        return str(self.dot.property("state"))

    def set_state(self, state: LedState, text: str) -> None:
        self.dot.setProperty("state", state)
        self.dot.setAccessibleName(text)
        self.label.setText(text)
        refresh_style(self.dot)


class ValueTile(QFrame):
    """Live value with a fixed-width font so the digits do not jump (UI-TYP-02)."""

    def __init__(
        self, caption: str, value: str, unit: str = "", parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setProperty("role", "tile")
        m = METRICS
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.space_m + 2, m.space_m + 2, m.space_m + 2, m.space_m + 2)
        layout.setSpacing(m.space_xs)
        caption_label = make_label(caption, "mono", self)
        layout.addWidget(caption_label)
        row = QHBoxLayout()
        row.setSpacing(m.space_xs + 2)
        self.value_label = make_label(value, "value", self)
        row.addWidget(self.value_label, 0, Qt.AlignmentFlag.AlignBaseline)
        self.unit_label = make_label(unit, "unit", self)
        row.addWidget(self.unit_label, 0, Qt.AlignmentFlag.AlignBaseline)
        row.addStretch(1)
        layout.addLayout(row)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)
