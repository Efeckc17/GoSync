import json
import os
from pathlib import Path

class Config:
    def __init__(self):
        self.config_dir = Path.home() / '.gosync'
        self.config_file = self.config_dir / 'config.json'
        self.ensure_config_dir()
        self.load_config()
    
    def ensure_config_dir(self):
        """Ensure the config directory exists"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
    
    def load_config(self):
        """Load configuration from file"""
        if self.config_file.exists():
            with open(self.config_file, 'r') as f:
                self.config = json.load(f)
        else:
            self.config = {
                'ssh': {
                    'hostname': '',
                    'username': '',
                    'remote_path': '',
                    'ssh_key': '',
                    'password': ''
                },
                'sync': {
                    'local_path': str(Path.home() / 'SyncerSync'),
                    'auto_sync': False,
                    'sync_interval': 300  # 5 minutes
                }
            }
            self.save_config()
    
    def save_config(self):
        """Save configuration to file"""
        with open(self.config_file, 'w') as f:
            json.dump(self.config, f, indent=4)
    
    def get_ssh_settings(self):
        """Get SSH connection settings"""
        return self.config.get('ssh', {})
    
    def save_ssh_settings(self, settings):
        """Save SSH connection settings"""
        self.config['ssh'] = settings
        self.save_config()
    
    def get_sync_settings(self):
        """Get synchronization settings"""
        return self.config.get('sync', {})
    
    def save_sync_settings(self, settings):
        """Save synchronization settings"""
        self.config['sync'] = settings
        self.save_config() 