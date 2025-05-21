import logging
from pathlib import Path
from PySide6.QtCore import QObject, Signal
from scp import SCPClient
import unicodedata
import re

logger = logging.getLogger('GOSync')

class FileTransferManager(QObject):
    transfer_progress = Signal(str)  # Progress message
    transfer_complete = Signal(bool, str)  # Success, Message
    
    def __init__(self, ssh_client):
        super().__init__()
        self.ssh_client = ssh_client
        self.sftp = None
    
    def ensure_sftp(self):
        """Ensure SFTP connection is active"""
        try:
            if not self.sftp or not self.ssh_client.is_connected():
                if not self.ssh_client.is_connected():
                    self.ssh_client.connect()
                self.sftp = self.ssh_client.client.open_sftp()
            return True
        except Exception as e:
            logger.error(f"Failed to establish SFTP connection: {str(e)}")
            return False

    def sanitize_filename(self, filename):
        """Sanitize filename to handle special characters"""
        # Normalize Unicode characters
        filename = unicodedata.normalize('NFKC', filename)
        # Replace problematic characters with safe alternatives
        filename = re.sub(r'[\\/:*?"<>|｜]', '_', filename)
        return filename
    
    def download_file(self, remote_file, local_path):
        """Download a single file from remote server"""
        try:
            if not self.ensure_sftp():
                error_msg = "Failed to establish SFTP connection"
                logger.error(error_msg)
                self.transfer_complete.emit(False, error_msg)
                return
            
            # Create local directory if it doesn't exist
            local_path = Path(local_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            self.transfer_progress.emit(f"Downloading {remote_file}...")
            
            # Use existing SFTP connection
            try:
                self.sftp.get(remote_file, str(local_path))
                logger.info(f"Downloaded {remote_file} to {local_path}")
                self.transfer_complete.emit(True, f"Downloaded {remote_file} successfully")
            except FileNotFoundError:
                error_msg = f"File does not exist on the remote server: {remote_file}"
                logger.error(error_msg)
                self.transfer_complete.emit(False, error_msg)
            except Exception as e:
                error_msg = f"Failed to download {remote_file}: {str(e)}"
                logger.error(error_msg)
                self.transfer_complete.emit(False, error_msg)
            
        except Exception as e:
            error_msg = f"Failed to download {remote_file}: {str(e)}"
            logger.error(error_msg.encode('utf-8', errors='replace').decode('utf-8'))
            self.transfer_complete.emit(False, error_msg)
    
    def upload_file(self, local_file, remote_path):
        """Upload a single file to remote server"""
        try:
            if not self.ssh_client.is_connected():
                self.transfer_progress.emit("Connecting to server...")
                self.ssh_client.connect()
            
            local_file = Path(local_file)
            if not local_file.exists():
                raise FileNotFoundError(f"Local file not found: {local_file}")
            
            # Sanitize remote path
            remote_dir = Path(remote_path).parent
            remote_name = self.sanitize_filename(Path(remote_path).name)
            remote_path = str(remote_dir / remote_name)
            
            # Create remote directory if needed
            self.ssh_client.client.exec_command(f'mkdir -p "{remote_dir}"')
            
            self.transfer_progress.emit(f"Uploading {local_file.name}...")
            
            with SCPClient(self.ssh_client.client.get_transport()) as scp:
                scp.put(str(local_file), remote_path)
            
            logger.info(f"Uploaded {local_file} to {remote_path}")
            self.transfer_complete.emit(True, f"Uploaded {local_file.name} successfully")
            
        except Exception as e:
            error_msg = f"Failed to upload {local_file}: {str(e)}"
            logger.error(error_msg.encode('utf-8', errors='replace').decode('utf-8'))
            self.transfer_complete.emit(False, error_msg)
    
    def verify_file_exists(self, remote_path):
        """Check if file exists on remote server"""
        try:
            if not self.ensure_sftp():
                return False
            
            try:
                self.sftp.stat(remote_path)
                return True
            except FileNotFoundError:
                return False
            except Exception as e:
                logger.error(f"Failed to verify remote file: {str(e)}")
                return False
            
        except Exception as e:
            logger.error(f"Failed to verify remote file: {str(e)}")
            return False
    
    def get_file_size(self, remote_path):
        """Get size of remote file"""
        try:
            if not self.ssh_client.is_connected():
                self.ssh_client.connect()
            
            cmd = f'stat -f "%z" "{remote_path}" 2>/dev/null || stat -c "%s" "{remote_path}"'
            stdin, stdout, stderr = self.ssh_client.client.exec_command(cmd)
            size = stdout.read().decode().strip()
            
            return int(size) if size.isdigit() else 0
            
        except Exception as e:
            logger.error(f"Failed to get file size: {str(e)}")
            return 0 