"""Top bar: logo, adapter, bitrate, connection, wizard, Base/Expert, language, menu (UI-LAY-01)."""

from __future__ import annotations

from importlib.resources import files

from PySide6.QtCore import QEvent, Qt, Signal, SignalInstance
from PySide6.QtGui import QAction, QActionGroup, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QWidget,
)

from rumia_configurator.gui.i18n import LANGUAGE_NAMES, LANGUAGES
from rumia_configurator.gui.theme.fonts import mono_font
from rumia_configurator.gui.theme.manager import ThemeManager
from rumia_configurator.gui.theme.tokens import METRICS, Theme
from rumia_configurator.gui.widgets.brand import SectionLabel, StatusLed, make_button, make_label

LOGO_HEIGHT = 22


def format_bitrate(bitrate: int) -> str:
    """``1000000`` -> ``"1000 kbit/s"``; units are not translated."""
    return f"{bitrate // 1000} kbit/s"


class TopBar(QFrame):
    """Signals carry the user's choices; the main window applies and saves them."""

    mode_requested = Signal(str)  # "base" | "expert"
    language_requested = Signal(str)  # "" | "it" | "en"
    theme_requested = Signal(str)  # "system" | "light" | "dark"
    export_logs_requested = Signal()
    quit_requested = Signal()

    def __init__(
        self, theme_manager: ThemeManager, bitrate: int, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        m = METRICS
        self._theme_manager = theme_manager
        layout = QHBoxLayout(self)
        layout.setContentsMargins(m.space_l, m.space_m, m.space_l, m.space_m)
        layout.setSpacing(m.space_m)

        self.logo = QLabel(self)
        layout.addWidget(self.logo)
        self.product = make_label("", "h2", self)
        layout.addWidget(self.product)
        separator = QFrame(self)
        separator.setProperty("role", "separator")
        separator.setFixedSize(1, 28)
        layout.addWidget(separator)

        self.adapter_label = SectionLabel("", self)
        layout.addWidget(self.adapter_label)
        self.adapter = make_button("", size="bar", icon="chevron-down", parent=self)
        self.adapter.setEnabled(False)
        layout.addWidget(self.adapter)
        self.bitrate = make_button(format_bitrate(bitrate), size="bar", icon="chevron-down")
        self.bitrate.setFont(mono_font())
        self.bitrate.setEnabled(False)
        layout.addWidget(self.bitrate)
        self.connect_button = make_button("", "primary", "bar", parent=self)
        self.connect_button.setEnabled(False)
        layout.addWidget(self.connect_button)
        self.connection = StatusLed("stopped", "", self)
        layout.addWidget(self.connection)
        layout.addStretch(1)

        self.wizard = make_button("", "secondary", "bar", icon="arrow-right", parent=self)
        self.wizard.setEnabled(False)
        layout.addWidget(self.wizard)

        self.mode_group = QButtonGroup(self)
        self.mode_group.setExclusive(True)
        self.base_button = make_button("", size="bar", parent=self)
        self.expert_button = make_button("", size="bar", parent=self)
        for mode, button in (("base", self.base_button), ("expert", self.expert_button)):
            button.setCheckable(True)
            button.setProperty("mode", mode)
            self.mode_group.addButton(button)
            layout.addWidget(button)
        self.mode_group.buttonClicked.connect(
            lambda b: self.mode_requested.emit(str(b.property("mode")))
        )

        self.language_button = make_button("", size="bar", parent=self)
        self.language_button.setFont(mono_font())
        self.language_menu = QMenu(self)
        self.language_actions = QActionGroup(self)
        self._language_system = self._add_choice(
            self.language_menu, self.language_actions, "", self.language_requested
        )
        for code in LANGUAGES:
            action = self._add_choice(
                self.language_menu, self.language_actions, code, self.language_requested
            )
            action.setText(LANGUAGE_NAMES[code])
        self.language_button.setMenu(self.language_menu)
        layout.addWidget(self.language_button)

        self.menu_button = make_button("", size="bar", icon="menu", parent=self)
        self.menu = QMenu(self)
        self.theme_menu = self.menu.addMenu("")
        self.theme_actions = QActionGroup(self)
        self._theme_choices = {
            mode: self._add_choice(self.theme_menu, self.theme_actions, mode, self.theme_requested)
            for mode in ("system", "light", "dark")
        }
        self.export_action = self.menu.addAction("")
        self.export_action.triggered.connect(self.export_logs_requested)
        self.menu.addSeparator()
        self.quit_action = self.menu.addAction("")
        self.quit_action.triggered.connect(self.quit_requested)
        self.menu_button.setMenu(self.menu)
        layout.addWidget(self.menu_button)

        theme_manager.changed.connect(self._on_theme_changed)
        self._on_theme_changed(theme_manager.theme)
        self.retranslate()

    @staticmethod
    def _add_choice(
        menu: QMenu, group: QActionGroup, value: str, signal: SignalInstance
    ) -> QAction:
        action = menu.addAction("")
        action.setCheckable(True)
        action.setData(value)
        group.addAction(action)
        action.triggered.connect(lambda _checked=False, v=value: signal.emit(v))
        return action

    def set_mode(self, mode: str) -> None:
        self.expert_button.setChecked(mode == "expert")
        self.base_button.setChecked(mode != "expert")

    def set_language(self, setting: str, language: str) -> None:
        """Show the choice in the menu and the language in use on the button."""
        for action in self.language_actions.actions():
            action.setChecked(action.data() == setting)
        self.language_button.setText(language.upper())

    def set_theme_mode(self, mode: str) -> None:
        for value, action in self._theme_choices.items():
            action.setChecked(value == mode)

    def retranslate(self) -> None:
        self.product.setText(self.tr("Configurator"))
        self.adapter_label.setText(self.tr("Adapter"))
        self.adapter.setText(self.tr("No adapter"))
        self.adapter.setToolTip(self.tr("Choose the USB-CAN adapter"))
        self.bitrate.setToolTip(self.tr("Bitrate of the CAN network"))
        self.connect_button.setText(self.tr("Connect"))
        self.connection.set_state("stopped", self.tr("Not connected"))
        self.wizard.setText(self.tr("Setup wizard"))
        self.base_button.setText(self.tr("Base"))
        self.base_button.setToolTip(self.tr("Rumia products and guided procedures"))
        self.expert_button.setText(self.tr("Expert"))
        self.expert_button.setToolTip(self.tr("Object dictionary, PDO and bus monitor"))
        self.language_button.setToolTip(self.tr("Language"))
        self._language_system.setText(self.tr("System language"))
        self.menu_button.setToolTip(self.tr("Menu"))
        self.menu_button.setAccessibleName(self.tr("Menu"))
        self.theme_menu.setTitle(self.tr("Theme"))
        self._theme_choices["system"].setText(self.tr("System"))
        self._theme_choices["light"].setText(self.tr("Light"))
        self._theme_choices["dark"].setText(self.tr("Dark"))
        self.export_action.setText(self.tr("Export logs…"))
        self.quit_action.setText(self.tr("Quit"))

    def changeEvent(self, event: QEvent) -> None:  # noqa: N802 (Qt API)
        if event.type() == QEvent.Type.LanguageChange:
            self.retranslate()
        super().changeEvent(event)

    def _on_theme_changed(self, theme: Theme) -> None:
        """The logo has a white wordmark in the dark theme."""
        logo = files("rumia_configurator.gui") / "assets" / f"logo_{theme.name.value}.png"
        data = logo.read_bytes()
        source = QPixmap()
        source.loadFromData(data)
        ratio = self.devicePixelRatioF()
        pixmap = source.scaledToHeight(
            round(LOGO_HEIGHT * ratio), Qt.TransformationMode.SmoothTransformation
        )
        pixmap.setDevicePixelRatio(ratio)
        self.logo.setPixmap(pixmap)
        self.logo.setAccessibleName("Rumia")
