import paramiko
import logging
from pathlib import Path
import io
from PySide6.QtCore import QThread, Signal, QObject
from scp import SCPClient

logger = logging.getLogger('GOSync')

class SSHWorker(QThread):
    connected = Signal(bool, str)  # Success, Message
    operation_complete = Signal(bool, str)  # Success, Message
    operation_progress = Signal(str)  # Progress message
    file_list_ready = Signal(list)  # List of remote files

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.client = None
        self.sftp = None
        self.operation = None
        self.params = None
        self._reconnect_attempts = 3
    
    def ensure_connected(self):
        """Ensure SSH connection is active, reconnect if needed"""
        try:
            if self.is_connected():
                return True
            
            for attempt in range(self._reconnect_attempts):
                try:
                    self._connect()
                    return True
                except Exception as e:
                    logger.warning(f"Connection attempt {attempt + 1} failed: {str(e)}")
                    if self.client:
                        self.client.close()
                    if self.sftp:
                        self.sftp.close()
                    self.client = None
                    self.sftp = None
            
            raise Exception("Failed to establish SSH connection after multiple attempts")
            
        except Exception as e:
            logger.error(f"Connection failed: {str(e)}")
            self.connected.emit(False, str(e))
            return False

    def _connect(self):
        """Establish SSH connection"""
        try:
            ssh_settings = self.config.get_ssh_settings()
            
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            # Prepare authentication
            if ssh_settings['ssh_key']:
                key_file = io.StringIO(ssh_settings['ssh_key'])
                private_key = paramiko.RSAKey.from_private_key(key_file)
                auth = {'pkey': private_key}
            else:
                auth = {'password': ssh_settings['password']}
            
            # Connect to remote host
            self.operation_progress.emit(f"Connecting to {ssh_settings['hostname']}...")
            self.client.connect(
                hostname=ssh_settings['hostname'],
                username=ssh_settings['username'],
                **auth
            )
            
            # Open SFTP session
            self.sftp = self.client.open_sftp()
            
            # Ensure base remote path exists
            self._ensure_base_path()
            
            logger.info(f"Connected to {ssh_settings['hostname']}")
            self.connected.emit(True, f"Connected to {ssh_settings['hostname']}")
            
        except Exception as e:
            self.disconnect()
            raise Exception(f"SSH connection failed: {str(e)}")

    def _ensure_base_path(self):
        """Ensure base remote path exists"""
        try:
            ssh_settings = self.config.get_ssh_settings()
            remote_path = ssh_settings['remote_path']
            
            # Split path into components
            parts = remote_path.replace('\\', '/').strip('/').split('/')
            current = ''
            
            # Create each directory level if needed
            for part in parts:
                current = current + '/' + part if current else '/' + part
                try:
                    self.sftp.stat(current)
                except FileNotFoundError:
                    try:
                        self.sftp.mkdir(current)
                        logger.info(f"Created remote directory: {current}")
                    except Exception as e:
                        logger.error(f"Failed to create remote directory {current}: {str(e)}")
                        raise
                        
        except Exception as e:
            logger.error(f"Failed to ensure base path: {str(e)}")
            raise

    def _list_remote_files(self):
        """List remote files"""
        try:
            if not self.ensure_connected():
                return
            
            ssh_settings = self.config.get_ssh_settings()
            remote_path = ssh_settings['remote_path'].replace('\\', '/')
            
            try:
                self.sftp.stat(remote_path)
            except FileNotFoundError:
                self._ensure_base_path()
            
            files = []
            self._list_remote_files_recursive(remote_path, '', files)
            self.file_list_ready.emit(files)
            self.operation_complete.emit(True, "File list retrieved successfully")
            
        except Exception as e:
            logger.error(f"Failed to list remote files: {str(e)}")
            self.operation_complete.emit(False, f"Failed to list files: {str(e)}")

    def _upload_file(self):
        """Upload file to remote server"""
        try:
            if not self.ensure_connected():
                return
            
            local_file = self.params['local_file']
            remote_file = self.params['remote_file']
            
            ssh_settings = self.config.get_ssh_settings()
            remote_path = Path(ssh_settings['remote_path'].replace('\\', '/')) / remote_file
            
            # Create remote directories if needed
            remote_dir = str(remote_path.parent).replace('\\', '/')
            try:
                self.sftp.stat(remote_dir)
            except FileNotFoundError:
                self._create_remote_dirs(remote_dir)
            
            # Upload file
            self.operation_progress.emit(f"Uploading {local_file}...")
            self.sftp.put(str(local_file), str(remote_path).replace('\\', '/'))
            
            logger.info(f"Uploaded {local_file} to {remote_path}")
            self.operation_complete.emit(True, f"Uploaded {local_file}")
            
        except Exception as e:
            logger.error(f"Failed to upload {self.params['local_file']}: {str(e)}")
            self.operation_complete.emit(False, f"Upload failed: {str(e)}")

    def _create_remote_dirs(self, path):
        """Create remote directory hierarchy"""
        path = path.replace('\\', '/').strip('/')
        current = ''
        
        for part in path.split('/'):
            current = current + '/' + part if current else '/' + part
            try:
                self.sftp.stat(current)
            except FileNotFoundError:
                try:
                    self.sftp.mkdir(current)
                    logger.info(f"Created remote directory: {current}")
                except Exception as e:
                    if "Socket is closed" in str(e):
                        if self.ensure_connected():
                            self.sftp.mkdir(current)
                            logger.info(f"Created remote directory after reconnection: {current}")
                        else:
                            raise
                    else:
                        raise

    def _download_file(self):
        """Download file from remote server"""
        try:
            if not self.ensure_connected():
                return
            
            remote_file = self.params['remote_file']
            local_file = self.params['local_file']
            
            ssh_settings = self.config.get_ssh_settings()
            remote_path = Path(ssh_settings['remote_path'].replace('\\', '/')) / remote_file
            
            # Create local directories if needed
            local_file.parent.mkdir(parents=True, exist_ok=True)
            
            # Download file
            self.operation_progress.emit(f"Downloading {remote_file}...")
            self.sftp.get(str(remote_path).replace('\\', '/'), str(local_file))
            
            logger.info(f"Downloaded {remote_path} to {local_file}")
            self.operation_complete.emit(True, f"Downloaded {remote_file}")
            
        except Exception as e:
            logger.error(f"Failed to download {self.params['remote_file']}: {str(e)}")
            self.operation_complete.emit(False, f"Download failed: {str(e)}")
    
    def disconnect(self):
        """Close SSH connection"""
        if self.sftp:
            self.sftp.close()
            self.sftp = None
        
        if self.client:
            self.client.close()
            self.client = None
        
        logger.info("Disconnected from SSH")
    
    def is_connected(self):
        """Check if SSH connection is active"""
        if not self.client or not self.sftp:
            return False
        
        try:
            self.client.get_transport().is_active()
            return True
        except:
            return False
    
    def _list_remote_files_recursive(self, remote_path, relative_path, files):
        """Recursively list files in remote directory"""
        try:
            for entry in self.sftp.listdir_attr(str(Path(remote_path) / relative_path)):
                full_path = str(Path(relative_path) / entry.filename)
                
                if self._is_file(entry):
                    files.append(full_path)
                elif self._is_dir(entry):
                    self._list_remote_files_recursive(remote_path, full_path, files)
                    
        except Exception as e:
            logger.error(f"Failed to list directory {relative_path}: {str(e)}")
    
    def _is_file(self, entry):
        """Check if SFTP entry is a regular file"""
        return entry.st_mode & 0o170000 == 0o100000
    
    def _is_dir(self, entry):
        """Check if SFTP entry is a directory"""
        return entry.st_mode & 0o170000 == 0o040000

    def run(self):
        """Execute the requested SSH operation"""
        try:
            if self.operation == 'connect':
                self._connect()
            elif self.operation == 'list_files':
                self._list_remote_files()
            elif self.operation == 'upload':
                self._upload_file()
            elif self.operation == 'download':
                self._download_file()
        except Exception as e:
            logger.error(f"SSH operation failed: {str(e)}")
            self.operation_complete.emit(False, str(e))

