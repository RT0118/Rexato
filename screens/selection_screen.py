"""
SelectionScreen - Initial screen to select conversion direction
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QPushButton, QLabel
from PyQt6.QtCore import Qt, QSize
from utils.pyqt6_colors import Colors
from utils.library_availability import REKORDBOX_AVAILABLE, SERATO_TOOLS_AVAILABLE


class SelectionScreen(QWidget):
    """Initial screen to select conversion direction"""
    
    def __init__(self, parent_window=None):
        super().__init__()
        self.parent_window = parent_window
        self.setup_ui()
    
    def setup_ui(self):
        """Set up the UI"""
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(30)
        layout.setContentsMargins(50, 50, 50, 50)
        
        # Title
        title = QLabel('Rexato')
        title.setStyleSheet(f"""
            QLabel {{
                color: {Colors.qss_color(Colors.FOREGROUND)};
                font-size: 36px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(title)
        
        subtitle = QLabel('Playlist Converter')
        subtitle.setStyleSheet(f"""
            QLabel {{
                color: {Colors.qss_color(Colors.COMMENT)};
                font-size: 18px;
            }}
        """)
        layout.addWidget(subtitle)
        
        # Add spacer
        layout.addStretch()
        
        # Conversion direction buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(20)
        
        rb_to_serato_btn = QPushButton('Rekordbox → Serato')
        rb_to_serato_btn.setMinimumHeight(60)
        rb_to_serato_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.qss_color(Colors.CYAN)};
                color: {Colors.qss_color(Colors.BACKGROUND)};
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.qss_color(Colors.GREEN)};
            }}
        """)
        rb_to_serato_btn.clicked.connect(self.on_rb_to_serato)
        button_layout.addWidget(rb_to_serato_btn)
        
        serato_to_rb_btn = QPushButton('Serato → Rekordbox')
        serato_to_rb_btn.setMinimumHeight(60)
        serato_to_rb_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.qss_color(Colors.PINK)};
                color: {Colors.qss_color(Colors.BACKGROUND)};
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.qss_color(Colors.PURPLE)};
            }}
        """)
        serato_to_rb_btn.clicked.connect(self.on_serato_to_rb)
        button_layout.addWidget(serato_to_rb_btn)
        
        layout.addLayout(button_layout)
        layout.addStretch()
        
        # Status messages
        self.status_label = QLabel('')
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.qss_color(Colors.RED)};
                font-size: 14px;
            }}
        """)
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
    
    def on_rb_to_serato(self):
        """Handle Rekordbox to Serato selection"""
        if not REKORDBOX_AVAILABLE:
            self.status_label.setText('Error: pyrekordbox not installed. Install with: python -m pip install pyrekordbox')
            return
        
        if self.parent_window:
            self.parent_window.show_library_browser('rekordbox', 'serato')
    
    def on_serato_to_rb(self):
        """Handle Serato to Rekordbox selection"""
        if not SERATO_TOOLS_AVAILABLE:
            self.status_label.setText('Error: serato-tools not installed. Install with: python -m pip install serato-tools')
            return
        
        if self.parent_window:
            self.parent_window.show_library_browser('serato', 'rekordbox')

