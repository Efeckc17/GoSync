import os
import logging
import tempfile
import time
from pathlib import Path
from PySide6.QtCore import QThread, Signal, QFileSystemWatcher, QObject
from core.ssh.ssh_client import SSHClient
from scp import SCPClient

logger = logging.getLogger('GOSync')

class SyncWorker(QThread):
    sync_complete = Signal(bool, str)  # Success, Message
    sync_progress = Signal(str)  # Progress message
    files_updated = Signal(list, list)  # Local files, Remote files

    def __init__(self, config):
        super().__init__()
        self.config = config
        self.ssh_client = SSHClient(config)
        self.running = False
        self.auto_sync = False
        self.sent_files = set()
        self.check_interval = 10  # 10 seconds interval
    
    def run(self):
        """Main worker thread"""
        self.running = True
        while self.running:
            try:
                self.sync_now()
                if not self.auto_sync:
                    break
                # Sleep for check_interval seconds
                self.msleep(self.check_interval * 1000)
            except Exception as e:
                logger.error(f"Sync error: {str(e)}")
                self.sync_complete.emit(False, str(e))
                if not self.auto_sync:
                    break
                # Even on error, continue checking after interval
                self.msleep(self.check_interval * 1000)
    
    def stop(self):
        """Stop the worker thread"""
        self.running = False
        self.wait()
    
    def sync_now(self):
        """Perform immediate synchronization"""
        try:
            sync_settings = self.config.get_sync_settings()
            local_path = Path(sync_settings['local_path'])
            
            self.sync_progress.emit("Connecting to SSH...")
            if not self.ssh_client.is_connected():
                self.ssh_client.connect()
            
            self.sync_progress.emit("Getting file lists...")
            local_files = self._get_local_files(local_path)
            remote_files = self.fetch_remote_filelist()
            
            self.files_updated.emit(local_files, list(remote_files))
            
            self.sync_progress.emit("Comparing files...")
            to_send = []
            for file in local_files:
                file_lower = file.lower()
                if file_lower not in remote_files:
                    self.sync_progress.emit(f"Ready to send: {file}")
                    to_send.append(file)
                else:
                    logger.debug(f"Skipping: {file} already exists on server")
            
            if to_send:
                self.sync_progress.emit(f"{len(to_send)} files will be sent: {', '.join(to_send)}")
                self.sync_progress.emit("Transferring files...")
                self._sync_files(to_send, local_path)
                self.sync_complete.emit(True, f"Sync completed successfully. Sent {len(to_send)} files.")
            else:
                logger.debug("No new files to send")
                self.sync_complete.emit(True, "No new files to sync")
            
        except Exception as e:
            logger.error(f"Sync failed: {str(e)}")
            self.sync_complete.emit(False, f"Sync failed: {str(e)}")
    
    def _get_local_files(self, path):
        """Get list of local files"""
        files = []
        for root, _, filenames in os.walk(path):
            for filename in filenames:
                full_path = Path(root) / filename
                rel_path = str(full_path.relative_to(path))
                files.append(rel_path)
        return files
    
    def fetch_remote_filelist(self):
        """Get list of remote files using temporary file approach"""
        try:
            ssh_settings = self.config.get_ssh_settings()
            remote_path = ssh_settings['remote_path']
            
            # Create temporary file on remote server
            remote_txt = os.path.join(remote_path, "filelist.txt").replace("\\", "/")
            self.ssh_client.client.exec_command(
                f'find "{remote_path}" -type f -printf "%P\\n" > "{remote_txt}"'
            )
            
            # Wait for file creation
            time.sleep(1)
            
            # Download and read the file
            local_txt = tempfile.mktemp(suffix=".txt")
            try:
                with SCPClient(self.ssh_client.client.get_transport()) as scp:
                    scp.get(remote_txt, local_txt)
                
                with open(local_txt, "r", encoding="utf-8") as f:
                    remote_files = set(line.strip().lower() for line in f if line.strip())
                
                return remote_files
            finally:
                if os.path.exists(local_txt):
                    os.remove(local_txt)
                # Clean up remote file
                self.ssh_client.client.exec_command(f'rm -f "{remote_txt}"')
                
        except Exception as e:
            logger.error(f"Failed to fetch remote file list: {str(e)}")
            raise
    
    def _sync_files(self, to_send, local_path):
        """Synchronize files between local and remote"""
        ssh_settings = self.config.get_ssh_settings()
        remote_base = ssh_settings['remote_path']
        
        for file in to_send:
            if not self.running:
                break
                
            try:
                local_file = local_path / file
                remote_dir = os.path.dirname(os.path.join(remote_base, file)).replace("\\", "/")
                
                # Ensure remote directory exists
                self.ssh_client.client.exec_command(f'mkdir -p "{remote_dir}"')
                
                # Upload file
                self.sync_progress.emit(f"Uploading {file}")
                with SCPClient(self.ssh_client.client.get_transport()) as scp:
                    scp.put(str(local_file), os.path.join(remote_base, file).replace("\\", "/"))
                
                self.sent_files.add(file.lower())
                logger.info(f"Uploaded {file}")
                
            except Exception as e:
                logger.error(f"Failed to upload {file}: {str(e)}")
                self.sync_progress.emit(f"Error uploading {file}: {str(e)}")

