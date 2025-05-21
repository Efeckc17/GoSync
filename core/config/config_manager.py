import os
import json
import platform
import base64
from pathlib import Path
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import logging

logger = logging.getLogger('GOSync')

class ConfigManager:
    def __init__(self):
        self._setup_paths()
        self._setup_encryption()
        self.config = self.load_config()
    
    def _setup_paths(self):
        """Setup application paths based on OS"""
        system = platform.system().lower()
        
        if system == 'windows':
            # Windows: Use %APPDATA%\GOSync
            self.config_dir = os.path.join(os.environ.get('APPDATA', ''), 'GOSync')
            self.sync_folder = os.path.join(os.path.expanduser('~'), 'GOSyncFiles')
        elif system == 'darwin':
            # macOS: Use ~/Library/Application Support/GOSync
            self.config_dir = os.path.join(
                os.path.expanduser('~'),
                'Library/Application Support/GOSync'
            )
            self.sync_folder = os.path.join(os.path.expanduser('~'), 'GOSyncFiles')
        else:
            # Linux/Unix: Use ~/.config/GOSync
            self.config_dir = os.path.join(
                os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')),
                'GOSync'
            )
            self.sync_folder = os.path.join(os.path.expanduser('~'), 'GOSyncFiles')
        
        # Ensure config directory exists
        os.makedirs(self.config_dir, mode=0o700, exist_ok=True)
        
        # Define config files
        self.config_file = os.path.join(self.config_dir, 'config.json')
        self.key_file = os.path.join(self.config_dir, '.key')
    
    def _setup_encryption(self):
        """Setup encryption for sensitive data"""
        try:
            if os.path.exists(self.key_file):
                # Load existing key
                with open(self.key_file, 'rb') as f:
                    self.key = f.read()
            else:
                # Generate new key
                self.key = Fernet.generate_key()
                # Save key with restricted permissions
                with open(self.key_file, 'wb') as f:
                    os.chmod(self.key_file, 0o600)
                    f.write(self.key)
            
            self.cipher = Fernet(self.key)
            
        except Exception as e:
            logger.error(f"Failed to setup encryption: {str(e)}")
            raise
    
    def _encrypt(self, data: str) -> str:
        """Encrypt sensitive data"""
        try:
            return base64.b64encode(
                self.cipher.encrypt(data.encode())
            ).decode()
        except Exception as e:
            logger.error(f"Encryption failed: {str(e)}")
            return ""
    
    def _decrypt(self, encrypted_data: str) -> str:
        """Decrypt sensitive data"""
        try:
            if not encrypted_data:
                return ""
            return self.cipher.decrypt(
                base64.b64decode(encrypted_data.encode())
            ).decode()
        except Exception as e:
            logger.error(f"Decryption failed: {str(e)}")
            return ""
    
    def load_config(self):
        """Load configuration from file or create default"""
        default_config = {
            "ssh": {
                "hostname": "",
                "username": "",
                "remote_path": "",
                "ssh_key": "",
                "password": ""
            },
            "sync": {
                "auto_sync": False,
                "sync_interval": 300,  # 5 minutes
                "local_path": self.sync_folder
            }
        }
        
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r', encoding='utf-8') as f:
                    config = json.load(f)
                    
                    # Decrypt sensitive data
                    if 'ssh' in config:
                        ssh = config['ssh']
                        ssh['password'] = self._decrypt(ssh.get('password', ''))
                        ssh['ssh_key'] = self._decrypt(ssh.get('ssh_key', ''))
                    
                    # Update with any missing default values
                    if 'ssh' not in config:
                        config['ssh'] = default_config['ssh']
                    if 'sync' not in config:
                        config['sync'] = default_config['sync']
                    
                    return config
                    
        except Exception as e:
            logger.error(f"Error loading config: {str(e)}")
        
        return default_config
    
    def save_config(self):
        """Save current configuration to file"""
        try:
            # Create a copy of config to encrypt sensitive data
            config_to_save = {
                "ssh": dict(self.config['ssh']),
                "sync": dict(self.config['sync'])
            }
            
            # Encrypt sensitive data
            ssh = config_to_save['ssh']
            ssh['password'] = self._encrypt(ssh.get('password', ''))
            ssh['ssh_key'] = self._encrypt(ssh.get('ssh_key', ''))
            
            # Save with restricted permissions
            with open(self.config_file, 'w', encoding='utf-8') as f:
                os.chmod(self.config_file, 0o600)
                json.dump(config_to_save, f, indent=4)
                
        except Exception as e:
            logger.error(f"Error saving config: {str(e)}")
    
    def get_ssh_settings(self):
        """Get SSH connection settings"""
        return self.config.get('ssh', {})
    
    def get_sync_settings(self):
        """Get synchronization settings"""
        return self.config.get('sync', {})
    
    def save_ssh_settings(self, settings):
        """Save SSH connection settings"""
        self.config['ssh'] = settings
        self.save_config()
    
    def save_sync_settings(self, settings):
        """Save synchronization settings"""
        self.config['sync'] = settings
        self.save_config()
    
    def get_sync_folder(self):
        """Get the sync folder path"""
        return self.sync_folder 