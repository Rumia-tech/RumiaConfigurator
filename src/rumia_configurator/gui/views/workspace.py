"""Work area: node header and tabs (UI-LAY-03).

Node tabs: Overview, Parameters, PDO, Plots. Global tabs: Bus monitor, Log.
In Base mode only Overview and Plots are shown (FR-APP-04; the rest in T3.7).
The pages are placeholders until their tasks.
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, Signal
from PySide6.QtWidgets import QFrame, QHBoxLayout, QTabWidget, QVBoxLayout, QWidget

from rumia_configurator.core.network import NodeInfo
from rumia_configurator.gui.theme.tokens import METRICS
from rumia_configurator.gui.views.nmt_menu import NmtMenu
from rumia_configurator.gui.widgets.brand import (
    Callout,
    Card,
    make_button,
    make_label,
    make_link,
)
from rumia_configurator.profiles.association import NodeProfile, ProfileSource

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
        """Set the card title and the explanation of the placeholder."""
        self.card.set_title(title)
        self.text.setText(text)


class Workspace(QWidget):
    """Node header (with the NMT menu of the node) plus tab widget."""

    nmt_requested = Signal(object)  # NmtCommand for the node in the header
    profile_change_requested = Signal()  # "Change profile…"
    warnings_requested = Signal()  # "N EDS warnings"

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
        title_row = QHBoxLayout()
        self.title = make_label("", "title", header)
        title_row.addWidget(self.title, 1)
        self.nmt_button = make_button("NMT", size="compact", icon="chevron-down", parent=header)
        self.nmt_menu = NmtMenu(self.nmt_button)
        self.nmt_menu.command_chosen.connect(self.nmt_requested)
        self.nmt_button.setMenu(self.nmt_menu)
        self.nmt_button.setEnabled(False)
        title_row.addWidget(self.nmt_button)
        header_layout.addLayout(title_row)
        self.subtitle = make_label("", "small", header)
        self.subtitle.setWordWrap(True)
        header_layout.addWidget(self.subtitle)
        profile_row = QHBoxLayout()
        profile_row.setSpacing(m.space_s)
        self.profile_label = make_label("", "small", header)
        profile_row.addWidget(self.profile_label)
        self.warnings_link = make_link("", parent=header)
        self.warnings_link.clicked.connect(self.warnings_requested)
        profile_row.addWidget(self.warnings_link)
        self.change_profile_link = make_link("", parent=header)
        self.change_profile_link.clicked.connect(self.profile_change_requested)
        profile_row.addWidget(self.change_profile_link)
        profile_row.addStretch(1)
        header_layout.addLayout(profile_row)
        self.notice = Callout("", "", "warning", header)
        self.notice.setVisible(False)
        header_layout.addWidget(self.notice)
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
        self._node: NodeInfo | None = None
        self._profile: NodeProfile | None = None
        self.retranslate()
        self.set_mode("base")

    def set_mode(self, mode: str) -> None:
        """Base shows only the Overview and Plots tabs."""
        self._mode = mode
        for index, key in enumerate(TAB_KEYS):
            self.tabs.setTabVisible(index, mode == "expert" or key in BASE_TABS)

    def set_node(self, info: NodeInfo | None) -> None:
        """Show the selected node in the header (``None``: no node selected)."""
        self._node = info
        self._show_header()

    def set_profile(self, profile: NodeProfile | None) -> None:
        """Show the profile of the node in the header."""
        self._profile = profile
        self._show_profile()

    def _show_profile(self) -> None:
        profile = self._profile
        visible = self._node is not None and profile is not None
        for widget in (self.profile_label, self.change_profile_link):
            widget.setVisible(visible)
        self.warnings_link.setVisible(visible and bool(profile and profile.warnings))
        if not visible or profile is None:
            return
        how = {
            ProfileSource.RECOGNIZED: self.tr("recognised by its name"),
            ProfileSource.MANUAL_PRODUCT: self.tr("chosen by hand until disconnection"),
            ProfileSource.MANUAL_FILE: self.tr("chosen by hand until disconnection"),
            ProfileSource.MANUAL_NONE: self.tr("chosen by hand until disconnection"),
            ProfileSource.NONE: self.tr("not recognised"),
        }[profile.source]
        if profile.product is not None:
            what = profile.product.name
        elif profile.eds_path is not None:
            what = profile.eds_path.name
        else:
            what = self.tr("no profile, only the CiA 301 objects")
        parts = [what]
        if profile.product is not None and profile.eds_path is not None:
            parts.append(profile.eds_path.name)
        parts.append(how)
        self.profile_label.setText(self.tr("Profile: %1").replace("%1", " · ".join(parts)))
        self.warnings_link.setText(self.tr("%n EDS warning(s)", "", len(profile.warnings)))
        self.change_profile_link.setText(self.tr("Change profile…"))

    def set_nmt_enabled(self, enabled: bool) -> None:
        """The NMT menu works only with a selected node on an open connection."""
        self.nmt_button.setEnabled(enabled)

    def show_notice(self, title: str | None, text: str = "") -> None:
        """Warning callout under the header; ``None`` hides it."""
        self.notice.setVisible(title is not None)
        if title is not None:
            self.notice.title_label.setText(title)
            self.notice.text_label.setText(text)
            self.notice.text_label.setVisible(bool(text))

    def _show_header(self) -> None:
        self._show_profile()
        info = self._node
        if info is None:
            self.title.setText(self.tr("No node selected"))
            self.subtitle.setText(
                self.tr("Connect to a CAN network and choose a node in the panel on the left.")
            )
            return
        node = self.tr("node %1").replace("%1", str(info.node_id))
        if info.name:
            self.title.setText(f"{info.name} · {node}")
        else:
            self.title.setText(self.tr("Node %1").replace("%1", str(info.node_id)))
        fields = (
            ("Vendor-ID", info.vendor_id),
            ("Product code", info.product_code),
            (self.tr("Revision"), info.revision),
            (self.tr("Serial"), info.serial),
        )
        known = [f"{label} 0x{value:08X}" for label, value in fields if value is not None]
        if known:
            self.subtitle.setText(" · ".join(known))
        elif info.identity_read:
            self.subtitle.setText(
                self.tr("Identity not available: the node did not answer 0x1018.")
            )
        else:
            self.subtitle.setText(self.tr("Reading the identity of the node…"))

    def visible_tabs(self) -> list[str]:
        """Keys of the tabs shown in the current mode, in order."""
        return [key for i, key in enumerate(TAB_KEYS) if self.tabs.isTabVisible(i)]

    def retranslate(self) -> None:
        """Set the header, the tab titles and the placeholder texts."""
        self.nmt_button.setToolTip(self.tr("NMT commands for this node"))
        self.nmt_menu.retranslate()
        self._show_header()
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
