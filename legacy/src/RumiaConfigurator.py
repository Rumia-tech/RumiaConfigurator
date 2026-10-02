"""
RumiaConfigurator - CAN Interface Application
Entry point for the application.
"""

from gui import CanInterfaceApp

def main():
    """Launch the RumiaConfigurator GUI application."""
    app = CanInterfaceApp()
    app.mainloop()


if __name__ == "__main__":
    main()