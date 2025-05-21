# GOSync - Secure File Backup Application

GOSync is a desktop application that enables secure file backup and synchronization over SSH.

## Features

- 🔒 Secure SSH connection
- 🔄 Automatic file synchronization
- 🕒 Customizable sync interval
- 📁 Local folder customization
- 🔐 Encrypted settings storage
- 💻 Cross-platform support (Windows, Linux)
- 🎯 Single instance application
- 🌈 Modern and user-friendly interface

## Installation

### Requirements

- Python 3.8 or higher
- pip (Python package manager)

### Steps

1. Clone the repository:
```bash
git clone https://github.com/Efeckc17/GoSync.git
cd GOSync
```

2. Create virtual environment (recommended):
```bash
python -m venv venv
# For Windows:
venv\Scripts\activate
# For Linux:
source venv/bin/activate
```

3. Install required packages:
```bash
pip install -r requirements.txt
```

4. Start the application:
```bash
python main.py
```

## Configuration

Application settings are stored in the following locations based on the operating system:

- Windows: `%APPDATA%\GOSync`
- Linux: `~/.config/GOSync`

Synchronized files are stored by default in:
- Windows: `C:\Users\Username\GOSyncFiles`
- Linux: `~/GOSyncFiles`

## Security Features

- SSH password and key are stored encrypted
- Configuration files are protected with secure permissions (600)
- Configuration directory is restricted to user access only (700)
- Sensitive data is protected with Fernet encryption

## Usage

1. Click "Settings" button on first launch
2. Enter SSH connection details:
   - Server address
   - Username
   - Remote directory path
   - SSH key or password
3. Select local synchronization folder
4. Click "Start Sync" to begin synchronization

## Features

### Automatic Synchronization
- Start automatic sync with "Start Sync"
- Stop with "Stop Sync"
- Manual sync with "Sync Now"

### File Operations
- Right-click menu for file download/upload
- Drag-and-drop support
- Double-click to open files

### System Tray
- Application continues running in system tray when closed
- Quick access through right-click menu
- Synchronization status notifications

## Contributing

1. Fork this repository
2. Create a new branch (`git checkout -b feature/NewFeature`)
3. Commit your changes (`git commit -am 'Add new feature: XYZ'`)
4. Push to the branch (`git push origin feature/NewFeature`)
5. Create a Pull Request

## Author

- [@Efeckc17](https://github.com/Efeckc17) - Desktop Application Developer

## License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details. 