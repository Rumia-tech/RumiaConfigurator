"""Work area: node header and tabs (UI-LAY-03).

Node tabs: Overview, Parameters, PDO, Plots. Global tabs: Bus monitor, Log.
In Base mode only Overview and Plots are shown (FR-APP-04; the rest in T3.7).
The pages are placeholders until their tasks.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent
from PySide6.QtWidgets import QFrame, QTabWidget, QVBoxLayout, QWidget

from rumia_configurator.gui.theme.tokens import METRICS
from rumia_configurator.gui.widgets.brand import Card, make_label

TAB_KEYS = ("overview", "parameters", "pdo", "plots", "monitor", "log")
BASE_TABS = ("overview", "plots")


class PlaceholderPage(QFrame):
    """Surface page with a card explaining what will appear here."""

    def __init__(self, icon: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "panel")
        m = METRICS
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.space_xxl, m.space_xl, m.space_xxl, m.space_xl)
        self.card = Card("", icon, self)
        self.text = make_label("", None, self.card)
        self.text.setWordWrap(True)
        self.card.body.addWidget(self.text)
        layout.addWidget(self.card)
        layout.addStretch(1)

    def set_texts(self, title: str, text: str) -> None:
        self.card.set_title(title)
        self.text.setText(text)


class Workspace(QWidget):
    """Node header plus tab widget."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        m = METRICS
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QWidget(self)
        header_layout = QVBoxLayout(header)
        header_layout.setContentsMargins(m.space_xxl, m.space_l + 2, m.space_xxl, m.space_s)
        header_layout.setSpacing(m.space_xs)
        self.title = make_label("", "title", header)
        header_layout.addWidget(self.title)
        self.subtitle = make_label("", "small", header)
        self.subtitle.setWordWrap(True)
        header_layout.addWidget(self.subtitle)
        layout.addWidget(header)

        self.tabs = QTabWidget(self)
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setExpanding(False)
        icons = {
            "overview": "activity",
            "parameters": "search",
            "pdo": "cpu",
            "plots": "activity",
            "monitor": "monitor",
            "log": "info",
        }
        self.pages: dict[str, PlaceholderPage] = {}
        for key in TAB_KEYS:
            page = PlaceholderPage(icons[key], self.tabs)
            self.pages[key] = page
            self.tabs.addTab(page, "")
        layout.addWidget(self.tabs, 1)
        self._mode = "base"
        self.retranslate()
        self.set_mode("base")

    def set_mode(self, mode: str) -> None:
        """Base shows only the Overview and Plots tabs."""
        self._mode = mode
        for index, key in enumerate(TAB_KEYS):
            self.tabs.setTabVisible(index, mode == "expert" or key in BASE_TABS)

    def visible_tabs(self) -> list[str]:
        return [key for i, key in enumerate(TAB_KEYS) if self.tabs.isTabVisible(i)]

    def retranslate(self) -> None:
        self.title.setText(self.tr("No node selected"))
        self.subtitle.setText(
            self.tr("Connect to a CAN network and choose a node in the panel on the left.")
        )
        node_text = self.tr("Choose a node in the network panel to see its data here.")
        texts: dict[str, tuple[str, str]] = {
            "overview": (self.tr("Overview"), node_text),
            "parameters": (self.tr("Parameters"), node_text),
            "pdo": (self.tr("PDO"), node_text),
            "plots": (self.tr("Plots"), node_text),
            "monitor": (
                self.tr("Bus monitor"),
                self.tr("Connect to an adapter to see the CAN traffic here."),
            ),
            "log": (
                self.tr("Log"),
                self.tr("The messages of the application will appear here."),
            ),
        }
        for index, key in enumerate(TAB_KEYS):
            title, text = texts[key]
            self.tabs.setTabText(index, title)
            self.pages[key].set_texts(title, text)

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 (Qt API)
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate()
        super().changeEvent(event)
