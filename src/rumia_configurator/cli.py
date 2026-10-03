"""Command-line entry point.

Kept free of GUI imports so that options like ``--version`` work instantly
and without a display.
"""

import argparse
import sys
from pathlib import Path

from rumia_configurator import __version__
from rumia_configurator.core import app_log, paths
from rumia_configurator.core.settings import SettingsStore

PROG = "rumia-configurator"


def build_parser() -> argparse.ArgumentParser:
    """Create the top-level argument parser."""
    parser = argparse.ArgumentParser(
        prog=PROG,
        description="Configure Rumia CANopen products and inspect any CANopen node.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"{PROG} {__version__}",
    )
    parser.add_argument(
        "--theme-demo",
        action="store_true",
        help="open a window showing the brand components in the light and dark themes",
    )
    parser.add_argument(
        "--demo",
        action="store_true",
        help="demo mode: a virtual CAN bus with a simulated Smart IMU and INCLI Sense",
    )
    commands = parser.add_subparsers(dest="command", metavar="COMMAND")
    export = commands.add_parser(
        "export-logs",
        help="save logs, settings and system information to a ZIP file",
        description="Save the application logs, settings and system information "
        "to a ZIP file to attach to a support request.",
    )
    export.add_argument(
        "-o",
        "--output",
        type=Path,
        default=None,
        help="destination ZIP file (default: a timestamped file in the current folder)",
    )
    commands.add_parser(
        "adapters",
        help="list the CAN adapters found on this computer",
        description="List the serial ports (SLCAN adapters, Rumia first) and, on Linux, "
        "the SocketCAN interfaces. PEAK, Kvaser, IXXAT and candleLight adapters are not "
        "probed: choose them in the application with Other adapter.",
    )
    return parser


def _list_adapters() -> int:
    """Print the adapters found, one per line; return the exit code."""
    from rumia_configurator.core.connection import list_adapters

    adapters = list_adapters()
    if not adapters:
        print("No adapter found. Plug the adapter in and run the command again.")
        return 0
    for adapter in adapters:
        usb = f"  USB {adapter.usb_id}" if adapter.usb_id else ""
        columns = f"{adapter.kind:<9} {adapter.backend:<9} {adapter.channel:<14}"
        print(f"{columns} {adapter.description}{usb}")
    return 0


def _setup_logging() -> None:
    """Configure the file log; if the folder is not writable, say so and go on."""
    settings = SettingsStore(paths.settings_path()).load().settings
    log_dir = paths.log_dir()
    try:
        app_log.configure_logging(log_dir, settings.log_level)
    except OSError as exc:
        print(
            f"Logging to file is disabled: the log folder {log_dir} cannot be written "
            f"({exc}). Check the permissions of that folder.",
            file=sys.stderr,
        )


def _export_logs(output: Path | None) -> int:
    """Write the log archive for the ``export-logs`` command; return the exit code."""
    dest = output if output is not None else Path.cwd() / app_log.default_export_name()
    try:
        app_log.export_logs(paths.log_dir(), paths.settings_path(), dest)
    except OSError as exc:
        print(
            f"Could not write the log archive {dest}: {exc}.\n"
            "Check that you can write to that folder, or choose another file with --output.",
            file=sys.stderr,
        )
        return 1
    print(f"Logs exported to {dest}")
    return 0


def main(argv: list[str] | None = None) -> int:
    """Run the command line interface and return the process exit code."""
    parser = build_parser()
    args = parser.parse_args(argv)
    _setup_logging()

    if args.command == "export-logs":
        return _export_logs(args.output)
    if args.command == "adapters":
        return _list_adapters()

    if args.theme_demo:
        # Imported here so that the other commands start without loading Qt.
        from rumia_configurator.gui.theme_demo import run_theme_demo

        return run_theme_demo()

    from rumia_configurator.gui.app import run_gui

    return run_gui(demo=args.demo)
