import sys
import logging
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QSharedMemory, Qt
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from ui.windows.main_window import MainWindow
from core.config.config_manager import ConfigManager

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

class SingleApplication(QApplication):
    def __init__(self, argv):
        super().__init__(argv)
        
        self.shared_memory = QSharedMemory('GOSyncApplication')
        
        # Try to create shared memory
        if self.shared_memory.create(1):
            # First instance - set up server
            self.is_first = True
            self.server = QLocalServer()
            self.server.listen('GOSyncServer')
            self.server.newConnection.connect(self.handle_connection)
        else:
            # Second instance - connect to first
            self.is_first = False
            socket = QLocalSocket()
            socket.connectToServer('GOSyncServer')
            if socket.waitForConnected(500):
                socket.write(b'show')
                socket.waitForBytesWritten()
            sys.exit(0)  # Exit second instance
    
    def handle_connection(self):
        """Handle connection from second instance"""
        socket = self.server.nextPendingConnection()
        if socket.waitForReadyRead(500):
            # Show and raise main window
            if hasattr(self, 'main_window'):
                self.main_window.show()
                self.main_window.raise_()
                self.main_window.activateWindow()

def main():
    # Create application
    app = SingleApplication(sys.argv)
    
    if not app.is_first:
        return
    
    # Create config manager
    config = ConfigManager()
    
    # Create main window
    main_window = MainWindow(config)
    app.main_window = main_window  # Store reference for handle_connection
    main_window.show()
    
    # Start application
    return app.exec()

if __name__ == '__main__':
    sys.exit(main()) 