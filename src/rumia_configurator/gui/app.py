"""Start the graphical interface."""

from __future__ import annotations

import logging
import sys

import can
from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import QApplication, QMessageBox

from rumia_configurator.core import paths
from rumia_configurator.core.settings import SettingsStore
from rumia_configurator.core.simulator import Simulator, default_demo_nodes
from rumia_configurator.gui.i18n import LanguageManager
from rumia_configurator.gui.main_window import MainWindow
from rumia_configurator.gui.theme.manager import install_theme

logger = logging.getLogger(__name__)


def _start_demo(app: QApplication) -> Simulator | None:
    """Start the simulated nodes of demo mode (FR-CON-06); on failure tell the user."""
    simulator = Simulator(default_demo_nodes())
    try:
        simulator.start()
    except (can.CanError, OSError, ValueError) as exc:
        logger.exception("Demo mode could not start")
        QMessageBox.critical(
            None,
            QCoreApplication.translate("app", "Demo mode"),
            QCoreApplication.translate(
                "app",
                "Demo mode could not start.\n\n"
                "Cause: the virtual CAN bus with the simulated nodes did not open (%1).\n\n"
                "Start the application without --demo, and send the logs "
                "(menu, Export logs) to Rumia support.",
            ).replace("%1", str(exc)),
        )
        return None
    app.aboutToQuit.connect(simulator.stop)
    return simulator


def run_gui(demo: bool = False) -> int:
    """Create the application and the main window, then run the event loop.

    With ``demo`` the simulated Smart IMU and INCLI Sense run on a virtual
    bus and the window shows the demo banner for the whole session.

    Qt 6 scales the interface on HiDPI screens by itself, with fractional
    factors such as 125% and 150% passed through unrounded (UI-LAY-06).
    """
    store = SettingsStore(paths.settings_path())
    loaded = store.load()
    settings = loaded.settings

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Rumia Configurator")
    app.setOrganizationName("Rumia")
    app.setOrganizationDomain("rumia.it")
    theme_manager, _fonts = install_theme(app, settings.theme)
    language_manager = LanguageManager(app, settings.language)

    demo_nodes: list[tuple[str, int]] | None = None
    simulator: Simulator | None = None
    if demo:
        simulator = _start_demo(app)
        if simulator is None:
            return 1
        demo_nodes = [(node.product_name, node.node_id) for node in simulator.nodes]

    window = MainWindow(store, settings, theme_manager, language_manager, demo_nodes)
    if loaded.warnings:
        window.report_settings_reset()
    window.show()
    if simulator is not None:
        window.start_demo_connection(simulator.channel)
    return app.exec()
