"""
PyDracula-inspired colors for Rexato PyQt6 application
Based on Dracula theme colors
"""

from PyQt6.QtGui import QColor


class Colors:
    """Dracula theme color palette for PyQt6"""
    
    # Background
    BACKGROUND = QColor("#282a36")  # Main background
    BACKGROUND_SECONDARY = QColor("#44475a")  # Secondary background
    BACKGROUND_TERTIARY = QColor("#6272a4")  # Tertiary background
    
    # Foreground  
    FOREGROUND = QColor("#f8f8f2")  # Main text
    COMMENT = QColor("#6272a4")  # Comments/muted text
    
    # Accent Colors
    CYAN = QColor("#8be9fd")  # Cyan
    GREEN = QColor("#50fa7b")  # Green
    ORANGE = QColor("#ffb86c")  # Orange
    PINK = QColor("#ff79c6")  # Pink
    PURPLE = QColor("#bd93f9")  # Purple
    RED = QColor("#ff5555")  # Red
    YELLOW = QColor("#f1fa8c")  # Yellow
    
    # Selection
    SELECTION = QColor("#44475a")  # Selected item background
    SELECTION_ACTIVE = QColor("#6272a4")  # Active selection
    
    @staticmethod
    def qss_color(color: QColor) -> str:
        """Convert QColor to QSS string"""
        return f"rgb({color.red()}, {color.green()}, {color.blue()})"
    
    @staticmethod
    def qss_rgba(color: QColor) -> str:
        """Convert QColor to QSS rgba string"""
        return f"rgba({color.red()}, {color.green()}, {color.blue()}, {color.alpha()})"

