"""Main window: top bar, network panel, work area, status bar (UI-LAY-01..06)."""

from __future__ import annotations

import base64
import binascii
import logging
from pathlib import Path

from PySide6.QtCore import QByteArray, QEvent, QSize, Qt
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QMainWindow,
    QMessageBox,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from rumia_configurator.core import app_log, paths
from rumia_configurator.core.connection import (
    BACKENDS,
    AdapterInfo,
    ConnectionConfig,
    ConnectionFailure,
    ConnectionState,
    backends_for,
)
from rumia_configurator.core.network import BROADCAST, NmtCommand, NmtOutcome, NodeInfo
from rumia_configurator.core.settings import Settings, SettingsStore
from rumia_configurator.gui import dialogs
from rumia_configurator.gui.connection import ConnectionController, failure_message
from rumia_configurator.gui.i18n import LanguageManager
from rumia_configurator.gui.live import LiveData
from rumia_configurator.gui.network import NetworkController
from rumia_configurator.gui.theme.manager import ThemeManager
from rumia_configurator.gui.views import profile_dialog
from rumia_configurator.gui.views.adapter_dialog import AdapterDialog
from rumia_configurator.gui.views.demo_banner import DemoBanner
from rumia_configurator.gui.views.nmt_menu import COMMAND_NAMES
from rumia_configurator.gui.views.node_panel import NodePanel
from rumia_configurator.gui.views.status_bar import StatusBar
from rumia_configurator.gui.views.top_bar import TopBar, adapter_text
from rumia_configurator.gui.views.workspace import Workspace
from rumia_configurator.profiles.association import NodeProfile
from rumia_configurator.profiles.eds import EdsLoadError, EdsLoadErrorKind

logger = logging.getLogger(__name__)

DEFAULT_SIZE = QSize(1366, 768)  # UI-LAY-06: must fit without horizontal scrolling


