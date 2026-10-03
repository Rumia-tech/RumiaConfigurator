"""Top bar: logo, adapter, bitrate, connection, wizard, Base/Expert, language, menu (UI-LAY-01)."""

from __future__ import annotations

from importlib.resources import files

from PySide6.QtCore import QEvent, Qt, Signal, SignalInstance
from PySide6.QtGui import QAction, QActionGroup, QFontMetrics, QPixmap
from PySide6.QtWidgets import (
    QButtonGroup,
    QFrame,
    QHBoxLayout,
    QLabel,
    QMenu,
    QWidget,
)

from rumia_configurator.core.connection import BACKENDS, BITRATES, AdapterInfo, ConnectionState
from rumia_configurator.gui.i18n import LANGUAGE_NAMES, LANGUAGES
from rumia_configurator.gui.theme.fonts import mono_font
from rumia_configurator.gui.theme.manager import ThemeManager
from rumia_configurator.gui.theme.tokens import METRICS, Theme
from rumia_configurator.gui.widgets.brand import SectionLabel, StatusLed, make_button, make_label

LOGO_HEIGHT = 22
ADAPTER_TEXT_WIDTH = 170  # longer adapter names are elided; the full name is in the tooltip


def format_bitrate(bitrate: int) -> str:
    """``1000000`` -> ``"1000 kbit/s"``; units are not translated."""
    return f"{bitrate // 1000} kbit/s"


def adapter_text(backend: str, channel: str, kind: str | None = None) -> str:
    """Short name of an adapter for the top bar, e.g. ``"Rumia USB-CAN · COM5"``.

    Brand and product names are not translated.
    """
    if kind == "rumia":
        return f"Rumia USB-CAN · {channel}"
    if kind == "canable":
        return f"CANable · {channel}"
    if backend == "slcan":
        return f"SLCAN · {channel}"
    family = BACKENDS[backend].label if backend in BACKENDS else backend
    return f"{family} · {channel}"


