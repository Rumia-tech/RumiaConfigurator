"""Confirmation of operations that can stop a machine or lose settings (rule 5).

Every destructive operation (NMT commands to the whole network, resets, and
later store 0x1010, restore 0x1011, LSS, bitrate change) asks through
:func:`confirm_action`. The question has three parts: what will happen, what
it causes, what to check first. The confirm button says the action in words
and **Cancel is the default**, so Enter or Esc never confirm by mistake.
"""

from __future__ import annotations

from PySide6.QtWidgets import QAbstractButton, QMessageBox, QWidget


def build_confirmation(
    parent: QWidget | None,
    title: str,
    what: str,
    consequences: str,
    advice: str,
    confirm_text: str,
) -> tuple[QMessageBox, QAbstractButton]:
    """The dialog and its confirm button, not shown yet (tests inspect it)."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Warning)
    box.setWindowTitle(title)
    box.setText(what)
    box.setInformativeText(f"{consequences}\n\n{advice}")
    confirm = box.addButton(confirm_text, QMessageBox.ButtonRole.AcceptRole)
    cancel = box.addButton(QMessageBox.StandardButton.Cancel)
    box.setDefaultButton(cancel)
    box.setEscapeButton(cancel)
    return box, confirm


def confirm_action(
    parent: QWidget | None,
    title: str,
    what: str,
    consequences: str,
    advice: str,
    confirm_text: str,
) -> bool:
    """Ask the user; True only if the confirm button was pressed."""
    box, confirm = build_confirmation(parent, title, what, consequences, advice, confirm_text)
    box.exec()
    return box.clickedButton() is confirm
