from PySide6.QtWidgets import QListWidget, QListWidgetItem
from PySide6.QtCore import Qt

class FileListWidget(QListWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setStyleSheet("""
            QListWidget {
                background-color: #2d2d2d;
                border: 1px solid #3d3d3d;
                border-radius: 4px;
                color: #FFFFFF;
            }
            QListWidget::item {
                padding: 4px;
            }
            QListWidget::item:selected {
                background-color: #4d4d4d;
            }
            QListWidget::item:hover {
                background-color: #3d3d3d;
            }
        """)
    
    def update_files(self, files):
        """Update the list with new files"""
        self.clear()
        for file in files:
            item = QListWidgetItem(file)
            self.addItem(item)
    
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    
    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            files.append(url.toLocalFile())
        self.update_files(files) 