"""Network panel on the left: scan, node list, network-wide NMT commands (UI-LAY-02).

Each node is a :class:`NodeRow`: state LED with the state written out,
Node-ID, name and heartbeat. A missing heartbeat turns the LED red and says
for how long it is missing (FR-NET-05). A right click on a row opens the NMT
menu of that node; the buttons at the bottom send Start, Pre-operational and
Reset node to the whole network, after a confirmation (FR-NET-04).
"""

from __future__ import annotations

from PySide6.QtCore import QEvent, QLocale, Qt, Signal
from PySide6.QtGui import QContextMenuEvent, QFontMetrics, QKeyEvent, QMouseEvent
from PySide6.QtWidgets import (
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from rumia_configurator.core.network import NmtCommand, NmtState, NodeInfo
from rumia_configurator.gui.theme.fonts import mono_font
from rumia_configurator.gui.theme.tokens import METRICS
from rumia_configurator.gui.views.nmt_menu import NmtMenu
from rumia_configurator.gui.widgets.brand import (
    Badge,
    LedState,
    SectionLabel,
    StatusLed,
    make_button,
    make_label,
    make_link,
    refresh_style,
)
from rumia_configurator.profiles.association import NodeProfile

MIN_WIDTH = 220

_LED: dict[NmtState, LedState] = {
    NmtState.OPERATIONAL: "operational",
    NmtState.PRE_OPERATIONAL: "preop",
    NmtState.STOPPED: "stopped",
    NmtState.BOOTUP: "preop",
    NmtState.UNKNOWN: "stopped",
}


_STATE_NAMES: dict[NmtState, str] = {
    NmtState.OPERATIONAL: "Operational",
    NmtState.PRE_OPERATIONAL: "Pre-operational",
    NmtState.STOPPED: "Stopped",
    NmtState.BOOTUP: "Boot-up",
}


class NodeRow(QFrame):
    """One node of the list; click or keyboard selects it, right click opens its NMT menu."""

    clicked = Signal(int)
    command_requested = Signal(int, object)  # node_id, NmtCommand
    profile_requested = Signal(int)  # node_id: "Associate profile…"

    def __init__(self, node_id: int, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.node_id = node_id
        self.setProperty("role", "node-row")
        self.setProperty("selected", "false")
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        m = METRICS
        layout = QGridLayout(self)
        layout.setContentsMargins(m.space_s, m.space_s, m.space_s, m.space_s)
        layout.setHorizontalSpacing(m.space_s)
        layout.setVerticalSpacing(m.space_xs)
        self.id_label = make_label(str(node_id), "strong", self)
        self.id_label.setFont(mono_font())
        layout.addWidget(self.id_label, 0, 0)
        self.name_label = make_label("", "strong", self)
        layout.addWidget(self.name_label, 0, 1)
        self.badge = Badge("RUMIA", parent=self)
        self.badge.setVisible(False)
        layout.addWidget(self.badge, 0, 2)
        self.led = StatusLed("stopped", "", self)
        layout.addWidget(self.led, 1, 1)
        self.detail = make_label("", "small", self)
        layout.addWidget(self.detail, 2, 1, 1, 2)
        self.profile_link = make_link("", on_surface=True, parent=self)
        self.profile_link.clicked.connect(lambda: self.profile_requested.emit(self.node_id))
        self.profile_link.setVisible(False)
        layout.addWidget(self.profile_link, 3, 1, 1, 2)
        layout.setColumnStretch(1, 1)
        self.info: NodeInfo | None = None
        self.profile: NodeProfile | None = None

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", "true" if selected else "false")
        refresh_style(self)

    def show_info(self, info: NodeInfo) -> None:
        """Write the state of ``info``; colors always come with text."""
        self.info = info
        locale = QLocale()
        name = info.name or self.tr("Node without name")
        width = max(self.name_label.width(), 120)
        self.name_label.setText(
            QFontMetrics(self.name_label.font()).elidedText(
                name, Qt.TextElideMode.ElideRight, width
            )
        )
        self.name_label.setToolTip(name)
        if info.heartbeat_missing:
            seconds = locale.toString(info.silent_for, "f", 1)
            self.led.set_state(
                "error", self.tr("Heartbeat missing for %1 s").replace("%1", seconds)
            )
        else:
            self.led.set_state(_LED[info.nmt_state], self.state_text(info.nmt_state))
        if info.heartbeat_off:
            detail = self.tr("heartbeat off")
        elif info.heartbeat_ms:
            detail = self.tr("heartbeat %1 ms").replace("%1", str(info.heartbeat_ms))  # no 1,000
        else:
            detail = self.tr("heartbeat not read")
        if self.profile is not None and self.profile.manual:
            detail += " · " + self.tr("chosen by hand")
        self.detail.setText(detail)
        self.setAccessibleName(
            self.tr("Node %1, %2, %3")
            .replace("%1", str(info.node_id))
            .replace("%2", name)
            .replace("%3", self.led.label.text())
        )

    def set_profile(self, profile: NodeProfile | None) -> None:
        """RUMIA badge for Rumia products; "Associate profile…" for the others."""
        self.profile = profile
        self.badge.setVisible(profile is not None and profile.is_rumia)
        known = profile is not None and (profile.is_rumia or profile.manual)
        self.profile_link.setVisible(profile is not None and not known)
        self.profile_link.setText(self.tr("Associate profile…"))
        if self.info is not None:
            self.show_info(self.info)

    def state_text(self, state: NmtState) -> str:
        """NMT state written out; the CANopen state names are not translated."""
        if state == NmtState.UNKNOWN:
            return self.tr("State unknown")
        return _STATE_NAMES[state]

    def mousePressEvent(self, event: QMouseEvent) -> None:  # noqa: N802 (Qt API)
        self.clicked.emit(self.node_id)
        super().mousePressEvent(event)

    def nmt_menu(self) -> NmtMenu:
        """The NMT menu of this node, with the texts in the current language."""
        menu = NmtMenu(self)
        menu.command_chosen.connect(lambda c: self.command_requested.emit(self.node_id, c))
        return menu

    def contextMenuEvent(self, event: QContextMenuEvent) -> None:  # noqa: N802 (Qt API)
        self.clicked.emit(self.node_id)
        menu = self.nmt_menu()
        menu.exec(event.globalPos())
        menu.deleteLater()

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt API)
        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter, Qt.Key.Key_Space):
            self.clicked.emit(self.node_id)
            return
        super().keyPressEvent(event)


