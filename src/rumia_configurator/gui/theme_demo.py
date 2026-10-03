"""Gallery of the brand components in both themes (``rumia-configurator --theme-demo``)."""

from __future__ import annotations

import logging
import sys
from collections.abc import Callable

from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QScrollArea,
    QSpinBox,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from rumia_configurator import __version__
from rumia_configurator.gui.theme.fonts import mono_font
from rumia_configurator.gui.theme.manager import MODES, ThemeManager, install_theme
from rumia_configurator.gui.theme.tokens import METRICS, TYPOGRAPHY, Theme
from rumia_configurator.gui.widgets.brand import (
    Badge,
    Callout,
    Card,
    SectionLabel,
    StatusLed,
    ValueTile,
    make_button,
    make_label,
    make_link,
)

logger = logging.getLogger(__name__)


class ThemeDemoWindow(QMainWindow):
    """Shows every component of the theme, with a Light / Dark / System switch."""

    def __init__(
        self,
        manager: ThemeManager,
        on_mode_changed: Callable[[str], None] | None = None,
    ) -> None:
        super().__init__()
        self._manager = manager
        self._on_mode_changed = on_mode_changed
        self.setWindowTitle(self.tr("Rumia Configurator - theme demo"))
        self.resize(1280, 860)

        root = QWidget(self)
        outer = QVBoxLayout(root)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)
        outer.addWidget(self._build_header())

        content = QFrame(root)
        content.setProperty("role", "panel")
        grid = QGridLayout(content)
        m = METRICS
        grid.setContentsMargins(m.space_xxl, m.space_xl, m.space_xxl, m.space_xl)
        grid.setHorizontalSpacing(m.space_xl)
        grid.setVerticalSpacing(m.space_xl)
        grid.addWidget(self._build_buttons(), 0, 0)
        grid.addWidget(self._build_typography(), 0, 1)
        grid.addWidget(self._build_values(), 1, 0)
        grid.addWidget(self._build_callouts(), 1, 1)
        grid.addWidget(self._build_inputs(), 2, 0)
        grid.addWidget(self._build_states(), 2, 1)
        grid.addWidget(self._build_table(), 3, 0, 1, 2)
        grid.setColumnStretch(0, 3)
        grid.setColumnStretch(1, 2)

        scroll = QScrollArea(root)
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setWidget(content)
        outer.addWidget(scroll, 1)
        outer.addWidget(self._build_statusbar())
        self.setCentralWidget(root)

        manager.changed.connect(self._on_theme_changed)
        self._on_theme_changed(manager.theme)

    # ----- sections -----

    def _build_header(self) -> QWidget:
        m = METRICS
        header = QFrame(self)
        layout = QHBoxLayout(header)
        layout.setContentsMargins(m.space_l, m.space_m, m.space_l, m.space_m)
        layout.setSpacing(m.space_m)
        layout.addWidget(make_label(self.tr("Theme demo"), "title"))
        layout.addWidget(make_label(f"v{__version__}", "mono"))
        layout.addStretch(1)
        layout.addWidget(SectionLabel(self.tr("Theme")))
        self.mode_buttons = QButtonGroup(self)
        self.mode_buttons.setExclusive(True)
        labels = {"system": self.tr("System"), "light": self.tr("Light"), "dark": self.tr("Dark")}
        icons = {"system": "monitor", "light": "sun", "dark": "moon"}
        for mode in MODES:
            button = make_button(labels[mode], size="bar", icon=icons[mode])
            button.setCheckable(True)
            button.setChecked(mode == self._manager.mode)
            button.setProperty("mode", mode)
            self.mode_buttons.addButton(button)
            layout.addWidget(button)
        self.mode_buttons.buttonClicked.connect(lambda b: self.set_mode(str(b.property("mode"))))
        separator = QFrame(self)
        separator.setProperty("role", "separator")
        separator.setFixedHeight(1)
        wrapper = QWidget(self)
        wrapper_layout = QVBoxLayout(wrapper)
        wrapper_layout.setContentsMargins(0, 0, 0, 0)
        wrapper_layout.setSpacing(0)
        wrapper_layout.addWidget(header)
        wrapper_layout.addWidget(separator)
        return wrapper

    def _build_buttons(self) -> QWidget:
        card = Card(self.tr("Buttons"), icon="cpu")
        row = QHBoxLayout()
        row.addWidget(make_button(self.tr("Save to sensor"), "primary", "large"), 1)
        row.addWidget(make_button(self.tr("Restore factory settings"), size="large"))
        card.body.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(make_button(self.tr("Apply to node"), "primary"))
        row.addWidget(make_button(self.tr("Read all"), icon="refresh-cw"))
        disabled_primary = make_button(self.tr("Write"), "primary")
        disabled_primary.setEnabled(False)
        row.addWidget(disabled_primary)
        disabled = make_button(self.tr("Compare"))
        disabled.setEnabled(False)
        row.addWidget(disabled)
        row.addStretch(1)
        card.body.addLayout(row)
        row = QHBoxLayout()
        row.addWidget(make_button(self.tr("Wizard"), "primary", "bar", icon="arrow-right"))
        row.addWidget(make_button("1000 kbit/s", size="bar", icon="chevron-down"))
        row.addWidget(make_button(self.tr("Scan"), size="compact", icon="refresh-cw"))
        menu = make_button("", size="bar", icon="menu")
        menu.setAccessibleName(self.tr("Menu"))
        menu.setToolTip(self.tr("Menu"))
        row.addWidget(menu)
        row.addStretch(1)
        card.body.addLayout(row)

        card.body.addWidget(SectionLabel(self.tr("Links")))
        row = QHBoxLayout()
        row.addWidget(make_link(self.tr("Generate installation report (PDF)")))
        row.addStretch(1)
        card.body.addLayout(row)
        panel = QFrame(card)
        panel.setProperty("role", "tile")
        panel_layout = QHBoxLayout(panel)
        panel_layout.setContentsMargins(METRICS.space_m, METRICS.space_m, 0, METRICS.space_m)
        panel_layout.addWidget(make_label(self.tr("On a surface panel:")))
        panel_layout.addWidget(make_link(self.tr("Associate EDS…"), on_surface=True))
        panel_layout.addStretch(1)
        card.body.addWidget(panel)
        card.body.addStretch(1)
        return card

    def _build_typography(self) -> QWidget:
        card = Card(self.tr("Typography"), icon="activity")
        card.body.addWidget(make_label(self.tr("Smart IMU"), "title"))
        card.body.addWidget(make_label(self.tr("Live data"), "h2"))
        body = make_label(
            self.tr(
                "Body text in IBM Plex Sans 13 px. Titles use Archivo at 112% width, "
                "values and identifiers IBM Plex Mono."
            )
        )
        body.setWordWrap(True)
        card.body.addWidget(body)
        card.body.addWidget(make_label("Node-ID 29 (0x1D) · COB-ID 0x19D · 4D 01 E8 FF", "mono"))
        card.body.addWidget(make_label(self.tr("Secondary text, 12 px"), "small"))
        card.body.addWidget(SectionLabel(self.tr("Section label")))
        row = QHBoxLayout()
        row.addWidget(Badge("RUMIA"))
        row.addWidget(Badge(self.tr("MODIFIED"), warning=True))
        row.addStretch(1)
        card.body.addLayout(row)
        card.body.addStretch(1)
        return card

    def _build_values(self) -> QWidget:
        card = Card(self.tr("Live values"))
        card.body.addWidget(SectionLabel(self.tr("Acceleration")))
        row = QHBoxLayout()
        row.setSpacing(METRICS.space_m)
        for axis, value in (("X", "336"), ("Y", "-24"), ("Z", "1024")):
            row.addWidget(ValueTile(axis, value, "mg"))
        card.body.addLayout(row)
        card.body.addWidget(SectionLabel(self.tr("Device status")))
        row = QHBoxLayout()
        row.setSpacing(METRICS.space_m)
        for caption, value in (
            (self.tr("Error register · 0x1001"), self.tr("0x00 · no error")),
            (self.tr("Last EMCY"), self.tr("none")),
        ):
            tile = QFrame(card)
            tile.setProperty("role", "tile-outline")
            tile_layout = QVBoxLayout(tile)
            pad = METRICS.space_m + 2
            tile_layout.setContentsMargins(pad, METRICS.space_m, pad, METRICS.space_m)
            tile_layout.setSpacing(METRICS.space_xs // 2)
            tile_layout.addWidget(make_label(caption, "mono"))
            tile_layout.addWidget(make_label(value, "strong"))
            row.addWidget(tile)
        card.body.addLayout(row)
        card.body.addStretch(1)
        return card

    def _build_callouts(self) -> QWidget:
        card = Card(self.tr("Callouts"), icon="info")
        card.body.addWidget(
            Callout(
                self.tr("1 unsaved change"),
                self.tr(
                    "The new rate is active but will be lost at power-off. "
                    "Press “Save to sensor” to make it permanent."
                ),
            )
        )
        card.body.addWidget(
            Callout(
                self.tr("Node 5 is pre-operational"),
                self.tr("It does not send PDOs. Start it from the NMT menu."),
                kind="warning",
            )
        )
        card.body.addWidget(
            Callout(
                self.tr("Write refused by node 29 (SDO abort 0x06090030)"),
                self.tr(
                    "The value is outside the range allowed for this object. "
                    "Enter a value between 10 and 1000 ms and write again."
                ),
                kind="error",
            )
        )
        card.body.addStretch(1)
        return card

    def _build_inputs(self) -> QWidget:
        card = Card(self.tr("Inputs"))
        form = QGridLayout()
        form.setHorizontalSpacing(METRICS.space_m)
        form.setVerticalSpacing(METRICS.space_s)
        search = QLineEdit()
        search.setPlaceholderText(self.tr("Search by index or name"))
        form.addWidget(make_label(self.tr("Search"), "strong"), 0, 0)
        form.addWidget(search, 0, 1)
        bitrate = QComboBox()
        bitrate.addItems(["1000 kbit/s", "500 kbit/s", "250 kbit/s", "125 kbit/s"])
        form.addWidget(make_label(self.tr("Bitrate"), "strong"), 1, 0)
        form.addWidget(bitrate, 1, 1)
        node_id = QSpinBox()
        node_id.setRange(1, 127)
        node_id.setValue(29)
        node_id.setFont(mono_font())
        form.addWidget(make_label(self.tr("Node-ID"), "strong"), 2, 0)
        form.addWidget(node_id, 2, 1)
        disabled = QLineEdit(self.tr("Read only"))
        disabled.setEnabled(False)
        form.addWidget(make_label(self.tr("Disabled"), "strong"), 3, 0)
        form.addWidget(disabled, 3, 1)
        form.addWidget(QCheckBox(self.tr("120 Ω termination resistor")), 4, 1)
        card.body.addLayout(form)
        card.body.addStretch(1)
        return card

    def _build_states(self) -> QWidget:
        card = Card(self.tr("Node states"))
        card.body.addWidget(StatusLed("operational", self.tr("Operational")))
        card.body.addWidget(StatusLed("preop", self.tr("Pre-operational")))
        card.body.addWidget(StatusLed("stopped", self.tr("Stopped")))
        card.body.addWidget(StatusLed("absent", self.tr("Absent · heartbeat timeout")))
        tabs = QTabWidget(card)
        tabs.setDocumentMode(True)
        for name in (self.tr("Overview"), self.tr("Parameters"), self.tr("PDO")):
            page = QWidget()
            page_layout = QVBoxLayout(page)
            page_layout.addWidget(
                make_label(self.tr("Content of the “%1” tab").replace("%1", name))
            )
            tabs.addTab(page, name)
        card.body.addWidget(tabs)
        card.body.addStretch(1)
        return card

    def _build_table(self) -> QWidget:
        card = Card(self.tr("Object dictionary"))
        headers = [
            self.tr("Index"),
            self.tr("Name"),
            self.tr("Type"),
            self.tr("Access"),
            self.tr("Value"),
            self.tr("Status"),
        ]
        rows = [
            ("0x1008", self.tr("Device name"), "VISIBLE_STRING", "ro", "Smart IMU", ""),
            ("0x1017", self.tr("Producer heartbeat time"), "UNSIGNED16", "rw", "1000", ""),
            (
                "0x1800:05",
                self.tr("TPDO1 event timer"),
                "UNSIGNED16",
                "rw",
                "200",
                self.tr("MODIFIED"),
            ),
            ("0x6001", self.tr("Acceleration X"), "INTEGER16", "ro", "336", ""),
            ("0x6007", self.tr("Accelerometer range"), "UNSIGNED8", "rw", "2", ""),
            (
                "0x1003:01",
                self.tr("Error history"),
                "UNSIGNED32",
                "ro",
                "0x00008130",
                self.tr("EMCY"),
            ),
        ]
        table = QTableWidget(len(rows), len(headers), card)
        table.setHorizontalHeaderLabels(headers)
        table.setAlternatingRowColors(True)
        table.setShowGrid(False)
        table.verticalHeader().setVisible(False)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        mono_columns = {0, 2, 4}
        for r, values in enumerate(rows):
            for c, value in enumerate(values):
                item = QTableWidgetItem(value)
                if c in mono_columns:
                    item.setFont(mono_font())
                table.setItem(r, c, item)
        header = table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeMode.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        table.setMinimumHeight(260)
        self._table = table
        self._emcy_row = len(rows) - 1
        card.body.addWidget(table)
        return card

    def _build_statusbar(self) -> QWidget:
        m = METRICS
        bar = QFrame(self)
        bar.setProperty("role", "statusbar")
        bar.setFixedHeight(m.statusbar_height)
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(m.space_l, 0, m.space_l, 0)
        layout.setSpacing(m.space_l)
        bus = StatusLed("operational", self.tr("Bus OK"))
        layout.addWidget(bus)
        for text in ("slcan · COM5", "1000 kbit/s", self.tr("412 frames/s"), self.tr("load 4.1%")):
            label = QLabel(text)
            label.setFont(mono_font(TYPOGRAPHY.small_px))
            layout.addWidget(label)
        layout.addStretch(1)
        last = QLabel(self.tr("Scan completed: 3 nodes found"))
        last.setProperty("muted", "true")
        last.setFont(mono_font(TYPOGRAPHY.small_px))
        layout.addWidget(last)
        return bar

    # ----- theme -----

    def set_mode(self, mode: str) -> None:
        """Switch theme and tell the caller, which saves the choice."""
        self._manager.set_mode(mode)
        for button in self.mode_buttons.buttons():
            button.setChecked(button.property("mode") == mode)
        if self._on_mode_changed is not None:
            self._on_mode_changed(mode)

    def _on_theme_changed(self, theme: Theme) -> None:
        """Repaint what the style sheet cannot reach: per-item colors in the table."""
        p = theme.palette
        modified_col = 5
        for r in range(self._table.rowCount()):
            for c in range(self._table.columnCount()):
                item = self._table.item(r, c)
                if item is None:
                    continue
                if r == self._emcy_row:
                    item.setBackground(QBrush(QColor(p.error_bg)))
                    item.setForeground(QBrush(QColor(p.error if c == modified_col else p.ink)))
                elif c == modified_col and item.text():
                    item.setForeground(QBrush(QColor(p.ink)))


def run_theme_demo() -> int:
    """Open the demo window; the theme choice is saved in the user settings."""
    from rumia_configurator.core import paths
    from rumia_configurator.core.settings import SettingsStore

    store = SettingsStore(paths.settings_path())
    settings = store.load().settings

    app = QApplication(sys.argv[:1])
    app.setApplicationName("Rumia Configurator")
    manager, fonts = install_theme(app, settings.theme)
    if fonts.missing_families:
        print(
            "Brand fonts missing: " + ", ".join(fonts.missing_families) + ". "
            "The demo uses system fonts; see the log for the cause.",
            file=sys.stderr,
        )

    def save_mode(mode: str) -> None:
        """Store the chosen theme in the user settings."""
        settings.theme = mode
        try:
            store.save(settings)
        except OSError:
            logger.exception("Could not save the theme choice")

    window = ThemeDemoWindow(manager, save_mode)
    window.show()
    return app.exec()
