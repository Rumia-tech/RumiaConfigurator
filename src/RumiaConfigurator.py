"""
RumiaConfigurator - CAN Interface Application
Entry point for the application.
"""

#test commit on main

# Import python-can if available
try:
    import can
except Exception:
    can = None


def main():
    """Launch the RumiaConfigurator GUI application."""
    app = CanInterfaceApp()
    app.mainloop()


if __name__ == "__main__":
    main()