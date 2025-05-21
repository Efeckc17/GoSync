from PySide6.QtWidgets import QSystemTrayIcon, QMenu
from PySide6.QtGui import QIcon
from PySide6.QtCore import Signal
import os
import sys

def get_resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
    try:
       
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class SystemTrayIcon(QSystemTrayIcon):
    quit_requested = Signal()
    sync_requested = Signal()
    settings_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        icon_path = get_resource_path("assets/icons/app.ico")
        self.setIcon(QIcon(icon_path))
        self.setToolTip("GOSync - File Synchronization")
        self.setup_menu()
        self.activated.connect(self._on_activated)
        self.show()

    def setup_menu(self):
        """Setup tray icon context menu"""
        menu = QMenu()

        # Show action
        show_action = menu.addAction("Show")
        show_action.triggered.connect(self.parent().show)

        # Sync action
        sync_action = menu.addAction("Sync Now")
        sync_action.triggered.connect(self.sync_requested.emit)

        # Settings action
        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.settings_requested.emit)

        menu.addSeparator()

        # Quit action
        quit_action = menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_requested.emit)

        self.setContextMenu(menu)

    def _on_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.parent().show()
            self.parent().raise_()
            self.parent().activateWindow()

    def show_message(self, title, message):
        """Show tray notification"""
        self.showMessage(
            title,
            message,
            QSystemTrayIcon.MessageIcon.Information,
            2000
        ) 