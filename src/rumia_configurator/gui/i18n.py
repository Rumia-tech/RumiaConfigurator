"""Interface language: Qt translators switched at run time (UI-I18N-01, FR-APP-03).

Source strings are English. Installing or removing a translator makes Qt send
``QEvent.LanguageChange`` to every widget; each view then calls its
``retranslate()``, so the language changes without a restart.
"""

from __future__ import annotations

import logging
from importlib.resources import as_file, files

from PySide6.QtCore import QLibraryInfo, QLocale, QObject, QTranslator, Signal
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)

SOURCE_LANGUAGE = "en"
LANGUAGES = ("it", "en")
# Shown in the language menu in their own language, never translated.
LANGUAGE_NAMES = {"it": "Italiano", "en": "English"}
CATALOG = "rumia_configurator"


def resolve_language(setting: str, system: QLocale | None = None) -> str:
    """Language to use for ``setting``: ``""`` follows the system, falling back to English."""
    if setting in LANGUAGES:
        return setting
    locale = system if system is not None else QLocale.system()
    for name in locale.uiLanguages():
        code = name.split("-")[0].split("_")[0].lower()
        if code in LANGUAGES:
            return code
    return SOURCE_LANGUAGE


class LanguageManager(QObject):
    """Owns the installed translators; emits ``changed`` with the language code."""

    changed = Signal(str)

    def __init__(self, app: QApplication, setting: str = "") -> None:
        super().__init__(app)
        self._app = app
        self._setting = ""
        self._language = SOURCE_LANGUAGE
        self._translators: list[QTranslator] = []
        self.set_language(setting)

    @property
    def setting(self) -> str:
        """The user's choice: ``""`` (system), ``"it"`` or ``"en"``."""
        return self._setting

    @property
    def language(self) -> str:
        """The language actually in use."""
        return self._language

    def set_language(self, setting: str) -> None:
        """Switch language without a restart."""
        if setting not in ("", *LANGUAGES):
            raise ValueError(f"unsupported language {setting!r}; expected '', 'it' or 'en'")
        self._setting = setting
        language = resolve_language(setting)
        self.uninstall()
        self._language = language
        QLocale.setDefault(QLocale(language))
        # The English catalog is loaded too: it holds the plural forms.
        self._install_app_catalog(language)
        if language != SOURCE_LANGUAGE:
            self._install_qt_catalog(language)
        logger.debug("Interface language %s (setting %r)", language, setting)
        self.changed.emit(language)

    def uninstall(self) -> None:
        """Remove the translators installed by this manager."""
        for translator in self._translators:
            self._app.removeTranslator(translator)
        self._translators = []

    def _install_app_catalog(self, language: str) -> None:
        """Install the application catalog; if it is missing, log it and keep English."""
        resource = files("rumia_configurator.gui") / "translations" / f"{CATALOG}_{language}.qm"
        translator = QTranslator(self)
        with as_file(resource) as path:
            loaded = path.is_file() and translator.load(str(path))
        if not loaded:
            logger.warning(
                "Translation %s not loaded: the interface shows the untranslated "
                "English texts. "
                "Reinstall the application to restore it.",
                resource.name,
            )
            return
        self._app.installTranslator(translator)
        self._translators.append(translator)

    def _install_qt_catalog(self, language: str) -> None:
        """Qt's own strings: standard buttons and file dialogs."""
        translator = QTranslator(self)
        directory = QLibraryInfo.path(QLibraryInfo.LibraryPath.TranslationsPath)
        if translator.load(QLocale(language), "qtbase", "_", directory):
            self._app.installTranslator(translator)
            self._translators.append(translator)
        else:
            logger.warning("Qt translation qtbase_%s not found in %s", language, directory)
