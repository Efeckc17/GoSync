from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel,
    QLineEdit, QPushButton, QTextEdit, QFileDialog
)
from PySide6.QtCore import Qt, QFile

class SettingsDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.config = config
        self.setup_ui()
        self.load_stylesheet()
        self.load_settings()
    
    def setup_ui(self):
        self.setWindowTitle("GOSync Settings")
        layout = QVBoxLayout(self)
        
        # Local Path
        local_path_layout = QHBoxLayout()
        local_path_label = QLabel("Local Folder")
        self.local_path_input = QLineEdit()
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.browse_local_path)
        local_path_layout.addWidget(local_path_label)
        local_path_layout.addWidget(self.local_path_input)
        local_path_layout.addWidget(browse_button)
        layout.addLayout(local_path_layout)
        
        # Hostname
        hostname_layout = QHBoxLayout()
        hostname_label = QLabel("Hostname")
        self.hostname_input = QLineEdit()
        hostname_layout.addWidget(hostname_label)
        hostname_layout.addWidget(self.hostname_input)
        layout.addLayout(hostname_layout)
        
        # Username
        username_layout = QHBoxLayout()
        username_label = QLabel("Username")
        self.username_input = QLineEdit()
        username_layout.addWidget(username_label)
        username_layout.addWidget(self.username_input)
        layout.addLayout(username_layout)
        
        # Remote Path
        remote_path_layout = QHBoxLayout()
        remote_path_label = QLabel("Remote Path")
        self.remote_path_input = QLineEdit()
        remote_path_layout.addWidget(remote_path_label)
        remote_path_layout.addWidget(self.remote_path_input)
        layout.addLayout(remote_path_layout)
        
        # SSH Private Key
        ssh_key_label = QLabel("SSH Private Key")
        self.ssh_key_input = QTextEdit()
        self.ssh_key_input.setPlaceholderText("Paste your SSH private key here (must start with -----BEGIN ... PRIVATE KEY-----)")
        layout.addWidget(ssh_key_label)
        layout.addWidget(self.ssh_key_input)
        
        # SSH Password (optional)
        password_layout = QHBoxLayout()
        password_label = QLabel("SSH Password (leave blank to use private key)")
        self.password_input = QLineEdit()
        self.password_input.setEchoMode(QLineEdit.Password)
        password_layout.addWidget(password_label)
        password_layout.addWidget(self.password_input)
        layout.addLayout(password_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        save_button = QPushButton("Save")
        save_button.clicked.connect(self.save_settings)
        cancel_button = QPushButton("Cancel")
        cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(save_button)
        button_layout.addWidget(cancel_button)
        layout.addLayout(button_layout)
        
        # Set dialog properties
        self.setMinimumWidth(500)
        self.setStyleSheet("""
            QDialog {
                background-color: #1a1a1a;
            }
            QLabel {
                color: #FFFFFF;
            }
            QLineEdit, QTextEdit {
                background-color: #2d2d2d;
                color: #FFFFFF;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                padding: 4px;
            }
            QPushButton {
                background-color: #2d2d2d;
                color: #FFFFFF;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QPushButton:hover {
                background-color: #3d3d3d;
            }
        """)
    
    def browse_local_path(self):
        """Open folder selection dialog"""
        folder = QFileDialog.getExistingDirectory(
            self,
            "Select Local Sync Folder",
            self.local_path_input.text()
        )
        if folder:
            self.local_path_input.setText(folder)
    
    def load_settings(self):
        """Load current settings"""
        ssh_settings = self.config.get_ssh_settings()
        sync_settings = self.config.get_sync_settings()
        
        self.local_path_input.setText(sync_settings.get('local_path', ''))
        self.hostname_input.setText(ssh_settings.get('hostname', ''))
        self.username_input.setText(ssh_settings.get('username', ''))
        self.remote_path_input.setText(ssh_settings.get('remote_path', ''))
        self.ssh_key_input.setText(ssh_settings.get('ssh_key', ''))
        self.password_input.setText(ssh_settings.get('password', ''))
    
    def save_settings(self):
        """Save settings"""
        ssh_settings = {
            'hostname': self.hostname_input.text(),
            'username': self.username_input.text(),
            'remote_path': self.remote_path_input.text(),
            'ssh_key': self.ssh_key_input.toPlainText(),
            'password': self.password_input.text()
        }
        
        sync_settings = {
            'local_path': self.local_path_input.text(),
            'auto_sync': True,  # Default to auto-sync enabled
            'sync_interval': 300  # 5 minutes default
        }
        
        self.config.save_ssh_settings(ssh_settings)
        self.config.save_sync_settings(sync_settings)
        self.accept()

    def load_stylesheet(self):
        """Load the application stylesheet"""
        qss_path = "themes/ui.qss"
        qss_file = QFile(qss_path)
        if qss_file.open(QFile.ReadOnly | QFile.Text):
            stylesheet = qss_file.readAll().data().decode()
            self.setStyleSheet(stylesheet)
            qss_file.close()
        else:
            print(f"Failed to load stylesheet from {qss_path}") 