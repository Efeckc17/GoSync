from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QFileDialog, QStatusBar,
    QMenu, QMessageBox, QProgressBar, QApplication
)
from PySide6.QtCore import Qt, QFile
from PySide6.QtGui import QIcon
from ui.widgets.file_list_widget import FileListWidget
from ui.widgets.settings_dialog import SettingsDialog
from ui.widgets.tray_icon import SystemTrayIcon
from core.sync.sync_manager import SyncManager
from core.ssh.file_transfer import FileTransferManager
import logging
import os
from pathlib import Path

logger = logging.getLogger(__name__)

class MainWindow(QMainWindow):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.sync_manager = SyncManager(config)
        self.file_transfer = None  # Will be initialized when needed
        
        self.setWindowTitle("GOSync")
        self.load_stylesheet()
        self.setup_ui()
        self.setup_signals()
        self.setup_tray()
        
        # Auto-start sync if settings exist
        self.check_and_start_sync()
    
    def load_stylesheet(self):
        """Load the application stylesheet"""
        qss_file = QFile("themes/ui.qss")
        if qss_file.open(QFile.ReadOnly | QFile.Text):
            stylesheet = qss_file.readAll().data().decode()
            self.setStyleSheet(stylesheet)
            qss_file.close()
    
    def check_and_start_sync(self):
        """Check if settings exist and start sync automatically"""
        ssh_settings = self.config.get_ssh_settings()
        if (ssh_settings.get('hostname') and 
            ssh_settings.get('username') and 
            ssh_settings.get('remote_path') and 
            (ssh_settings.get('ssh_key') or ssh_settings.get('password'))):
            
            logger.info("Found existing settings, starting sync automatically")
            self.start_sync()
    
    def setup_ui(self):
        # Create central widget and main layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Create header
        header_layout = QHBoxLayout()
        title_label = QLabel("GOSync")
        title_label.setObjectName("titleLabel")
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        main_layout.addLayout(header_layout)
        
        # Create file lists container
        lists_layout = QHBoxLayout()
        lists_layout.setSpacing(20)
        
        # Local files
        local_container = QWidget()
        local_layout = QVBoxLayout(local_container)
        local_header = QHBoxLayout()
        local_label = QLabel("Local Files")
        local_label.setObjectName("sectionLabel")
        local_header.addWidget(local_label)
        local_header.addStretch()
        
        self.local_files = FileListWidget()
        self.local_files.setContextMenuPolicy(Qt.CustomContextMenu)
        self.local_files.customContextMenuRequested.connect(self.show_local_context_menu)
        
        local_layout.addLayout(local_header)
        local_layout.addWidget(self.local_files)
        lists_layout.addWidget(local_container)
        
        # Remote files
        remote_container = QWidget()
        remote_layout = QVBoxLayout(remote_container)
        remote_header = QHBoxLayout()
        remote_label = QLabel("Remote Files")
        remote_label.setObjectName("sectionLabel")
        remote_header.addWidget(remote_label)
        remote_header.addStretch()
        
        self.remote_files = FileListWidget()
        self.remote_files.setContextMenuPolicy(Qt.CustomContextMenu)
        self.remote_files.customContextMenuRequested.connect(self.show_remote_context_menu)
        
        remote_layout.addLayout(remote_header)
        remote_layout.addWidget(self.remote_files)
        lists_layout.addWidget(remote_container)
        
        main_layout.addLayout(lists_layout)
        
        # Create bottom buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(10)
        
        self.sync_button = QPushButton("Sync Now")
        self.sync_button.clicked.connect(self.sync_files)
        
        self.start_sync_button = QPushButton("Start Sync")
        self.start_sync_button.clicked.connect(self.start_sync)
        
        self.stop_sync_button = QPushButton("Stop Sync")
        self.stop_sync_button.clicked.connect(self.stop_sync)
        self.stop_sync_button.setObjectName("dangerButton")
        self.stop_sync_button.setEnabled(False)
        
        self.settings_button = QPushButton("Settings")
        self.settings_button.clicked.connect(self.show_settings)
        
        button_layout.addWidget(self.sync_button)
        button_layout.addWidget(self.start_sync_button)
        button_layout.addWidget(self.stop_sync_button)
        button_layout.addStretch()
        button_layout.addWidget(self.settings_button)
        
        main_layout.addLayout(button_layout)
        
        # Create status bar
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Add progress bar to status bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setFixedWidth(200)
        self.progress_bar.setVisible(False)
        self.status_bar.addPermanentWidget(self.progress_bar)
        
        # Set window properties
        self.setMinimumSize(1000, 700)
    
    def setup_signals(self):
        """Connect signals from sync manager"""
        if self.sync_manager.sync_worker:
            self.sync_manager.sync_worker.sync_complete.connect(self.on_sync_complete)
            self.sync_manager.sync_worker.sync_progress.connect(self.on_sync_progress)
            self.sync_manager.sync_worker.files_updated.connect(self.on_files_updated)
            
            if self.sync_manager.sync_worker.ssh_client and self.sync_manager.sync_worker.ssh_client.worker:
                worker = self.sync_manager.sync_worker.ssh_client.worker
                worker.connected.connect(self.on_ssh_connected)
                worker.operation_complete.connect(self.on_operation_complete)
                worker.operation_progress.connect(self.on_operation_progress)
                worker.file_list_ready.connect(self.on_remote_files_updated)
    
    def sync_files(self):
        """Start manual sync"""
        self.sync_button.setEnabled(False)
        self.start_sync_button.setEnabled(False)
        self.stop_sync_button.setEnabled(False)
        self.settings_button.setEnabled(False)
        self.status_bar.showMessage("Starting synchronization...")
        self.sync_manager.sync_now()
    
    def start_sync(self):
        """Start automatic sync"""
        self.sync_button.setEnabled(False)
        self.start_sync_button.setEnabled(False)
        self.stop_sync_button.setEnabled(True)
        self.settings_button.setEnabled(True)
        self.status_bar.showMessage("Starting automatic synchronization...")
        self.sync_manager.start_sync()
        self.setup_signals()
    
    def stop_sync(self):
        """Stop automatic sync"""
        self.sync_manager.stop_sync()
        self.sync_button.setEnabled(True)
        self.start_sync_button.setEnabled(True)
        self.stop_sync_button.setEnabled(False)
        self.settings_button.setEnabled(True)
        self.status_bar.showMessage("Synchronization stopped")
    
    def show_settings(self):
        """Show settings dialog"""
        dialog = SettingsDialog(self.config, self)
        if dialog.exec():
            self.status_bar.showMessage("Settings saved")
            # Auto-start sync if it wasn't running
            if not self.stop_sync_button.isEnabled():
                self.check_and_start_sync()
    
    def on_sync_complete(self, success, message):
        """Handle sync completion"""
        self.sync_button.setEnabled(True)
        self.start_sync_button.setEnabled(True)
        self.settings_button.setEnabled(True)
        self.status_bar.showMessage(message)
    
    def on_sync_progress(self, message):
        """Handle sync progress update"""
        self.status_bar.showMessage(message)
    
    def on_files_updated(self, local_files, remote_files):
        """Update file lists"""
        self.local_files.update_files(local_files)
        self.remote_files.update_files(remote_files)
    
    def on_ssh_connected(self, success, message):
        """Handle SSH connection status"""
        if not success:
            self.stop_sync()
        self.status_bar.showMessage(message)
    
    def on_operation_complete(self, success, message):
        """Handle SSH operation completion"""
        if not success:
            self.status_bar.showMessage(f"Error: {message}", 5000)
        else:
            self.status_bar.showMessage(message, 3000)
    
    def on_operation_progress(self, message):
        """Handle SSH operation progress"""
        self.status_bar.showMessage(message)
    
    def on_remote_files_updated(self, files):
        """Update remote files list"""
        self.remote_files.update_files(files)
    
    def show_local_context_menu(self, position):
        """Show context menu for local files"""
        menu = QMenu()
        upload_action = menu.addAction("Upload to Server")
        delete_action = menu.addAction("Delete")
        
        action = menu.exec_(self.local_files.mapToGlobal(position))
        if action == upload_action:
            self.upload_selected_files()
        elif action == delete_action:
            self.delete_local_files()
    
    def show_remote_context_menu(self, position):
        """Show context menu for remote files"""
        selected_items = self.remote_files.selectedItems()
        if not selected_items:
            return
            
        menu = QMenu()
        download_action = menu.addAction("Download to Local")
        refresh_action = menu.addAction("Refresh File List")
        
        action = menu.exec_(self.remote_files.mapToGlobal(position))
        if action == download_action:
            self.download_selected_files()
        elif action == refresh_action:
            self.sync_manager.sync_now()  # Refresh the file list
    
    def download_selected_files(self):
        """Download selected files from remote server"""
        selected_items = self.remote_files.selectedItems()
        if not selected_items:
            return
        
        # Initialize file transfer manager if needed
        if not self.file_transfer:
            self.file_transfer = FileTransferManager(self.sync_manager.sync_worker.ssh_client)
            self.file_transfer.transfer_progress.connect(self.on_transfer_progress)
            self.file_transfer.transfer_complete.connect(self.on_transfer_complete)
        
        sync_settings = self.config.get_sync_settings()
        local_path = Path(sync_settings['local_path'])
        
        # Get remote base path
        ssh_settings = self.config.get_ssh_settings()
        remote_base = Path(ssh_settings['remote_path'])
        
        for item in selected_items:
            try:
                remote_file = item.text()
                local_file = local_path / remote_file
                
                # Construct full remote path
                full_remote_path = str(remote_base / remote_file).replace('\\', '/')
                logger.info(f"Attempting to download: {full_remote_path}")
                
                # Start download
                self.progress_bar.setVisible(True)
                self.progress_bar.setRange(0, 0)  # Indeterminate progress
                self.file_transfer.download_file(full_remote_path, local_file)
                
            except Exception as e:
                logger.error(f"Error downloading {remote_file}: {str(e)}")
                QMessageBox.warning(
                    self,
                    "Download Error",
                    f"Failed to download '{remote_file}': {str(e)}",
                    QMessageBox.Ok
                )
    
    def upload_selected_files(self):
        """Upload selected files to server"""
        selected_items = self.local_files.selectedItems()
        if not selected_items:
            return
        
        # Initialize file transfer manager if needed
        if not self.file_transfer:
            self.file_transfer = FileTransferManager(self.sync_manager.sync_worker.ssh_client)
            self.file_transfer.transfer_progress.connect(self.on_transfer_progress)
            self.file_transfer.transfer_complete.connect(self.on_transfer_complete)
        
        sync_settings = self.config.get_sync_settings()
        local_path = Path(sync_settings['local_path'])
        ssh_settings = self.config.get_ssh_settings()
        remote_base = ssh_settings['remote_path']
        
        for item in selected_items:
            local_file = local_path / item.text()
            remote_file = os.path.join(remote_base, item.text()).replace('\\', '/')
            
            # Start upload
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # Indeterminate progress
            self.file_transfer.upload_file(local_file, remote_file)
    
    def on_transfer_progress(self, message):
        """Handle file transfer progress"""
        self.status_bar.showMessage(message)
    
    def on_transfer_complete(self, success, message):
        """Handle file transfer completion"""
        self.progress_bar.setVisible(False)
        self.status_bar.showMessage(message, 5000 if success else 10000)
        
        if success:
            # Refresh file lists
            self.sync_manager.sync_now()
    
    def delete_local_files(self):
        """Delete selected local files"""
        selected_items = self.local_files.selectedItems()
        if not selected_items:
            return
            
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete {len(selected_items)} file(s)?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            sync_settings = self.config.get_sync_settings()
            local_path = sync_settings['local_path']
            
            for item in selected_items:
                file_path = os.path.join(local_path, item.text())
                try:
                    os.remove(file_path)
                    logger.info(f"Deleted local file: {file_path}")
                except Exception as e:
                    logger.error(f"Failed to delete {file_path}: {str(e)}")
    
    def setup_tray(self):
        """Setup system tray icon"""
        self.tray_icon = SystemTrayIcon(self)
        self.tray_icon.sync_requested.connect(self.sync_files)
        self.tray_icon.settings_requested.connect(self.show_settings)
        self.tray_icon.quit_requested.connect(self.quit_application)
    
    def closeEvent(self, event):
        """Handle window close event"""
        if self.tray_icon.isVisible():
            self.hide()
            self.tray_icon.show_message(
                "GOSync",
                "Application is still running in the background."
            )
            event.ignore()
        else:
            self.quit_application()
    
    def quit_application(self):
        """Quit the application properly"""
        self.sync_manager.stop_sync()
        self.tray_icon.hide()
        self.close()
        QApplication.quit() 