"""Start the graphical interface."""

from __future__ import annotations

import sys

from PySide6.QtWidgets import QApplication

from rumia_configurator.core import paths
from rumia_configurator.core.settings import SettingsStore
from rumia_configurator.gui.i18n import LanguageManager
from rumia_configurator.gui.main_window import MainWindow
from rumia_configurator.gui.theme.manager import install_theme


def run_gui() -> int:
    """Create the application and the main window, then run the event loop.

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

    window = MainWindow(store, settings, theme_manager, language_manager)
    if loaded.warnings:
        window.report_settings_reset()
    window.show()
    return app.exec()
