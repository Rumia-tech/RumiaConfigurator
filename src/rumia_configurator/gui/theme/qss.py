"""Qt style sheet generated from the design tokens.

Widgets choose their look with dynamic properties, never with colors:

- ``QPushButton``: ``variant`` = ``primary`` | ``secondary`` (default) | ``link``,
  ``buttonSize`` = ``large`` | ``bar`` | ``compact`` (default 36 px),
  ``onSurface`` = ``true`` for links inside ``surface`` containers.
- ``QFrame``: ``role`` = ``card`` | ``panel`` | ``tile`` | ``tile-outline`` |
  ``callout`` (with ``kind`` = ``info`` | ``warning`` | ``error``) | ``statusbar`` | ``separator``.
- ``QLabel``: ``role`` = ``title`` | ``h2`` | ``mono`` | ``value`` | ``unit`` | ``small`` |
  ``section`` | ``callout-title`` | ``badge`` (with ``kind`` = ``warning``) | ``led``
  (with ``state``) | ``card-icon``.

Qt style sheets do not support ``letter-spacing`` or ``text-transform``: the
section labels set their font in code (``widgets.SectionLabel``).
"""

from __future__ import annotations

from collections.abc import Mapping

from rumia_configurator.gui.theme.tokens import Theme

# Images the style sheet needs, as (icon name, palette role). Style sheets cannot
# recolor an SVG, so the theme manager writes recolored copies to a folder and
# passes their paths here.
STYLE_IMAGES: tuple[tuple[str, str], ...] = (
    ("chevron-down", "ink"),
    ("chevron-up", "ink"),
    ("check", "on_link"),
)


