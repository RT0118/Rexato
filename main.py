"""
Rexato - Rekordbox/Serato Playlist Converter GUI
PyQt6 application with PyDracula theme
"""

import sys

from PyQt6.QtWidgets import QApplication, QMainWindow, QStackedWidget, QVBoxLayout, QWidget
from PyQt6.QtCore import Qt, QThread, pyqtSignal


# Import library availability checks
from utils.library_availability import REKORDBOX_AVAILABLE, SERATO_TOOLS_AVAILABLE

# Import PyDracula colors
from utils.pyqt6_colors import Colors


# Store global reference to app for access from widgets
_global_app = None


class PlaylistLoader(QThread):
    """Background thread for loading playlists"""
    finished = pyqtSignal(list)  # Emits list of playlists when done
    progress = pyqtSignal(str, str)  # Emits (status, progress) updates
    
    def __init__(self, source_type, parent=None):
        super().__init__(parent)
        self.source_type = source_type
    
    def run(self):
        """Load playlists in background thread"""
        try:
            # Progress callback that emits signals
            def progress_callback(status, progress, debug):
                self.progress.emit(status, progress)
            
            if self.source_type == 'rekordbox':
                from utils.rekordbox_utils import load_rekordbox_playlists_OOP
                playlists = load_rekordbox_playlists_OOP(progress_callback=progress_callback)
            elif self.source_type == 'serato':
                from utils.serato_utils import load_serato_crates
                playlists = load_serato_crates(progress_callback=progress_callback)
            else:
                playlists = []
            
            self.finished.emit(playlists)
            
        except Exception as e:
            print(f"Error loading playlists: {e}")
            import traceback
            traceback.print_exc()
            self.finished.emit([])


class RexatoWindow(QMainWindow):
    """Main application window with PyDracula theme"""
    
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Rexato - Playlist Converter")
        self.setMinimumSize(1200, 800)
        
        # Set window background color
        self.setStyleSheet(f"""
            QMainWindow {{
                background-color: {Colors.qss_color(Colors.BACKGROUND)};
                color: {Colors.qss_color(Colors.FOREGROUND)};
            }}
        """)
        
        # Create central widget with stacked layout for screens
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        self.stacked_widget = QStackedWidget()
        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stacked_widget)
        central_widget.setLayout(layout)
        
        # Initialize screens
        self.show_selection_screen()
    
    def _clear_stack(self):
        """Clear all widgets from the stacked widget"""
        while self.stacked_widget.count() > 0:
            widget = self.stacked_widget.widget(0)
            self.stacked_widget.removeWidget(widget)
            widget.deleteLater()
    
    def show_selection_screen(self):
        """Show the selection screen"""
        from screens.selection_screen import SelectionScreen
        self._clear_stack()
        selection = SelectionScreen(parent_window=self)
        self.stacked_widget.addWidget(selection)
    
    def show_loading_screen(self, source_type, target_type):
        """Show loading screen and start loading"""
        from screens.loading_screen import LoadingScreen
        self._clear_stack()
        loading = LoadingScreen()
        self.stacked_widget.addWidget(loading)
        
        # Start loading in background thread
        self.loader = PlaylistLoader(source_type)
        self.loader.progress.connect(loading.update_progress)
        self.loader.finished.connect(lambda playlists: self.on_playlists_loaded(source_type, target_type, playlists))
        self.loader.start()
    
    def on_playlists_loaded(self, source_type, target_type, playlists):
        """Switch to library browser after playlists are loaded"""
        from screens.library_browser_screen import LibraryBrowserScreen
        self._clear_stack()
        browser = LibraryBrowserScreen(source_type, target_type, parent_window=self)
        browser.playlists = playlists
        browser.update_playlist_list()
        self.stacked_widget.addWidget(browser)
    
    def show_library_browser(self, source_type, target_type):
        """Deprecated: Use show_loading_screen instead"""
        self.show_loading_screen(source_type, target_type)


class RexatoApp(QApplication):
    """Main application class"""
    
    def __init__(self, argv):
        super().__init__(argv)
        global _global_app
        _global_app = self
        
        # Set application properties
        self.setApplicationName("Rexato")
        self.setOrganizationName("Rexato")
        
        # Set global style
        self.apply_pydracula_theme()
        
        # Create and show main window
        self.window = RexatoWindow()
        self.window.show()
    
    def apply_pydracula_theme(self):
        """Apply PyDracula theme stylesheet"""
        stylesheet = f"""
            /* Global styles */
            * {{
                font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
            }}
            
            /* Main window */
            QMainWindow {{
                background-color: {Colors.qss_color(Colors.BACKGROUND)};
                color: {Colors.qss_color(Colors.FOREGROUND)};
            }}
            
            /* Buttons */
            QPushButton {{
                background-color: {Colors.qss_color(Colors.PURPLE)};
                color: {Colors.qss_color(Colors.BACKGROUND)};
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }}
            
            QPushButton:hover {{
                background-color: {Colors.qss_color(Colors.PINK)};
            }}
            
            QPushButton:pressed {{
                background-color: {Colors.qss_color(Colors.RED)};
            }}
            
            /* Labels */
            QLabel {{
                color: {Colors.qss_color(Colors.FOREGROUND)};
            }}
            
            /* Scroll bars */
            QScrollBar:vertical {{
                background: {Colors.qss_color(Colors.BACKGROUND_SECONDARY)};
                width: 12px;
                border: none;
            }}
            
            QScrollBar::handle:vertical {{
                background: {Colors.qss_color(Colors.BACKGROUND_TERTIARY)};
                border-radius: 6px;
                min-height: 30px;
            }}
            
            QScrollBar::handle:vertical:hover {{
                background: {Colors.qss_color(Colors.FOREGROUND)};
            }}
            
            QScrollBar:horizontal {{
                background: {Colors.qss_color(Colors.BACKGROUND_SECONDARY)};
                height: 12px;
                border: none;
            }}
            
            QScrollBar::handle:horizontal {{
                background: {Colors.qss_color(Colors.BACKGROUND_TERTIARY)};
                border-radius: 6px;
                min-width: 30px;
            }}
            
            QScrollBar::handle:horizontal:hover {{
                background: {Colors.qss_color(Colors.FOREGROUND)};
            }}
        """
        self.setStyleSheet(stylesheet)
    
    def get_main_window(self):
        """Get the main window instance"""
        return self.window


def get_app():
    """Get the global application instance"""
    global _global_app
    return _global_app

def run_cli(source_type):
    from utils.rekordbox_classes import RbLibraryBase, RbFolder, RbIntelligentPlaylist, RbPlaylist, RbTrack, RbPlaylistAttribute, RbTrackFileType
    if source_type == 'rekordbox':
        from utils.rekordbox_utils import load_rekordbox_playlists_OOP
        library = load_rekordbox_playlists_OOP()

        # try printing library
        def print_tree(node, level=0):
            indent = "  "*level
            print(f"{indent}> {node.to_string()}")
            if type(node) == RbFolder:
                for x in node.subitems:
                    print_tree(x, level+1)
            elif type(node) == RbPlaylist:
                for x in node.tracks:
                    print(f"{indent}> {x.to_string()}")
        #for x in library:
        #    print_tree(x)

    elif source_type == 'serato':
        from utils.serato_utils import load_serato_crates
        playlists = load_serato_crates()
    else:
        playlists = []
    

if __name__ == '__main__':
    #run_cli("rekordbox")
    app = RexatoApp(sys.argv)
    sys.exit(app.exec())
