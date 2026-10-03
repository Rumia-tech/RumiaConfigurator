"""Choose the profile of a node, and read the warnings of its EDS (FR-SDO-01, FR-SDO-12).

The choice lasts until the connection closes: the dialog says so.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from PySide6.QtCore import QCoreApplication
from PySide6.QtWidgets import (
    QButtonGroup,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QMessageBox,
    QRadioButton,
    QVBoxLayout,
    QWidget,
)

from rumia_configurator.gui.widgets.brand import make_label
from rumia_configurator.profiles.association import NodeProfile
from rumia_configurator.profiles.catalog import PRODUCTS, Product
from rumia_configurator.profiles.eds import EdsWarning, EdsWarningCode

MAX_LISTED_OBJECTS = 4


class ChoiceKind(StrEnum):
    PRODUCT = "product"
    FILE = "file"
    NONE = "none"
    AUTOMATIC = "automatic"


@dataclass(frozen=True)
class ProfileChoice:
    """What the user chose in the dialog."""

    kind: ChoiceKind
    product: Product | None = None
    path: Path | None = None


class ProfileDialog(QDialog):
    """Rumia products, an EDS/DCF file, no profile, or back to the automatic recognition."""

    def __init__(
        self, node_id: int, current: NodeProfile | None, parent: QWidget | None = None
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle(self.tr("Profile of node %1").replace("%1", str(node_id)))
        layout = QVBoxLayout(self)
        intro = make_label(
            self.tr(
                "Choose how the application reads node %1. The choice lasts until you disconnect."
            ).replace("%1", str(node_id)),
            None,
            self,
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)
        self.group = QButtonGroup(self)
        self.options: dict[QRadioButton, ProfileChoice] = {}
        for product in PRODUCTS:
            self._add(
                f"{product.name} · {product.eds.name}", ProfileChoice(ChoiceKind.PRODUCT, product)
            )
        self.file_option = self._add(self.tr("EDS or DCF file…"), ProfileChoice(ChoiceKind.FILE))
        self._add(self.tr("No profile (only the CiA 301 objects)"), ProfileChoice(ChoiceKind.NONE))
        if current is not None and current.manual:
            self._add(self.tr("Automatic recognition"), ProfileChoice(ChoiceKind.AUTOMATIC))
        for button, choice in self.options.items():
            layout.addWidget(button)
            if (
                current is not None
                and current.product is not None
                and choice.product == current.product
            ):
                button.setChecked(True)
        if self.group.checkedButton() is None:
            next(iter(self.options)).setChecked(True)
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

    def _add(self, text: str, choice: ProfileChoice) -> QRadioButton:
        button = QRadioButton(text, self)
        self.group.addButton(button)
        self.options[button] = choice
        return button

    def choice(self) -> ProfileChoice:
        """The option checked now."""
        checked = self.group.checkedButton()
        assert isinstance(checked, QRadioButton)
        return self.options[checked]


def choose_profile(
    parent: QWidget | None, node_id: int, current: NodeProfile | None
) -> ProfileChoice | None:
    """Ask the user; ``None`` if cancelled (also when the file dialog is cancelled)."""
    dialog = ProfileDialog(node_id, current, parent)
    if dialog.exec() != QDialog.DialogCode.Accepted:
        return None
    choice = dialog.choice()
    if choice.kind != ChoiceKind.FILE:
        return choice
    filename, _filter = QFileDialog.getOpenFileName(
        parent,
        QCoreApplication.translate("ProfileDialog", "EDS or DCF file"),
        str(Path.home()),
        QCoreApplication.translate("ProfileDialog", "Electronic data sheets (*.eds *.dcf)"),
    )
    return ProfileChoice(ChoiceKind.FILE, path=Path(filename)) if filename else None


def warning_text(warning: EdsWarning) -> str:
    """The warning in the language of the interface."""
    objects = list(warning.objects[:MAX_LISTED_OBJECTS])
    if len(warning.objects) > MAX_LISTED_OBJECTS:
        objects.append("…")
    listed = ", ".join(objects)
    if warning.code == EdsWarningCode.EMPTY_DEVICE_INFO:
        return QCoreApplication.translate(
            "EdsWarnings", "Field %1 of [DeviceInfo] is empty: read as 0"
        ).replace("%1", listed)
    if warning.code == EdsWarningCode.MISSING_MANDATORY:
        return QCoreApplication.translate(
            "EdsWarnings", "Mandatory CiA 301 objects missing: %1"
        ).replace("%1", listed)
    if warning.code == EdsWarningCode.MISSING_DEFAULTS:
        return (
            QCoreApplication.translate("EdsWarnings", "%1 objects without a default value (%2)")
            .replace("%1", str(len(warning.objects)))
            .replace("%2", listed)
        )
    if warning.code == EdsWarningCode.EMPTY_PRODUCT_NAME:
        return QCoreApplication.translate("EdsWarnings", "The product name is empty")
    return QCoreApplication.translate("EdsWarnings", "CANopen library: %1").replace(
        "%1", warning.text
    )


def show_eds_warnings(parent: QWidget | None, profile: NodeProfile) -> None:
    """List the warnings of the EDS of ``profile``; the technical text is in the details."""
    name = profile.eds_path.name if profile.eds_path else "-"
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Information)
    box.setWindowTitle(QCoreApplication.translate("EdsWarnings", "EDS warnings"))
    box.setText(
        QCoreApplication.translate(
            "EdsWarnings", "%1 loaded, with these warnings. The application works anyway."
        ).replace("%1", name)
    )
    box.setInformativeText("\n".join(f"• {warning_text(w)}" for w in profile.warnings))
    box.setDetailedText("\n".join(w.text for w in profile.warnings))
    box.exec()