class SSHClient(QObject):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.client = None
        self._setup_client()
        self.worker = None
    
    def _setup_client(self):
        """Initialize SSH client with default settings"""
        self.client = paramiko.SSHClient()
        self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    
    def connect(self):
        """Connect to remote server using either password or key-based auth"""
        if not self.client:
            self._setup_client()
            
        try:
            ssh_settings = self.config.get_ssh_settings()
            
            if ssh_settings.get('password'):
                # Password authentication
                self.client.connect(
                    hostname=ssh_settings['hostname'],
                    username=ssh_settings['username'],
                    password=ssh_settings['password'],
                    look_for_keys=False,
                    allow_agent=False
                )
            else:
                # Key-based authentication
                self.client.connect(
                    hostname=ssh_settings['hostname'],
                    username=ssh_settings['username'],
                    key_filename=ssh_settings['key_path'],
                    look_for_keys=False,
                    allow_agent=False
                )
            logger.info("SSH connection established successfully")
        except Exception as e:
            logger.error(f"SSH connection failed: {str(e)}")
            raise
    
    def disconnect(self):
        """Close SSH connection"""
        if self.client:
            self.client.close()
            self.client = None
        
        if self.worker:
            self.worker.disconnect()
            self.worker = None
    
    def is_connected(self):
        """Check if SSH connection is active"""
        return (self.client and 
                self.client.get_transport() and 
                self.client.get_transport().is_active())
    
    def list_remote_files(self):
        """Get list of files in remote directory"""
        try:
            if not self.is_connected():
                self.connect()
                
            ssh_settings = self.config.get_ssh_settings()
            remote_path = ssh_settings.get('remote_path', '')
            
            if not remote_path:
                raise ValueError("Remote path not configured")
            
            stdin, stdout, stderr = self.client.exec_command(
                f'find "{remote_path}" -type f -printf "%P\\n"'
            )
            return [line.strip() for line in stdout if line.strip()]
        except Exception as e:
            logger.error(f"Failed to list remote files: {str(e)}")
            raise
    
    def upload_file(self, local_path, remote_path):
        """Upload a file using SCP"""
        try:
            if not self.is_connected():
                self.connect()
                
            ssh_settings = self.config.get_ssh_settings()
            base_remote_path = ssh_settings.get('remote_path', '')
            
            if not base_remote_path:
                raise ValueError("Remote path not configured")
                
            full_remote_path = str(Path(base_remote_path) / remote_path)
            remote_dir = str(Path(full_remote_path).parent)
            
            self.client.exec_command(f'mkdir -p "{remote_dir}"')
            
            with SCPClient(self.client.get_transport()) as scp:
                scp.put(str(local_path), full_remote_path)
            logger.info(f"File uploaded successfully: {full_remote_path}")
        except Exception as e:
            logger.error(f"File upload failed: {str(e)}")
            raise
    
    def download_file(self, remote_path, local_path):
        """Download a file using SCP"""
        try:
            if not self.is_connected():
                self.connect()
                
            ssh_settings = self.config.get_ssh_settings()
            base_remote_path = ssh_settings.get('remote_path', '')
            
            if not base_remote_path:
                raise ValueError("Remote path not configured")
                
            full_remote_path = str(Path(base_remote_path) / remote_path)
            local_dir = Path(local_path).parent
            local_dir.mkdir(parents=True, exist_ok=True)
            
            with SCPClient(self.client.get_transport()) as scp:
                scp.get(full_remote_path, str(local_path))
            logger.info(f"File downloaded successfully: {local_path}")
        except Exception as e:
            logger.error(f"File download failed: {str(e)}")
            raise
    
    def get_remote_mtime(self, remote_path):
        """Get modification time of remote file"""
        try:
            if not self.is_connected():
                self.connect()
                
            ssh_settings = self.config.get_ssh_settings()
            base_remote_path = ssh_settings.get('remote_path', '')
            
            if not base_remote_path:
                raise ValueError("Remote path not configured")
                
            full_remote_path = str(Path(base_remote_path) / remote_path)
            
            stdin, stdout, stderr = self.client.exec_command(
                f'stat -c %Y "{full_remote_path}"'
            )
            mtime = stdout.read().decode().strip()
            return float(mtime) if mtime else 0
        except Exception as e:
            logger.error(f"Failed to get remote mtime: {str(e)}")
            return 0

    def start_worker(self):
        """Start the SSH worker"""
        if not self.worker:
            self.worker = SSHWorker(self.config)
        
        self.worker.operation = 'connect'
        self.worker.start()
    
    def wait_for_completion(self):
        """Wait for the SSH worker to complete"""
        if self.worker:
            self.worker.wait()
    
    def get_file_list(self):
        """Get the list of remote files"""
        if not self.worker:
            self.worker = SSHWorker(self.config)
        
        self.worker.operation = 'list_files'
        self.worker.start()
        self.worker.wait()  # Wait for completion since we need the result
        return []  # Return empty list, actual results will come through signal
    
    def start_upload(self, local_file, remote_file):
        """Start the upload worker"""
        if not self.worker:
            self.worker = SSHWorker(self.config)
        
        self.worker.operation = 'upload'
        self.worker.params = {
            'local_file': local_file,
            'remote_file': remote_file
        }
        self.worker.start()
    
    def start_download(self, remote_file, local_file):
        """Start the download worker"""
        if not self.worker:
            self.worker = SSHWorker(self.config)
        
        self.worker.operation = 'download'
        self.worker.params = {
            'remote_file': remote_file,
            'local_file': local_file
        }
        self.worker.start()
    
    def get_remote_mtime(self, remote_file):
        """Get remote file modification time"""
        if not self.is_connected():
            return 0
        
        try:
            ssh_settings = self.config.get_ssh_settings()
            remote_path = Path(ssh_settings['remote_path']) / remote_file
            stat = self.client.exec_command(f'stat -c %Y "{remote_path}"')[1].read().decode().strip()
            return float(stat) if stat else 0
        except Exception as e:
            logger.error(f"Failed to get mtime for {remote_file}: {str(e)}")
            return 0 