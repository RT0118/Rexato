"""
LoadingScreen - Loading screen with spinner and progress messages
"""

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QMovie
from utils.pyqt6_colors import Colors


class LoadingScreen(QWidget):
    """Loading screen with spinner and progress messages"""
    
    def __init__(self):
        super().__init__()
        self._ellipse_count = 0
        self.setup_ui()
        self.start_ellipses_animation()
    
    def setup_ui(self):
        """Set up the UI"""
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.setSpacing(20)
        
        # Create animated spinner using QLabel with a movie
        # We'll use a text-based spinner instead
        self.spinner_label = QLabel()
        self.spinner_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.spinner_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.qss_color(Colors.CYAN)};
                font-size: 48px;
                font-weight: bold;
            }}
        """)
        self.spinner_label.setText('◐')  # Unicode spinner
        layout.addWidget(self.spinner_label)
        
        # Start rotation animation
        self.rotation_angle = 0
        self.timer = QTimer()
        self.timer.timeout.connect(self.rotate_spinner)
        self.timer.start(50)  # Update every 50ms for smooth rotation
        
        # Main status label
        self.status_label = QLabel('Loading')
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.qss_color(Colors.FOREGROUND)};
                font-size: 20px;
                font-weight: bold;
            }}
        """)
        layout.addWidget(self.status_label)
        
        # Progress label
        self.progress_label = QLabel('')
        self.progress_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.progress_label.setStyleSheet(f"""
            QLabel {{
                color: {Colors.qss_color(Colors.COMMENT)};
                font-size: 14px;
            }}
        """)
        layout.addWidget(self.progress_label)
        
        self.setLayout(layout)
    
    def rotate_spinner(self):
        """Rotate the spinner character"""
        # Create rotating spinner effect
        self.rotation_angle = (self.rotation_angle + 18) % 360
        
        # Use different spinner characters to create animation
        spinner_chars = ['◐', '◓', '◑', '◒']
        char_index = int(self.rotation_angle / 30) % len(spinner_chars)
        self.spinner_label.setText(spinner_chars[char_index])
    
    def start_ellipses_animation(self):
        """Start the ellipses animation"""
        self.ellipses_timer = QTimer()
        self.ellipses_timer.timeout.connect(self.animate_ellipses)
        self.ellipses_timer.start(500)  # Update every 500ms
    
    def animate_ellipses(self):
        """Animate ellipses"""
        self._ellipse_count = (self._ellipse_count + 1) % 4
        ellipses = '.' * self._ellipse_count
        self.status_label.setText(f'Loading{ellipses}')
    
    def update_status(self, message):
        """Update the main status message"""
        if message:
            self.ellipses_timer.stop()
            self.status_label.setText(message)
    
    def update_progress(self, status, progress):
        """Update the progress message"""
        # Both parameters are received as strings
        if progress:
            self.progress_label.setText(progress)
        if status and status.strip():
            self.status_label.setText(status)

