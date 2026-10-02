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
from rumia_configurator.core.settings import Settings, SettingsStore
from rumia_configurator.gui.i18n import LanguageManager
from rumia_configurator.gui.theme.manager import ThemeManager
from rumia_configurator.gui.views.node_panel import NodePanel
from rumia_configurator.gui.views.status_bar import StatusBar
from rumia_configurator.gui.views.top_bar import TopBar
from rumia_configurator.gui.views.workspace import Workspace

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
    ) -> None:
        super().__init__()
        self._store = store
        self._settings = settings
        self._theme_manager = theme_manager
        self._language_manager = language_manager

        bitrate = settings.connection.bitrate
        self.top_bar = TopBar(theme_manager, bitrate, self)
        self.node_panel = NodePanel(self)
        self.workspace = Workspace(self)
        self.status = StatusBar(bitrate, self)

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
        layout.addWidget(self.splitter, 1)
        layout.addWidget(self.status)
        self.setCentralWidget(root)

        self.top_bar.mode_requested.connect(self.set_ui_mode)
        self.top_bar.language_requested.connect(self.set_language)
        self.top_bar.theme_requested.connect(self.set_theme_mode)
        self.top_bar.export_logs_requested.connect(self.export_logs)
        self.top_bar.quit_requested.connect(self.close)

        self.top_bar.set_mode(settings.ui_mode)
        self.workspace.set_mode(settings.ui_mode)
        self.top_bar.set_language(language_manager.setting, language_manager.language)
        self.top_bar.set_theme_mode(theme_manager.mode)
        self._restore_layout()
        self.retranslate()

    # ----- user choices -----

    def set_ui_mode(self, mode: str) -> None:
        self._settings.ui_mode = mode
        self.top_bar.set_mode(mode)
        self.workspace.set_mode(mode)
        self._save()

    def set_language(self, setting: str) -> None:
        self._language_manager.set_language(setting)
        self._settings.language = setting
        self.top_bar.set_language(setting, self._language_manager.language)
        self._save()

    def set_theme_mode(self, mode: str) -> None:
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

    def report_settings_reset(self) -> None:
        """Tell the user that unreadable settings were replaced by defaults."""
        self.status.show_event(
            self.tr("Some settings were not valid and were reset: see the log for details.")
        )

    # ----- layout -----

    def _restore_layout(self) -> None:
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
        self._settings.window_geometry = base64.b64encode(bytes(self.saveGeometry().data())).decode(
            "ascii"
        )
        panel_width = self.splitter.sizes()[0]
        if panel_width > 0:
            self._settings.node_panel_width = panel_width

    def _save(self) -> None:
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
        super().closeEvent(event)

    # ----- language -----

    def retranslate(self) -> None:
        self.setWindowTitle(self.tr("Rumia Configurator"))

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 (Qt API)
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate()
        super().changeEvent(event)