class SyncManager(QObject):
    def __init__(self, config):
        super().__init__()
        self.config = config
        self.watcher = None
        self.sync_worker = None
        self.pending_files = set()  # Track files pending upload
        
    def start_sync(self):
        """Start automatic synchronization"""
        sync_settings = self.config.get_sync_settings()
        local_path = Path(sync_settings['local_path'])
        local_path.mkdir(parents=True, exist_ok=True)
        
        # Start file system watcher
        if not self.watcher:
            self.watcher = QFileSystemWatcher()
            self.watcher.directoryChanged.connect(self._on_directory_changed)
            self.watcher.fileChanged.connect(self._on_file_changed)
        
        # Add local path and its subdirectories to watcher
        self._add_watch_paths(local_path)
        
        # Start sync worker
        if not self.sync_worker:
            self.sync_worker = SyncWorker(self.config)
            self.sync_worker.sync_complete.connect(self._on_sync_complete)
            self.sync_worker.sync_progress.connect(self._on_sync_progress)
        
        # Enable continuous sync
        self.sync_worker.auto_sync = True
        self.sync_worker.start()
        
        logger.info("Continuous sync started with 10-second interval")
    
    def stop_sync(self):
        """Stop automatic synchronization"""
        if self.watcher:
            self.watcher.removePaths(self.watcher.directories())
            self.watcher.removePaths(self.watcher.files())
            self.watcher = None
        
        if self.sync_worker:
            self.sync_worker.running = False
            self.sync_worker.auto_sync = False
            self.sync_worker.wait()
            self.sync_worker = None
        
        logger.info("Sync stopped")
    
    def sync_now(self):
        """Perform immediate synchronization"""
        if self.sync_worker and self.sync_worker.isRunning():
            logger.info("Sync already running")
            return
            
        self.sync_worker = SyncWorker(self.config)
        self.sync_worker.sync_complete.connect(self._on_sync_complete)
        self.sync_worker.sync_progress.connect(self._on_sync_progress)
        self.sync_worker.auto_sync = False
        self.sync_worker.start()
    
    def _add_watch_paths(self, path):
        """Add directory and its subdirectories to watcher"""
        try:
            # Add main directory
            self.watcher.addPath(str(path))
            logger.info(f"Watching directory: {path}")
            
            # Add all subdirectories and files
            for root, dirs, files in os.walk(path):
                root_path = Path(root)
                # Add directories
                for dir_name in dirs:
                    dir_path = root_path / dir_name
                    self.watcher.addPath(str(dir_path))
                    logger.info(f"Watching directory: {dir_path}")
                # Add files
                for file_name in files:
                    file_path = root_path / file_name
                    self.watcher.addPath(str(file_path))
                    logger.info(f"Watching file: {file_path}")
                    # Add to pending files if not already synced
                    if not self.sync_worker or file_name.lower() not in self.sync_worker.sent_files:
                        self.pending_files.add(str(file_path))
        except Exception as e:
            logger.error(f"Failed to add watch paths: {str(e)}")
    
    def _on_directory_changed(self, path):
        """Handle directory change events"""
        try:
            path = Path(path)
            logger.info(f"Directory changed: {path}")
            
            # Get sync settings
            sync_settings = self.config.get_sync_settings()
            local_base = Path(sync_settings['local_path'])
            
            # Check for new files
            for item in path.glob('*'):
                if item.is_file():
                    rel_path = item.relative_to(local_base)
                    if not self.sync_worker or str(rel_path).lower() not in self.sync_worker.sent_files:
                        self.pending_files.add(str(item))
                        logger.info(f"New file detected: {item}")
                elif item.is_dir():
                    # Add new directory to watcher
                    self._add_watch_paths(item)
            
            # Trigger sync if there are pending files
            if self.pending_files:
                self._sync_pending_files()
            
        except Exception as e:
            logger.error(f"Error handling directory change: {str(e)}")
    
    def _on_file_changed(self, path):
        """Handle file change events"""
        try:
            path = Path(path)
            logger.info(f"File changed: {path}")
            
            if path.exists():  # File was modified
                self.pending_files.add(str(path))
                self._sync_pending_files()
            
        except Exception as e:
            logger.error(f"Error handling file change: {str(e)}")
    
    def _sync_pending_files(self):
        """Sync pending files to remote server"""
        if not self.sync_worker or not self.sync_worker.isRunning():
            sync_settings = self.config.get_sync_settings()
            local_base = Path(sync_settings['local_path'])
            
            # Convert absolute paths to relative paths
            relative_paths = []
            for file_path in self.pending_files:
                try:
                    rel_path = str(Path(file_path).relative_to(local_base))
                    relative_paths.append(rel_path)
                except Exception as e:
                    logger.error(f"Error converting path {file_path}: {str(e)}")
            
            if relative_paths:
                logger.info(f"Syncing pending files: {relative_paths}")
                self.sync_worker = SyncWorker(self.config)
                self.sync_worker.sync_complete.connect(self._on_sync_complete)
                self.sync_worker.sync_progress.connect(self._on_sync_progress)
                self.sync_worker.auto_sync = False
                self.sync_worker.start()
    
    def _on_sync_complete(self, success, message):
        """Handle sync completion"""
        if success:
            self.pending_files.clear()
        logger.info(f"Sync complete: {message}")
    
    def _on_sync_progress(self, message):
        """Handle sync progress"""
        logger.info(f"Sync progress: {message}")