class TopBar(QFrame):
    """Signals carry the user's choices; the main window applies and saves them."""

    mode_requested = Signal(str)  # "base" | "expert"
    language_requested = Signal(str)  # "" | "it" | "en"
    theme_requested = Signal(str)  # "system" | "light" | "dark"
    export_logs_requested = Signal()
    quit_requested = Signal()
    adapter_selected = Signal(str, str)  # backend, channel
    refresh_adapters_requested = Signal()
    other_adapter_requested = Signal()
    bitrate_selected = Signal(int)  # bit/s
    connect_clicked = Signal()  # Connect or Disconnect, depending on the state

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
        self.adapter_menu = QMenu(self)
        self.adapter_actions = QActionGroup(self)
        self.refresh_action = QAction(self)
        self.refresh_action.triggered.connect(self.refresh_adapters_requested)
        self.other_action = QAction(self)
        self.other_action.triggered.connect(self.other_adapter_requested)
        self.no_adapter_action = QAction(self)
        self.no_adapter_action.setEnabled(False)
        self.adapter.setMenu(self.adapter_menu)
        layout.addWidget(self.adapter)
        self.bitrate = make_button(format_bitrate(bitrate), size="bar", icon="chevron-down")
        self.bitrate.setFont(mono_font())
        self.bitrate_menu = QMenu(self)
        self.bitrate_actions = QActionGroup(self)
        for value in BITRATES:
            action = self.bitrate_menu.addAction(format_bitrate(value))
            action.setCheckable(True)
            action.setChecked(value == bitrate)
            action.setData(value)
            self.bitrate_actions.addAction(action)
            action.triggered.connect(lambda _checked=False, v=value: self.bitrate_selected.emit(v))
        self.bitrate.setMenu(self.bitrate_menu)
        layout.addWidget(self.bitrate)
        self.connect_button = make_button("", "primary", "bar", parent=self)
        self.connect_button.clicked.connect(self.connect_clicked)
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

        self._adapters: list[AdapterInfo] = []
        self._selection: tuple[str, str] | None = None
        self._selection_text: str | None = None
        self._state = ConnectionState.DISCONNECTED
        self._demo = False

        theme_manager.changed.connect(self._on_theme_changed)
        self._on_theme_changed(theme_manager.theme)
        self.retranslate()
        self.set_adapters([])

    @staticmethod
    def _add_choice(
        menu: QMenu, group: QActionGroup, value: str, signal: SignalInstance
    ) -> QAction:
        """Add a checkable menu item that emits ``signal`` with ``value``."""
        action = menu.addAction("")
        action.setCheckable(True)
        action.setData(value)
        group.addAction(action)
        action.triggered.connect(lambda _checked=False, v=value: signal.emit(v))
        return action

    def set_mode(self, mode: str) -> None:
        """Show ``"base"`` or ``"expert"`` as the checked button."""
        self.expert_button.setChecked(mode == "expert")
        self.base_button.setChecked(mode != "expert")

    def set_language(self, setting: str, language: str) -> None:
        """Show the choice in the menu and the language in use on the button."""
        for action in self.language_actions.actions():
            action.setChecked(action.data() == setting)
        self.language_button.setText(language.upper())

    def set_theme_mode(self, mode: str) -> None:
        """Check the theme menu item of ``mode``."""
        for value, action in self._theme_choices.items():
            action.setChecked(value == mode)

    # ----- connection (FR-CON-01..04) -----

    def set_adapters(self, adapters: list[AdapterInfo]) -> None:
        """Fill the adapter menu: adapters found, then Refresh list and Other adapter…."""
        self._adapters = list(adapters)
        for action in self.adapter_actions.actions():
            self.adapter_actions.removeAction(action)
            action.deleteLater()
        self.adapter_menu.clear()
        for adapter in self._adapters:
            text = f"{adapter.description} · {adapter.channel}"
            if adapter.kind == "rumia":
                text = f"RUMIA · {text}"
            if adapter.usb_id:
                text += f" ({adapter.usb_id})"
            action = QAction(text, self)
            action.setCheckable(True)
            action.setData((adapter.backend, adapter.channel))
            action.setChecked((adapter.backend, adapter.channel) == self._selection)
            action.triggered.connect(
                lambda _checked=False, a=adapter: self.adapter_selected.emit(a.backend, a.channel)
            )
            self.adapter_actions.addAction(action)
            self.adapter_menu.addAction(action)
        if not self._adapters:
            self.adapter_menu.addAction(self.no_adapter_action)
        self.adapter_menu.addSeparator()
        self.adapter_menu.addAction(self.refresh_action)
        self.adapter_menu.addAction(self.other_action)

    def adapter_info(self, backend: str, channel: str) -> AdapterInfo | None:
        """The listed adapter with ``backend`` and ``channel``, if any."""
        for adapter in self._adapters:
            if (adapter.backend, adapter.channel) == (backend, channel):
                return adapter
        return None

    def set_selection(self, backend: str, channel: str) -> None:
        """Show the chosen adapter on the button and check it in the menu."""
        self._selection = (backend, channel)
        info = self.adapter_info(backend, channel)
        self._selection_text = adapter_text(backend, channel, info.kind if info else None)
        for action in self.adapter_actions.actions():
            action.setChecked(action.data() == self._selection)
        self._update_connection_widgets()

    def set_bitrate(self, bitrate: int) -> None:
        """Show ``bitrate`` (bit/s) on the button and check it in the menu."""
        self.bitrate.setText(format_bitrate(bitrate))
        for action in self.bitrate_actions.actions():
            action.setChecked(action.data() == bitrate)

    def set_demo(self) -> None:
        """Demo mode: the adapter is the virtual bus and cannot be changed."""
        self._demo = True
        self._update_connection_widgets()

    def set_connection_state(self, state: ConnectionState) -> None:
        """Connect/Disconnect button, LED and locks follow the connection state."""
        self._state = state
        self._update_connection_widgets()

    def _update_connection_widgets(self) -> None:
        state = self._state
        idle = state in (ConnectionState.DISCONNECTED, ConnectionState.LOST)
        if self._demo:
            text = self.tr("Virtual bus (demo)")
        elif self._selection_text is not None:
            text = self._selection_text
        else:
            text = self.tr("No adapter")
        shown = QFontMetrics(self.adapter.font()).elidedText(
            text, Qt.TextElideMode.ElideMiddle, ADAPTER_TEXT_WIDTH
        )
        self.adapter.setText(shown)
        self.adapter.setToolTip(text if shown != text else self.tr("Choose the USB-CAN adapter"))
        self.adapter.setEnabled(idle and not self._demo)
        self.bitrate.setEnabled(idle and not self._demo)
        if state == ConnectionState.CONNECTED:
            self.connect_button.setText(self.tr("Disconnect"))
            self.connect_button.setEnabled(not self._demo)
            self.connection.set_state("operational", self.tr("Connected"))
        elif state == ConnectionState.CONNECTING:
            self.connect_button.setText(self.tr("Connecting…"))
            self.connect_button.setEnabled(False)
            self.connection.set_state("preop", self.tr("Connecting…"))
        else:
            self.connect_button.setText(self.tr("Connect"))
            self.connect_button.setEnabled(self._selection is not None and not self._demo)
            if state == ConnectionState.LOST:
                self.connection.set_state("error", self.tr("Adapter lost"))
            else:
                self.connection.set_state("stopped", self.tr("Not connected"))

    def retranslate(self) -> None:
        """Set every text, tooltip and menu item in the current language."""
        self.product.setText(self.tr("Configurator"))
        self.adapter_label.setText(self.tr("Adapter"))
        self.refresh_action.setText(self.tr("Refresh list"))
        self.other_action.setText(self.tr("Other adapter…"))
        self.no_adapter_action.setText(self.tr("No adapter found"))
        self.bitrate.setToolTip(self.tr("Bitrate of the CAN network"))
        self._update_connection_widgets()
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