def build_stylesheet(theme: Theme, images: Mapping[str, str] | None = None) -> str:
    """Return the application style sheet for ``theme``.

    ``images`` maps the names in :data:`STYLE_IMAGES` to file paths; without it
    the arrows and check marks are left to the Fusion style.
    """
    p = theme.palette
    t = theme.typography
    m = theme.metrics
    border = 1

    def button_height(height: int) -> str:
        inner = height - 2 * border
        return f"min-height: {inner}px; max-height: {inner}px;"

    images = images or {}
    sheet = f"""
/* ---------- Buttons (UI-CMP-01) ---------- */
QPushButton {{
    background-color: {p.bg};
    color: {p.ink};
    border: {border}px solid {p.line};
    border-radius: {m.radius_button}px;
    padding: 0px {m.space_m}px;
    font-weight: 600;
    {button_height(m.button)}
}}
QPushButton:hover {{ background-color: {p.surface}; }}
QPushButton:pressed {{ background-color: {p.line}; }}
QPushButton:focus {{ border-color: {p.link}; }}
QPushButton:checked {{ background-color: {p.surface}; color: {p.ink}; border-color: {p.link}; }}
QPushButton:disabled {{ background-color: {p.surface}; color: {p.text}; border-color: {p.line}; }}

QPushButton[variant="primary"] {{
    background-color: {p.primary};
    color: {p.on_primary};
    border-color: {p.primary};
}}
QPushButton[variant="primary"]:hover {{ border-color: {p.ink}; }}
QPushButton[variant="primary"]:focus {{ border-color: {p.ink}; }}
QPushButton[variant="primary"]:pressed {{ background-color: {p.primary}; border-color: {p.ink}; }}
QPushButton[variant="primary"]:disabled {{
    background-color: {p.line};
    color: {p.text};
    border-color: {p.line};
}}

QPushButton[variant="link"] {{
    background-color: transparent;
    color: {p.link};
    border: none;
    padding: 0px;
    text-align: left;
    min-height: 0px;
    max-height: 16777215px;
}}
QPushButton[variant="link"]:hover {{ color: {p.ink}; text-decoration: underline; }}
QPushButton[variant="link"]:focus {{ text-decoration: underline; }}
QPushButton[variant="link"][onSurface="true"] {{
    color: {p.link_on_surface};
    text-decoration: underline;
}}

QPushButton[buttonSize="large"] {{ {button_height(m.button_large)} }}
QPushButton[buttonSize="bar"] {{
    {button_height(m.button_bar)}
    padding: 0px {m.space_s + 2}px;
}}
QPushButton[buttonSize="compact"] {{
    {button_height(m.button_compact)}
    padding: 0px {m.space_s + 2}px;
}}

/* ---------- Inputs ---------- */
QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {{
    background-color: {p.bg};
    color: {p.ink};
    border: {border}px solid {p.line};
    border-radius: {m.radius_button}px;
    padding: 0px {m.space_s}px;
    min-height: {m.input_height - 2 * border}px;
    selection-background-color: {p.link};
    selection-color: {p.on_link};
}}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QDoubleSpinBox:focus {{
    border-color: {p.link};
}}
QLineEdit:disabled, QComboBox:disabled, QSpinBox:disabled, QDoubleSpinBox:disabled {{
    background-color: {p.surface};
    color: {p.text};
}}
QComboBox QAbstractItemView {{
    background-color: {p.bg};
    color: {p.ink};
    border: {border}px solid {p.line};
    selection-background-color: {p.link};
    selection-color: {p.on_link};
}}

/* ---------- Tables ---------- */
QTableView, QTreeView, QListView {{
    background-color: {p.bg};
    alternate-background-color: {p.surface};
    color: {p.text};
    border: {border}px solid {p.line};
    gridline-color: {p.line};
    selection-background-color: {p.link};
    selection-color: {p.on_link};
}}
QHeaderView::section {{
    background-color: {p.surface};
    color: {p.text};
    border: none;
    border-bottom: {border}px solid {p.line};
    border-right: {border}px solid {p.line};
    padding: {m.space_xs + 2}px {m.space_s}px;
    font-weight: 600;
}}
QTableCornerButton::section {{ background-color: {p.surface}; border: none; }}
QTableView::item {{ padding: 0px {m.space_s}px; }}

/* ---------- Tabs ---------- */
QTabWidget::pane {{ border: none; border-top: {border}px solid {p.line}; }}
QTabWidget::tab-bar {{ left: {m.space_xxl}px; }}
QTabBar::tab {{
    background: transparent;
    color: {p.text};
    font-weight: 600;
    padding: {m.space_s}px 0px {m.space_s + 2}px 0px;
    margin-right: {m.space_xxl}px;
    border: none;
    border-bottom: {m.tab_indicator}px solid transparent;
}}
QTabBar::tab:selected {{ color: {p.link}; border-bottom-color: {p.link}; }}
QTabBar::tab:hover:!selected {{ color: {p.ink}; }}

/* ---------- Containers (UI-CMP-02, UI-CMP-03) ---------- */
QFrame[role="card"] {{
    background-color: {p.bg};
    border: {border}px solid {p.line};
    border-radius: {m.radius_card}px;
}}
QFrame[role="panel"] {{ background-color: {p.surface}; border: none; }}
QFrame[role="panel"] QScrollArea,
QWidget[role="node-list"] {{ background: transparent; border: none; }}
QFrame[role="node-row"] {{
    background: transparent;
    border: 1px solid transparent;
    border-radius: {m.radius_button}px;
}}
QFrame[role="node-row"]:hover {{ background-color: {p.bg}; }}
QFrame[role="node-row"][selected="true"] {{ background-color: {p.bg}; border-color: {p.link}; }}
QFrame[role="node-row"]:focus {{ border-color: {p.link}; }}
QFrame[role="tile"] {{
    background-color: {p.surface};
    border: none;
    border-radius: {m.radius_tile}px;
}}
QFrame[role="tile-outline"] {{
    background-color: transparent;
    border: {border}px solid {p.line};
    border-radius: {m.radius_tile}px;
}}
QFrame[role="callout"] {{
    background-color: {p.surface};
    border: none;
    border-left: {m.callout_bar}px solid {p.link};
}}
QFrame[role="callout"][kind="warning"] {{ border-left-color: {p.accent}; }}
QFrame[role="callout"][kind="error"] {{
    background-color: {p.bg};
    border: {border}px solid {p.line};
    border-left: {m.callout_bar}px solid {p.error};
}}
QFrame[role="separator"] {{ background-color: {p.line}; border: none; }}
QFrame[role="statusbar"] {{ background-color: {p.statusbar}; border: none; }}
QFrame[role="statusbar"] QLabel {{ color: {p.on_statusbar}; }}
QFrame[role="statusbar"] QLabel[muted="true"] {{ color: {p.statusbar_muted}; }}
QFrame[role="statusbar"] QLabel[role="led"][state="stopped"] {{
    background-color: {p.on_statusbar};
}}
QFrame[role="statusbar"] QLabel[role="led"][state="error"] {{
    background-color: {p.statusbar_error};
}}
QFrame[role="statusbar"] QLabel[error="true"] {{ color: {p.statusbar_error}; }}

/* ---------- Text ---------- */
QLabel {{ background: transparent; }}
QLabel[role="title"] {{
    font-family: "{t.title_family}";
    font-size: {t.page_title_px}px;
    font-weight: 700;
    color: {p.ink};
}}
QLabel[role="h2"] {{
    font-family: "{t.title_family}";
    font-size: {t.section_title_px}px;
    font-weight: 700;
    color: {p.ink};
}}
QLabel[role="strong"] {{ color: {p.ink}; font-weight: 600; }}
QLabel[role="mono"] {{ font-family: "{t.mono_family}"; font-size: {t.mono_px}px; }}
QLabel[role="small"] {{ font-size: {t.small_px}px; }}
QLabel[role="value"] {{
    font-family: "{t.mono_family}";
    font-size: {t.value_px}px;
    font-weight: 500;
    color: {p.ink};
}}
QLabel[role="unit"] {{ font-family: "{t.mono_family}"; font-size: {t.unit_px}px; color: {p.ink}; }}
QLabel[role="section"] {{ color: {p.text}; }}
QLabel[role="callout-title"] {{ color: {p.ink}; font-weight: 600; }}
QFrame[kind="error"] QLabel[role="callout-title"] {{ color: {p.error}; }}
QLabel[role="error"] {{ color: {p.error}; }}
QLabel[role="badge"] {{
    font-family: "{t.mono_family}";
    font-size: {t.badge_px}px;
    background-color: {p.badge};
    color: {p.on_badge};
    border-radius: {m.radius_badge}px;
    padding: {m.badge_padding[0]}px {m.badge_padding[1]}px;
}}
QLabel[role="badge"][kind="warning"] {{ background-color: {p.accent}; color: {p.on_accent}; }}
QLabel[role="card-icon"] {{
    background-color: {p.surface};
    border-radius: {m.card_icon // 2}px;
}}

/* ---------- Status LEDs (UI-COL-04: always next to a text) ---------- */
QLabel[role="led"] {{ border-radius: {m.led // 2}px; background-color: {p.text}; }}
QLabel[role="led"][state="operational"] {{ background-color: {p.link}; }}
QLabel[role="led"][state="preop"] {{ background-color: {p.accent}; }}
QLabel[role="led"][state="stopped"] {{ background-color: {p.text}; }}
QLabel[role="led"][state="absent"] {{ background-color: {p.error}; }}
QLabel[role="led"][state="error"] {{ background-color: {p.error}; }}

/* ---------- Misc ---------- */
QToolTip {{
    background-color: {p.tooltip};
    color: {p.on_tooltip};
    border: none;
    padding: {m.space_xs}px {m.space_s}px;
}}
QMenu {{ background-color: {p.bg}; color: {p.ink}; border: {border}px solid {p.line}; }}
QMenu::item:selected {{ background-color: {p.surface}; }}
QScrollArea {{ background: transparent; border: none; }}
QSplitter::handle {{ background-color: {p.line}; }}
QSplitter::handle:hover {{ background-color: {p.link}; }}
QCheckBox, QRadioButton {{ color: {p.text}; spacing: {m.space_s}px; }}
QScrollBar:vertical {{ background: {p.surface}; width: {m.scrollbar}px; margin: 0px; }}
QScrollBar:horizontal {{ background: {p.surface}; height: {m.scrollbar}px; margin: 0px; }}
QScrollBar::handle {{ background: {p.line}; border-radius: {m.scrollbar // 2}px; }}
QScrollBar::handle:vertical {{ min-height: {m.button_compact}px; }}
QScrollBar::handle:horizontal {{ min-width: {m.button_compact}px; }}
QScrollBar::handle:hover {{ background: {p.text}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0px; height: 0px; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
QCheckBox::indicator {{
    width: {m.indicator}px;
    height: {m.indicator}px;
    border: {border}px solid {p.text};
    border-radius: {m.radius_badge}px;
    background-color: {p.bg};
}}
QCheckBox::indicator:checked {{ background-color: {p.link}; border-color: {p.link}; }}
QCheckBox::indicator:disabled {{ background-color: {p.surface}; }}
"""
    if images:
        sheet += f"""
QComboBox::drop-down {{ border: none; width: {m.space_xxl}px; }}
QComboBox::down-arrow {{
    image: url("{images["chevron-down"]}");
    width: {m.arrow}px;
    height: {m.arrow}px;
}}
QSpinBox::up-button, QSpinBox::down-button,
QDoubleSpinBox::up-button, QDoubleSpinBox::down-button {{
    border: none;
    background: transparent;
    width: {m.space_xl}px;
}}
QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {{
    image: url("{images["chevron-up"]}"); width: {m.arrow}px; height: {m.arrow}px;
}}
QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {{
    image: url("{images["chevron-down"]}"); width: {m.arrow}px; height: {m.arrow}px;
}}
QCheckBox::indicator:checked {{ image: url("{images["check"]}"); }}
"""
    return sheet
