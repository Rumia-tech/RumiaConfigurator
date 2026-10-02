"""Smoke test: Qt and pytest-qt work in this environment (also headless in CI)."""

from PySide6.QtWidgets import QWidget
from pytestqt.qtbot import QtBot


def test_widget_can_be_created(qtbot: QtBot) -> None:
    widget = QWidget()
    qtbot.addWidget(widget)
    widget.show()
    assert widget.isVisible()