class MainWindow(QMainWindow):
    """Applies and saves the user's choices: mode, language, theme, layout."""

    def __init__(
        self,
        store: SettingsStore,
        settings: Settings,
        theme_manager: ThemeManager,
        language_manager: LanguageManager,
        demo_nodes: list[tuple[str, int]] | None = None,
        connection: ConnectionController | None = None,
    ) -> None:
        """``demo_nodes`` (name, Node-ID) turns on the demo mode banner (FR-CON-06).

        ``connection`` replaces the connection controller (tests).
        """
        super().__init__()
        self._store = store
        self._settings = settings
        self._theme_manager = theme_manager
        self._language_manager = language_manager
        self.connection = connection or ConnectionController(parent=self)
        self._demo = demo_nodes is not None
        self._backend = settings.connection.backend
        self._channel = settings.connection.channel
        self._bitrate = settings.connection.bitrate
        self._connection_state = ConnectionState.DISCONNECTED  # as last reported by the signal

        bitrate = settings.connection.bitrate
        self.top_bar = TopBar(theme_manager, bitrate, self)
        self.node_panel = NodePanel(self)
        self.workspace = Workspace(self)
        self.status = StatusBar(bitrate, self)
        self.demo_banner = DemoBanner(demo_nodes, self) if demo_nodes is not None else None

        separator = QFrame(self)
        separator.setProperty("role", "separator")
        separator.setFixedHeight(1)
        self.splitter = QSplitter(Qt.Orientation.Horizontal, self)
        self.splitter.setChildrenCollapsible(False)
        self.splitter.setHandleWidth(1)
        self.splitter.addWidget(self.node_panel)
        self.splitter.addWidget(self.workspace)
        self.splitter.setStretchFactor(0, 0)
        self.splitter.setStretchFactor(1, 1)

        root = QWidget(self)
        layout = QVBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.top_bar)
        layout.addWidget(separator)
        if self.demo_banner is not None:
            layout.addWidget(self.demo_banner)
        layout.addWidget(self.splitter, 1)
        layout.addWidget(self.status)
        self.setCentralWidget(root)

        self.top_bar.mode_requested.connect(self.set_ui_mode)
        self.top_bar.language_requested.connect(self.set_language)
        self.top_bar.theme_requested.connect(self.set_theme_mode)
        self.top_bar.export_logs_requested.connect(self.export_logs)
        self.top_bar.quit_requested.connect(self.close)
        self.top_bar.adapter_selected.connect(self.select_adapter)
        self.top_bar.refresh_adapters_requested.connect(self.connection.refresh_adapters)
        self.top_bar.other_adapter_requested.connect(self.choose_other_adapter)
        self.top_bar.bitrate_selected.connect(self.select_bitrate)
        self.top_bar.connect_clicked.connect(self.toggle_connection)
        self.connection.adapters_listed.connect(self._on_adapters_listed)
        self.connection.state_changed.connect(self._on_connection_state)
        self.connection.status_updated.connect(self.status.set_controller)
        self.live = LiveData(self.connection.service, self)
        self.live.stats_updated.connect(self.status.set_traffic)
        self.network = NetworkController(self.connection.service, self)
        self._nodes: dict[int, NodeInfo] = {}
        self.node_panel.scan_requested.connect(self.network.scan)
        self.node_panel.node_selected.connect(self._on_node_selected)
        self.network.scan_running.connect(self.node_panel.set_scanning)
        self.network.nodes_changed.connect(self._on_nodes_changed)
        self.network.heartbeat_alarm.connect(self._on_heartbeat_alarm)
        self.network.scan_finished.connect(self._on_scan_finished)
        self.network.scan_failed.connect(self._on_scan_failed)
        self.network.command_verified.connect(self._on_command_verified)
        self.network.command_failed.connect(self._on_command_failed)
        self.node_panel.node_command.connect(self.request_nmt)
        self.node_panel.network_command.connect(lambda c: self.request_nmt(BROADCAST, c))
        self.workspace.nmt_requested.connect(self._on_header_nmt)
        self._profiles: dict[int, NodeProfile] = {}
        self.network.profiles_changed.connect(self._on_profiles_changed)
        self.network.profile_failed.connect(self._on_profile_failed)
        self.node_panel.profile_requested.connect(self.choose_profile)
        self.workspace.profile_change_requested.connect(self._on_header_profile)
        self.workspace.warnings_requested.connect(self._on_header_warnings)

        if self._demo:
            self.top_bar.set_demo()
        else:
            if self._channel and self._backend in BACKENDS:
                self.top_bar.set_selection(self._backend, self._channel)
            self.connection.refresh_adapters()
        self._show_connection()

        self.top_bar.set_mode(settings.ui_mode)
        self.workspace.set_mode(settings.ui_mode)
        self.top_bar.set_language(language_manager.setting, language_manager.language)
        self.top_bar.set_theme_mode(theme_manager.mode)
        self._restore_layout()
        self.retranslate()

    # ----- user choices -----

    def set_ui_mode(self, mode: str) -> None:
        """Switch between ``"base"`` and ``"expert"``: tabs and top bar follow, then save."""
        self._settings.ui_mode = mode
        self.top_bar.set_mode(mode)
        self.workspace.set_mode(mode)
        self._save()

    def set_language(self, setting: str) -> None:
        """Switch language without a restart (``""``, ``"it"`` or ``"en"``), then save."""
        self._language_manager.set_language(setting)
        self._settings.language = setting
        self.top_bar.set_language(setting, self._language_manager.language)
        self._save()

    def set_theme_mode(self, mode: str) -> None:
        """Switch theme without a restart (``"system"``, ``"light"``, ``"dark"``), then save."""
        self._theme_manager.set_mode(mode)
        self._settings.theme = mode
        self.top_bar.set_theme_mode(mode)
        self._save()

    def export_logs(self) -> None:
        """Save logs, settings and system information to a ZIP file (FR-APP-02)."""
        default = str(Path.home() / app_log.default_export_name())
        filename, _filter = QFileDialog.getSaveFileName(
            self, self.tr("Export logs"), default, self.tr("ZIP archive (*.zip)")
        )
        if not filename:
            return
        try:
            app_log.export_logs(paths.log_dir(), paths.settings_path(), Path(filename))
        except OSError as exc:
            logger.exception("Log export failed")
            QMessageBox.critical(
                self,
                self.tr("Export logs"),
                self.tr(
                    "The logs could not be saved to %1.\n\n"
                    "Cause: %2.\n\n"
                    "Choose a folder where you can write, for example Documents, and try again."
                )
                .replace("%1", filename)
                .replace("%2", str(exc)),
            )
            return
        self.status.show_event(self.tr("Logs exported to %1").replace("%1", filename))

    # ----- connection (FR-CON-01..05) -----

    def select_adapter(self, backend: str, channel: str) -> None:
        """Use this adapter for the next connection."""
        self._backend, self._channel = backend, channel
        self.top_bar.set_selection(backend, channel)
        self._show_connection()

    def choose_other_adapter(self) -> None:
        """Ask for the backend and channel of an adapter that is not listed."""
        dialog = AdapterDialog(backends_for(), self._backend, self._channel, self)
        if dialog.exec() == AdapterDialog.DialogCode.Accepted:
            self.select_adapter(*dialog.selection())

    def select_bitrate(self, bitrate: int) -> None:
        """Use ``bitrate`` (bit/s) for the next connection."""
        self._bitrate = bitrate
        self.top_bar.set_bitrate(bitrate)
        self._show_connection()

    def toggle_connection(self) -> None:
        """Connect to the chosen adapter, or disconnect."""
        if self._connection_state == ConnectionState.CONNECTED:
            self.connection.disconnect_bus()
        elif self._channel:
            config = ConnectionConfig(self._backend, self._channel, self._bitrate)
            self.connection.connect_bus(config)

    def start_demo_connection(self, channel: str) -> None:
        """Demo mode: connect to the virtual bus of the simulated nodes (FR-CON-06)."""
        self.connection.connect_virtual(channel, self._bitrate)

    def _on_adapters_listed(self, adapters: list[AdapterInfo]) -> None:
        """New adapter list: propose the first one (Rumia first) if nothing usable is chosen."""
        self.top_bar.set_adapters(adapters)
        listed = {(a.backend, a.channel) for a in adapters}
        current = (self._backend, self._channel)
        missing = self._backend in ("slcan", "socketcan") and current not in listed
        if adapters and (not self._channel or missing):
            self.select_adapter(adapters[0].backend, adapters[0].channel)
        elif self._channel:
            self.top_bar.set_selection(*current)  # refresh the name with the listed kind
            self._show_connection()

    def _on_connection_state(
        self, state: ConnectionState, failure: ConnectionFailure | None
    ) -> None:
        self._connection_state = state
        self.top_bar.set_connection_state(state)
        self._show_connection()
        if state == ConnectionState.CONNECTED:
            self.live.start()
        elif self.live.running:
            self.live.stop()
        self.network.on_connection_state(state)
        self.node_panel.set_connected(state == ConnectionState.CONNECTED)
        self._update_nmt_enabled()
        if state == ConnectionState.CONNECTED:
            self.status.show_event(self.tr("Connected"))
            if not self.connection.service.is_virtual:
                self._remember_connection()
        elif state == ConnectionState.DISCONNECTED and failure is None:
            self.status.show_event(self.tr("Disconnected"))
        if failure is not None:
            self._show_failure(failure)

    # ----- network (FR-NET-01, FR-NET-02, FR-NET-05) -----

    def _on_nodes_changed(self, nodes: list[NodeInfo]) -> None:
        self._nodes = {info.node_id: info for info in nodes}
        self.node_panel.set_nodes(nodes)
        selected = self.node_panel.selected
        self.workspace.set_node(self._nodes.get(selected) if selected is not None else None)

    def _on_node_selected(self, node_id: int) -> None:
        self.workspace.set_node(self._nodes.get(node_id))
        self.workspace.set_profile(self._profiles.get(node_id))
        self.workspace.show_notice(None)
        self._update_nmt_enabled()

    def _update_nmt_enabled(self) -> None:
        connected = self._connection_state == ConnectionState.CONNECTED
        self.workspace.set_nmt_enabled(connected and self.node_panel.selected is not None)

    # ----- profiles (FR-NET-03, FR-NET-08, FR-SDO-01, FR-SDO-12) -----

    def _on_profiles_changed(self, profiles: dict[int, NodeProfile]) -> None:
        if profiles == self._profiles:
            return
        self._profiles = dict(profiles)
        self.node_panel.set_profiles(profiles)
        selected = self.node_panel.selected
        self.workspace.set_profile(profiles.get(selected) if selected is not None else None)

    def _on_header_profile(self) -> None:
        if self.node_panel.selected is not None:
            self.choose_profile(self.node_panel.selected)

    def _on_header_warnings(self) -> None:
        selected = self.node_panel.selected
        profile = self._profiles.get(selected) if selected is not None else None
        if profile is not None and profile.warnings:
            profile_dialog.show_eds_warnings(self, profile)

    def choose_profile(self, node_id: int) -> None:
        """Ask which profile ``node_id`` uses until disconnection, and apply it."""
        choice = profile_dialog.choose_profile(self, node_id, self._profiles.get(node_id))
        if choice is None:
            return
        kind = profile_dialog.ChoiceKind
        if choice.kind == kind.PRODUCT and choice.product is not None:
            self.network.associate_product(node_id, choice.product)
        elif choice.kind == kind.FILE and choice.path is not None:
            self.network.associate_file(node_id, choice.path)
        elif choice.kind == kind.NONE:
            self.network.associate_none(node_id)
        else:
            self.network.automatic_profile(node_id)
        self.status.show_event(
            self.tr("Node %1: profile changed until disconnection").replace("%1", str(node_id))
        )

    def _on_profile_failed(self, node_id: int, error: EdsLoadError) -> None:
        """Three-part message: the node keeps its previous profile."""
        title = self.tr("EDS not loaded")
        text = "\n\n".join(
            (
                self.tr("The file %1 could not be used for node %2.")
                .replace("%1", error.path.name)
                .replace("%2", str(node_id)),
                self._eds_error_cause(error),
                self.tr(
                    "Choose an .eds or .dcf file of this device, for example from the "
                    "manufacturer's website. The node keeps its previous profile."
                ),
            )
        )
        self.status.show_event(title)
        QMessageBox.critical(self, title, text)

    def _eds_error_cause(self, error: EdsLoadError) -> str:
        """The "why" part of an EDS error, in the language of the interface."""
        if error.kind == EdsLoadErrorKind.UNREADABLE:
            return self.tr("Cause: the file cannot be read; it may have been moved or deleted.")
        if error.kind == EdsLoadErrorKind.WRONG_TYPE:
            return self.tr("Cause: only .eds and .dcf files describe a CANopen device.")
        if error.kind == EdsLoadErrorKind.EMPTY:
            return self.tr("Cause: the file describes no objects.")
        return self.tr("Cause: the file is not a valid EDS or DCF (%1).").replace(
            "%1", error.reason
        )

    # ----- NMT commands (FR-NET-04, NFR-REL-03) -----

    def _on_header_nmt(self, command: NmtCommand) -> None:
        if self.node_panel.selected is not None:
            self.request_nmt(self.node_panel.selected, command)

    def request_nmt(self, node_id: int, command: NmtCommand) -> None:
        """Send ``command`` to ``node_id`` (0: every node), confirming it first when needed.

        Commands to the whole network and resets ask for confirmation (rule 5).
        """
        needs_confirmation = node_id == BROADCAST or command.is_reset
        if needs_confirmation and not self._confirm_nmt(node_id, command):
            return
        self.workspace.show_notice(None)
        self.network.send_command(command, node_id)
        self.status.show_event(
            self._target(node_id) + ": " + self.tr("%1 sent…").replace("%1", COMMAND_NAMES[command])
        )

    def _target(self, node_id: int) -> str:
        if node_id == BROADCAST:
            return self.tr("Whole network")
        return self.tr("Node %1").replace("%1", str(node_id))

    def _confirm_nmt(self, node_id: int, command: NmtCommand) -> bool:
        """Three-part confirmation of a command to the whole network or of a reset."""
        name = COMMAND_NAMES[command]
        everyone = self.tr(
            "The command reaches every node of the network, also those not in the list."
        )
        if node_id == BROADCAST and command == NmtCommand.START:
            what = self.tr("Put every node of the network in Operational?")
            consequences = (
                everyone
                + " "
                + self.tr("The nodes start sending their PDOs: the machine can start moving.")
            )
            advice = self.tr("Confirm only if the machine is in a safe condition.")
            confirm = self.tr("Start all nodes")
        elif node_id == BROADCAST and command == NmtCommand.PRE_OPERATIONAL:
            what = self.tr("Put every node of the network in Pre-operational?")
            consequences = (
                everyone
                + " "
                + self.tr(
                    "The nodes stop sending their PDOs: a PLC or controller that uses them "
                    "gets no more data until Start."
                )
            )
            advice = self.tr("Confirm only if no one depends on these data now.")
            confirm = self.tr("Stop the PDOs of all nodes")
        elif node_id == BROADCAST:
            what = self.tr("Reset every node of the network?")
            consequences = (
                everyone
                + " "
                + self.tr(
                    "Every node restarts and sends nothing for a few moments; settings not "
                    "stored with 0x1010 go back to the stored values."
                )
            )
            advice = self.tr(
                "Confirm only if the machine is in a safe condition and you do not need "
                "the settings not stored."
            )
            confirm = self.tr("Reset all nodes")
        elif command == NmtCommand.RESET_COMMUNICATION:
            what = self.tr("Reset the communication of node %1?").replace("%1", str(node_id))
            consequences = self.tr(
                "The node restarts its communication with the stored parameters (COB-IDs, "
                "PDOs, heartbeat): changes not stored with 0x1010 are lost, and it sends "
                "nothing for a few moments."
            )
            advice = self.tr("Confirm only if you do not need the changes not stored.")
            confirm = self.tr("Reset the communication")
        else:
            what = self.tr("Reset node %1?").replace("%1", str(node_id))
            consequences = self.tr(
                "The node restarts and sends nothing for a few moments; settings not "
                "stored with 0x1010 go back to the stored values."
            )
            advice = self.tr(
                "Confirm only if the machine is in a safe condition and you do not need "
                "the settings not stored."
            )
            confirm = self.tr("Reset the node")
        title = f"{name} · {self._target(node_id)}"
        return dialogs.confirm_action(self, title, what, consequences, advice, confirm)

    def _on_command_verified(
        self, command: NmtCommand, node_id: int, outcomes: dict[int, NmtOutcome]
    ) -> None:
        """Status bar summary; a warning callout when a node did not confirm."""
        name = COMMAND_NAMES[command]
        failed = sorted(n for n, o in outcomes.items() if o != NmtOutcome.CONFIRMED)
        if node_id != BROADCAST:
            outcome = outcomes.get(node_id, NmtOutcome.NO_HEARTBEAT)
            texts = {
                NmtOutcome.CONFIRMED: self.tr("%1 confirmed by the heartbeat"),
                NmtOutcome.NOT_CONFIRMED: self.tr("the state did not change after %1"),
                NmtOutcome.NO_HEARTBEAT: self.tr("no heartbeat after %1"),
                NmtOutcome.NOT_VERIFIABLE: self.tr("%1 sent, not verifiable (heartbeat off)"),
            }
            summary = self._target(node_id) + ": " + texts[outcome].replace("%1", name)
        else:
            confirmed = len(outcomes) - len(failed)
            summary = (
                self._target(node_id)
                + ": "
                + self.tr("%1 confirmed by %2 of %3 nodes")
                .replace("%1", name)
                .replace("%2", str(confirmed))
                .replace("%3", str(len(outcomes)))
            )
        self.status.show_event(summary)
        verifiable = [n for n in failed if outcomes[n] != NmtOutcome.NOT_VERIFIABLE]
        if verifiable:
            nodes = ", ".join(str(n) for n in verifiable)
            self.workspace.show_notice(
                self.tr("%1 not confirmed by node %2").replace("%1", name).replace("%2", nodes),
                self.tr(
                    "The heartbeat did not show the expected state in time. The node may be "
                    "disconnected, refuse the command in its current state, or be slower "
                    "than its heartbeat period. Check the cable and the state in the list, "
                    "then send the command again."
                ),
            )

    def _on_command_failed(self, command: NmtCommand, node_id: int, detail: str) -> None:
        logger.warning("NMT %s to node %d not sent: %s", command.name, node_id, detail)
        self.status.show_event(
            self._target(node_id)
            + ": "
            + self.tr("%1 not sent, see the log").replace("%1", COMMAND_NAMES[command])
        )

    def _on_heartbeat_alarm(self, node_id: int, missing: bool) -> None:
        if missing:
            text = self.tr("Node %1: heartbeat missing")
        else:
            text = self.tr("Node %1: heartbeat back")
        self.status.show_event(text.replace("%1", str(node_id)))

    def _on_scan_finished(self, count: int) -> None:
        self.status.show_event(self.tr("Scan finished: %n node(s)", "", count))

    def _on_scan_failed(self, detail: str) -> None:
        logger.warning("Scan failed: %s", detail)
        self.status.show_event(self.tr("Scan failed: see the log"))

    def _show_connection(self) -> None:
        """Status bar: state, adapter and bitrate."""
        if self._demo:
            text: str | None = self.tr("virtual bus (demo)")
        elif self._channel:
            info = self.top_bar.adapter_info(self._backend, self._channel)
            text = adapter_text(self._backend, self._channel, info.kind if info else None)
        else:
            text = None
        self.status.set_connection(self._connection_state, text, self._bitrate)

    def _remember_connection(self) -> None:
        """Save the adapter and bitrate that worked, to propose them next time."""
        self._settings.connection.backend = self._backend
        self._settings.connection.channel = self._channel
        self._settings.connection.bitrate = self._bitrate
        self._save()

    def _show_failure(self, failure: ConnectionFailure) -> None:
        """Error in three parts (what, why, what to do), and in the status bar."""
        logger.warning("Connection problem: %s", failure)
        title, text = failure_message(failure)
        self.status.show_event(title)
        QMessageBox.critical(self, title, text)

    def report_settings_reset(self) -> None:
        """Tell the user that unreadable settings were replaced by defaults."""
        self.status.show_event(
            self.tr("Some settings were not valid and were reset: see the log for details.")
        )

    # ----- layout -----

    def _restore_layout(self) -> None:
        """Put back the saved panel width and window geometry, or use the defaults."""
        width = self._settings.node_panel_width
        self.splitter.setSizes([width, max(DEFAULT_SIZE.width() - width, 1)])
        geometry = self._settings.window_geometry
        if geometry:
            try:
                data = base64.b64decode(geometry, validate=True)
            except (binascii.Error, ValueError):
                data = b""
            if data and self.restoreGeometry(QByteArray(data)):
                return
            logger.warning("Saved window geometry is not valid: using the default size")
        self.resize(DEFAULT_SIZE)

    def _store_layout(self) -> None:
        """Copy the current window geometry and panel width into the settings."""
        self._settings.window_geometry = base64.b64encode(bytes(self.saveGeometry().data())).decode(
            "ascii"
        )
        panel_width = self.splitter.sizes()[0]
        if panel_width > 0:
            self._settings.node_panel_width = panel_width

    def _save(self) -> None:
        """Save the settings; on failure tell the user in the status bar."""
        try:
            self._store.save(self._settings)
        except OSError as exc:
            logger.exception("Settings not saved")
            self.status.show_event(
                self.tr(
                    "Settings not saved (%1). Check the permissions of the settings folder."
                ).replace("%1", str(exc))
            )

    def closeEvent(self, event: QCloseEvent) -> None:  # noqa: N802 (Qt API)
        self._store_layout()
        self._save()
        self.network.shutdown()
        self.connection.shutdown()
        super().closeEvent(event)

    # ----- language -----

    def retranslate(self) -> None:
        """Set the texts of the window in the current language."""
        self.setWindowTitle(self.tr("Rumia Configurator"))

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 (Qt API)
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate()
        super().changeEvent(event)