class NodePanel(QFrame):
    """Surface panel; its width is set by the splitter and saved between sessions."""

    scan_requested = Signal()
    node_selected = Signal(int)
    node_command = Signal(int, object)  # node_id, NmtCommand (from the row menu)
    profile_requested = Signal(int)  # node_id
    network_command = Signal(object)  # NmtCommand to every node

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setProperty("role", "panel")
        self.setMinimumWidth(MIN_WIDTH)
        m = METRICS
        layout = QVBoxLayout(self)
        layout.setContentsMargins(m.space_l, m.space_l, m.space_l, m.space_l)
        layout.setSpacing(m.space_s + 2)

        header = QHBoxLayout()
        self.title = SectionLabel("", self)
        header.addWidget(self.title)
        header.addStretch(1)
        self.scan_button = make_button("", size="compact", icon="refresh-cw", parent=self)
        self.scan_button.setEnabled(False)
        self.scan_button.clicked.connect(self.scan_requested)
        header.addWidget(self.scan_button)
        layout.addLayout(header)

        self.empty_title = make_label("", "strong", self)
        self.empty_title.setWordWrap(True)
        layout.addWidget(self.empty_title)
        self.empty_text = make_label("", "small", self)
        self.empty_text.setWordWrap(True)
        layout.addWidget(self.empty_text)

        self.list_area = QScrollArea(self)
        self.list_area.setWidgetResizable(True)
        self.list_area.setFrameShape(QFrame.Shape.NoFrame)
        self.list_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.list_widget = QWidget(self.list_area)
        self.list_widget.setProperty("role", "node-list")
        self.list_layout = QVBoxLayout(self.list_widget)
        self.list_layout.setContentsMargins(0, 0, 0, 0)
        self.list_layout.setSpacing(m.space_xs)
        self.list_layout.addStretch(1)
        self.list_area.setWidget(self.list_widget)
        layout.addWidget(self.list_area, 1)

        self.network_label = SectionLabel("", self)
        layout.addWidget(self.network_label)
        commands = QGridLayout()
        commands.setSpacing(m.space_xs + 2)
        self.start_button = make_button("", size="compact", parent=self)
        self.preop_button = make_button("", size="compact", parent=self)
        self.reset_button = make_button("", size="compact", parent=self)
        network_commands = (
            (self.start_button, NmtCommand.START),
            (self.preop_button, NmtCommand.PRE_OPERATIONAL),
            (self.reset_button, NmtCommand.RESET_NODE),
        )
        for column, (button, command) in enumerate(network_commands):
            button.setEnabled(False)
            button.clicked.connect(lambda _checked=False, c=command: self.network_command.emit(c))
            commands.addWidget(button, 0, column)
        layout.addLayout(commands)

        self.rows: dict[int, NodeRow] = {}
        self._profiles: dict[int, NodeProfile] = {}
        self.selected: int | None = None
        self._connected = False
        self._scanning = False
        self.node_count = 0
        self.retranslate()
        self._update_empty_state()

    # ----- state from the main window -----

    def set_connected(self, connected: bool) -> None:
        """Scan is possible only while connected."""
        self._connected = connected
        self._update_scan_button()
        self._update_empty_state()

    def set_scanning(self, scanning: bool) -> None:
        self._scanning = scanning
        self._update_scan_button()

    def set_nodes(self, nodes: list[NodeInfo]) -> None:
        """Show ``nodes``: rows are added, updated in place, removed."""
        ids = [info.node_id for info in nodes]
        for node_id in [n for n in self.rows if n not in ids]:
            self.rows.pop(node_id).deleteLater()
            if self.selected == node_id:
                self.selected = None
        for position, info in enumerate(nodes):
            row = self.rows.get(info.node_id)
            if row is None:
                row = NodeRow(info.node_id, self.list_widget)
                row.clicked.connect(self.select)
                row.command_requested.connect(self.node_command)
                row.profile_requested.connect(self.profile_requested)
                row.set_profile(self._profiles.get(info.node_id))
                self.rows[info.node_id] = row
                self.list_layout.insertWidget(position, row)
            row.show_info(info)
        if len(nodes) != self.node_count:
            self.node_count = len(nodes)
            self.retranslate()
        self._update_empty_state()

    def set_profiles(self, profiles: dict[int, NodeProfile]) -> None:
        """Show the profile of each node (badge, link, "chosen by hand")."""
        changed = profiles != self._profiles
        self._profiles = dict(profiles)
        if changed:
            for node_id, row in self.rows.items():
                row.set_profile(profiles.get(node_id))

    def select(self, node_id: int) -> None:
        """Select a node (click, keyboard or code) and tell the main window."""
        if node_id not in self.rows:
            return
        self.selected = node_id
        for other, row in self.rows.items():
            row.set_selected(other == node_id)
        self.node_selected.emit(node_id)

    def keyPressEvent(self, event: QKeyEvent) -> None:  # noqa: N802 (Qt API)
        """Up and Down move the selection."""
        ids = sorted(self.rows)
        if ids and event.key() in (Qt.Key.Key_Up, Qt.Key.Key_Down):
            step = -1 if event.key() == Qt.Key.Key_Up else 1
            current = ids.index(self.selected) if self.selected in ids else -step
            target = ids[max(0, min(len(ids) - 1, current + step))]
            self.select(target)
            self.rows[target].setFocus()
            return
        super().keyPressEvent(event)

    def _update_scan_button(self) -> None:
        for button in (self.start_button, self.preop_button, self.reset_button):
            button.setEnabled(self._connected)
        self.scan_button.setEnabled(self._connected and not self._scanning)
        self.scan_button.setText(self.tr("Scanning…") if self._scanning else self.tr("Scan"))

    def _update_empty_state(self) -> None:
        empty = not self.rows
        self.empty_title.setVisible(empty)
        self.empty_text.setVisible(empty)
        self.list_area.setVisible(not empty)
        if self._connected:
            self.empty_text.setText(
                self.tr(
                    "Nodes with a heartbeat appear by themselves. Press Scan to find the others."
                )
            )
        else:
            self.empty_text.setText(
                self.tr("Connect to the adapter, then press Scan to find the nodes on the network.")
            )

    def retranslate(self) -> None:
        """Set every text of the panel in the current language."""
        self.title.setText(self.tr("Network · %n node(s)", "", self.node_count))
        self._update_scan_button()
        self.scan_button.setToolTip(self.tr("Look for the nodes on the network"))
        self.empty_title.setText(self.tr("No nodes yet"))
        self.network_label.setText(self.tr("Commands to the whole network"))
        self.start_button.setText(self.tr("Start"))
        self.start_button.setToolTip(
            self.tr("Put every node of the network in Operational state (asks for confirmation)")
        )
        self.preop_button.setText(self.tr("Pre-op"))
        self.preop_button.setToolTip(
            self.tr(
                "Put every node of the network in Pre-operational state (asks for confirmation)"
            )
        )
        self.reset_button.setText(self.tr("Reset"))
        self.reset_button.setToolTip(
            self.tr("Restart every node of the network (asks for confirmation)")
        )
        if hasattr(self, "rows"):
            self._update_empty_state()
            for row in self.rows.values():
                row.set_profile(row.profile)

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 (Qt API)
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate()
        super().changeEvent(event)
