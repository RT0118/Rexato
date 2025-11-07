"""
LibraryBrowserScreen - Main library browser with left panel and right panel
"""

from PyQt6.QtWidgets import (QWidget, QHBoxLayout, QVBoxLayout, QPushButton, QLabel, 
                              QTableWidget, QTableWidgetItem, QHeaderView,
                              QMessageBox, QTreeWidget, QTreeWidgetItem, QTreeWidgetItemIterator,
                              QDialog, QDialogButtonBox, QProgressBar)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QFontMetrics
from utils.pyqt6_colors import Colors
from utils.metadata_utils import format_time
from utils.key_converter import convert_key
from utils.path_utils import get_resource_path
import os
from utils.rekordbox_classes import RbFolder, RbIntelligentPlaylist, RbPlaylist, RbTrack
from utils.serato_classes import SeratoCrate, SeratoTrack

class SmartResizeTable(QTableWidget):
    """Table with stretch-by-default columns that become interactive when manually resized"""
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._manually_resized_columns = set()  # Columns that have been manually resized
        self._is_adjusting = False
        self._base_widths = {}  # Store base widths for stretchable columns
        self._column_min_widths = {}  # Per-column minimum widths
        
        header = self.horizontalHeader()
        header.sectionResized.connect(self._on_section_resized)
    
    def getMinColumnWidth(self, column_index):
        """Get the minimum width for a specific column"""
        return self._column_min_widths.get(column_index, 40)
    
    def setColumnCount(self, columns):
        """Set column count and initialize stretchable columns"""
        super().setColumnCount(columns)
        header = self.horizontalHeader()
        # All columns start as Interactive so they can be resized
        for i in range(columns):
            header.setSectionResizeMode(i, QHeaderView.ResizeMode.Interactive)
    
    def setStretchableColumns(self, stretchable_indices):
        """Set which columns should be stretchable by default"""
        self._stretchable_indices = set(stretchable_indices)
        # Store initial widths for stretchable columns
        header = self.horizontalHeader()
        for idx in stretchable_indices:
            if idx < self.columnCount():
                self._base_widths[idx] = header.sectionSize(idx)
    
    def showEvent(self, event):
        """Trigger initial stretch adjustment when widget is first shown"""
        super().showEvent(event)
        # Use timer to ensure viewport is ready
        QTimer.singleShot(50, self._adjust_stretch)
    
    def resizeEvent(self, event):
        """Auto-stretch non-manually-resized columns when table is resized"""
        super().resizeEvent(event)
        self._adjust_stretch()
    
    def _adjust_stretch(self):
        """Adjust stretchable columns to fill available space"""
        if self._is_adjusting:
            return
        
        # Only adjust if we have stretchable columns defined
        if not hasattr(self, '_stretchable_indices'):
            return
        
        # Get columns that should auto-stretch (stretchable but not manually resized)
        auto_stretch_cols = [
            idx for idx in self._stretchable_indices 
            if idx not in self._manually_resized_columns and idx < self.columnCount()
        ]
        
        if not auto_stretch_cols:
            return
        
        self._is_adjusting = True
        try:
            header = self.horizontalHeader()
            viewport_width = self.viewport().width()
            
            if viewport_width <= 0:
                return
            
            # Calculate total fixed width (non-stretchable + manually resized stretchable)
            fixed_width = sum(
                header.sectionSize(i) 
                for i in range(self.columnCount()) 
                if i not in auto_stretch_cols
            )
            
            # Calculate available width for stretching
            available_width = viewport_width - fixed_width
            
            if available_width > 0 and len(auto_stretch_cols) > 0:
                # Distribute available width proportionally based on base widths
                total_base = sum(
                    self._base_widths.get(idx, header.sectionSize(idx)) 
                    for idx in auto_stretch_cols
                )
                
                if total_base > 0:
                    for idx in auto_stretch_cols:
                        base_width = self._base_widths.get(idx, header.sectionSize(idx))
                        ratio = base_width / total_base
                        min_width = self.getMinColumnWidth(idx)
                        new_width = max(min_width, int(available_width * ratio))
                        header.resizeSection(idx, new_width)
        finally:
            self._is_adjusting = False
    
    def _on_section_resized(self, logical_index, old_size, new_size):
        """Track when a column is manually resized"""
        if self._is_adjusting:
            return
        
        # Ensure column doesn't go below minimum width
        min_width = self.getMinColumnWidth(logical_index)
        if new_size < min_width:
            self._is_adjusting = True
            try:
                header = self.horizontalHeader()
                header.resizeSection(logical_index, min_width)
            finally:
                self._is_adjusting = False
            new_size = min_width
        
        # Mark this column as manually resized if it's a stretchable column
        if hasattr(self, '_stretchable_indices') and logical_index in self._stretchable_indices:
            if logical_index not in self._manually_resized_columns:
                self._manually_resized_columns.add(logical_index)
            # Update base width for this column
            self._base_widths[logical_index] = new_size
            # Adjust other stretchable columns to fill remaining space
            QTimer.singleShot(10, self._adjust_stretch)


class LibraryBrowserScreen(QWidget):
    """Main library browser with left panel and right panel"""
    
    def __init__(self, source_type, target_type, parent_window=None):
        super().__init__()
        self.source_type = source_type
        self.target_type = target_type
        self.playlists = []
        self.current_playlist = None
        self.parent_window = parent_window
        self.key_format = 'camelot'  # Default to Camelot format
        self._original_track_order = []  # Store original track order for reset
        self._last_sorted_column = -1  # Track last sorted column
        self._sort_order = Qt.SortOrder.AscendingOrder  # Current sort order
        self.setup_ui()
    
    def _create_track_progress_callback(self, progress_dialog):
        """Create a progress callback for track-level updates"""
        def track_progress_callback(name, current, total):
            progress_dialog.update_track_progress(name, current, total)
            # Process events to update UI
            from PyQt6.QtWidgets import QApplication
            QApplication.processEvents()
        return track_progress_callback
    
    def _show_conversion_results(self, results, success_count, fail_count, name_key, source_type):
        """Show conversion results in a message box"""
        # Determine item label based on what was converted
        item_label = 'crate(s)' if source_type == 'serato' else 'playlist(s)'
        message = f"Conversion Complete!\n\n"
        message += f"Successfully converted: {success_count} {item_label}\n"
        message += f"Failed: {fail_count} {item_label}\n\n"
        
        if success_count > 0:
            message += "Successfully converted:\n"
            for result in results:
                if result['success']:
                    name = result.get(name_key, 'Unknown')
                    track_count = result.get('track_count', 0)
                    suffix = '.crate' if name_key == 'crate_name' else ''
                    message += f"  • {name}{suffix} ({track_count} tracks)\n"
        
        if fail_count > 0:
            message += "\nFailed:\n"
            for result in results:
                if not result['success']:
                    name = result.get(name_key, 'Unknown')
                    error = result.get('error', 'Unknown error')
                    message += f"  • {name}: {error}\n"
        
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("Conversion Results")
        msg_box.setText(message)
        msg_box.setIcon(QMessageBox.Icon.Information)
        self._style_message_box(msg_box)
        msg_box.exec()
    
    def _style_message_box(self, msg_box):
        """Apply theme-aware styling to QMessageBox"""
        msg_box.setStyleSheet(f"""
            QMessageBox {{
                background-color: {Colors.qss_color(Colors.BACKGROUND)};
                color: {Colors.qss_color(Colors.FOREGROUND)};
            }}
            QMessageBox QLabel {{
                color: {Colors.qss_color(Colors.FOREGROUND)};
            }}
            QMessageBox QPushButton {{
                background-color: {Colors.qss_color(Colors.BACKGROUND_SECONDARY)};
                color: {Colors.qss_color(Colors.FOREGROUND)};
                border: 1px solid {Colors.qss_color(Colors.BACKGROUND_TERTIARY)};
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
                min-width: 80px;
            }}
            QMessageBox QPushButton:hover {{
                background-color: {Colors.qss_color(Colors.SELECTION)};
                border: 1px solid {Colors.qss_color(Colors.CYAN)};
            }}
            QMessageBox QPushButton:pressed {{
                background-color: {Colors.qss_color(Colors.SELECTION_ACTIVE)};
            }}
        """)
    
    def _format_rating_value(self, value):
        """Format rating value as stars (★ for filled, ☆ for empty)"""
        try:
            # Try to convert to integer
            rating = int(float(str(value)))
            # Clamp to 0-5 range
            rating = max(0, min(5, rating))
            # Return stars: filled stars for rating, empty stars for remainder
            filled_stars = '★' * rating
            empty_stars = '☆' * (5 - rating)
            return filled_stars + empty_stars
        except (ValueError, TypeError):
            # If value is not a valid number, return empty stars
            return '☆' * 5
    
    def _parse_key_value(self, key_string):
        """Extract the key value from string (e.g., '<DjmdKey(1567300487 Name=12A)>' -> '12A')"""
        if not key_string:
            return ''
        
        key_str = str(key_string)
        
        # Find the position of 'Name=' 
        name_pos = key_str.find('Name=')
        if name_pos == -1:
            return key_str
        
        # Find the position of '=' (after 'Name')
        eq_pos = key_str.find('=', name_pos)
        if eq_pos == -1:
            return key_str
        
        # Find the position of ')' after the '='
        closing_paren_pos = key_str.find(')', eq_pos)
        if closing_paren_pos == -1:
            return key_str
        
        # Extract the substring between '=' and ')'
        # Start from after the '=' character
        key_value = key_str[eq_pos + 1:closing_paren_pos]
        return key_value
    
    def _format_time_value(self, time_value):
        """Format time value - handles both numeric (seconds) and already formatted strings"""
        if not time_value and time_value != 0:
            return 'N/A'
        
        time_str = str(time_value).strip()
        
        # If it's already a formatted string (contains ':')
        if ':' in time_str:
            # If it's "0:00", might be missing data, but keep it as-is
            return time_str
        
        # Try to parse as number (seconds) and format it
        try:
            seconds = float(time_value)
            if seconds <= 0:
                return 'N/A'
            return format_time(seconds)
        except (ValueError, TypeError):
            # If parsing fails, return original string or N/A
            return time_str if time_str else 'N/A'
    
    def setup_ui(self):
        """Set up the UI"""
        main_layout = QHBoxLayout()
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Left panel - Playlists/Crates
        left_panel = QWidget()
        left_panel.setFixedWidth(300)
        left_layout = QVBoxLayout()
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(5)
        
        # Header with settings button - use terminology based on source type
        header_layout = QHBoxLayout()
        header_layout.setContentsMargins(0, 0, 0, 0)
        header_layout.setSpacing(10)
        
        if self.source_type.lower() == 'rekordbox':
            header_text = 'Rekordbox Playlists'
        else:
            header_text = 'Serato Crates'
        header = QLabel(header_text)
        header.setStyleSheet(f"""
            QLabel {{
                color: {Colors.qss_color(Colors.FOREGROUND)};
                font-size: 14px;
                font-weight: bold;
                padding: 10px;
            }}
        """)
        header_layout.addWidget(header)
        header_layout.addStretch()  # Push settings button to the right
        
        # Settings button aligned to the right
        settings_btn = QPushButton('Settings')
        settings_btn.setMinimumHeight(30)
        settings_btn.setToolTip('Settings')
        settings_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.qss_color(Colors.BACKGROUND_SECONDARY)};
                color: {Colors.qss_color(Colors.FOREGROUND)};
                border: none;
                border-radius: 5px;
                font-size: 12px;
                padding: 6px 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.qss_color(Colors.SELECTION)};
                color: {Colors.qss_color(Colors.CYAN)};
            }}
            QPushButton:pressed {{
                background-color: {Colors.qss_color(Colors.SELECTION_ACTIVE)};
            }}
        """)
        settings_btn.clicked.connect(self.on_settings)
        header_layout.addWidget(settings_btn)
        
        left_layout.addLayout(header_layout)
        
        # Playlist tree with sections
        self.playlist_tree = QTreeWidget()
        self.playlist_tree.setHeaderLabel("Playlists")
        self.playlist_tree.setHeaderHidden(True)
        self.playlist_tree.setRootIsDecorated(True)  # Show expand/collapse chevrons for root items
        self.playlist_tree.setExpandsOnDoubleClick(False)  # Don't require double-click
        # Enable chevron indicators for all items with children
        self.playlist_tree.setItemsExpandable(True)  # Allow expanding/collapsing items
        
        # Get paths to SVG icons
        checkmark_path = get_resource_path('resources/checkboxtick-svgrepo-com.svg')
        indeterminate_path = get_resource_path('resources/indeterminate-svgrepo-com.svg')
        chevron_right_path = get_resource_path('resources/arrowshortforward-svgrepo-com.svg')
        chevron_down_path = get_resource_path('resources/arrowshortbottom-svgrepo-com.svg')
        
        self.playlist_tree.setStyleSheet(f"""
            QTreeWidget {{
                background-color: {Colors.qss_color(Colors.BACKGROUND_SECONDARY)};
                border: none;
            }}
            QTreeWidget::item {{
                color: {Colors.qss_color(Colors.FOREGROUND)};
                padding: 5px;
                border-bottom: 1px solid {Colors.qss_color(Colors.BACKGROUND_TERTIARY)};
            }}
            QTreeWidget::item:hover {{
                background-color: {Colors.qss_color(Colors.SELECTION)};
            }}
            QTreeWidget::item:selected {{
                background-color: {Colors.qss_color(Colors.SELECTION_ACTIVE)};
            }}
            /* Branch styling - make chevrons visible with theme colors */
            QTreeWidget::branch {{
                background-color: {Colors.qss_color(Colors.BACKGROUND_SECONDARY)};
            }}
            /* Custom chevron icons for collapsed folders (pointing right) */
            QTreeWidget::branch:closed:has-children:!has-siblings {{
                image: url({chevron_right_path});
            }}
            QTreeWidget::branch:closed:has-children:has-siblings {{
                image: url({chevron_right_path});
            }}
            /* Custom chevron icons for expanded folders (pointing down) */
            QTreeWidget::branch:open:has-children:!has-siblings {{
                image: url({chevron_down_path});
            }}
            QTreeWidget::branch:open:has-children:has-siblings {{
                image: url({chevron_down_path});
            }}
            /* No indicator for items without children */
            QTreeWidget::branch:!has-children:!has-siblings {{
                border-image: none;
                image: none;
            }}
            QTreeWidget::branch:!has-children:has-siblings {{
                border-image: none;
                image: none;
            }}
            /* Use SVG files for checkbox icons with colored backgrounds */
            QTreeWidget::indicator {{
                border: 1px solid {Colors.qss_color(Colors.FOREGROUND)};
                background-color: {Colors.qss_color(Colors.BACKGROUND)};
            }}
            QTreeWidget::indicator:checked {{
                border: 2px solid {Colors.qss_color(Colors.GREEN)};
                background-color: {Colors.qss_color(Colors.GREEN)};
                image: url({checkmark_path});
            }}
            QTreeWidget::indicator:indeterminate {{
                border: 2px solid {Colors.qss_color(Colors.CYAN)};
                background-color: {Colors.qss_color(Colors.CYAN)};
                image: url({indeterminate_path});
            }}
        """)
        self.playlist_tree.itemClicked.connect(self.on_playlist_selected)
        self.playlist_tree.itemChanged.connect(self.on_item_changed)
        left_layout.addWidget(self.playlist_tree)
        
        # Back button
        back_btn = QPushButton('← Back')
        back_btn.setMinimumHeight(50)
        back_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.qss_color(Colors.BACKGROUND_SECONDARY)};
                color: {Colors.qss_color(Colors.FOREGROUND)};
                border: none;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.qss_color(Colors.SELECTION)};
                color: {Colors.qss_color(Colors.CYAN)};
            }}
            QPushButton:pressed {{
                background-color: {Colors.qss_color(Colors.SELECTION_ACTIVE)};
            }}
        """)
        back_btn.clicked.connect(self.on_back)
        left_layout.addWidget(back_btn)
        
        left_panel.setLayout(left_layout)
        main_layout.addWidget(left_panel)
        
        # Right panel - Track details
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setSpacing(10)
        
        # Track table with smart resize (stretch by default, interactive when manually resized)
        self.track_table = SmartResizeTable()
        self.track_table.setColumnCount(11)
        self.track_table.setHorizontalHeaderLabels([
            '#', 'Title', 'Artist', 'Time', 'BPM', 'Key', 'Rating', 'Genre', 'Type', 'Year', 'Comments'
        ])
        
        # Configure table
        self.track_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.track_table.setAlternatingRowColors(True)
        self.track_table.verticalHeader().setVisible(False)
        self.track_table.setShowGrid(True)
        # Don't enable built-in sorting - we'll handle it manually
        self.track_table.setSortingEnabled(False)
        
        # Configure header
        header = self.track_table.horizontalHeader()
        header.setSectionsClickable(True)  # Enable clicking on headers
        header.setSortIndicatorShown(True)  # Show sort indicators
        header.sectionClicked.connect(self.on_header_clicked)  # Connect header click event
        
        # Calculate minimum widths based on header text
        header_labels = ['#', 'Title', 'Artist', 'Time', 'BPM', 'Key', 'Rating', 'Genre', 'Type', 'Year', 'Comments']
        header_font = header.font()
        font_metrics = QFontMetrics(header_font)
        
        # Calculate and set minimum width for each column based on header text
        # Add padding (left padding + text width + right padding + some extra margin)
        padding = 30  # Total horizontal padding (increased to prevent text cutoff)
        for col_idx, label in enumerate(header_labels):
            text_width = font_metrics.horizontalAdvance(label)
            
            # Special handling for Rating column - need space for 5 stars (★★★★★)
            if col_idx == 6:  # Rating column
                stars_width = font_metrics.horizontalAdvance('★★★★★')
                min_width = max(text_width, stars_width) + padding
            else:
                min_width = text_width + padding
            
            # Store the minimum width for this column in the table
            self.track_table._column_min_widths[col_idx] = min_width
        
        # Set a global minimum as well (use the smallest calculated minimum)
        global_min = min(self.track_table._column_min_widths.values()) if self.track_table._column_min_widths else 40
        header.setMinimumSectionSize(global_min)
        
        # Set initial column widths based on minimum text size (header text width)
        for col_idx in range(self.track_table.columnCount()):
            min_width = self.track_table._column_min_widths.get(col_idx, 40)
            self.track_table.setColumnWidth(col_idx, min_width)
        
        # Set which columns should stretch by default (will become interactive when manually resized)
        # Columns 1, 2, 7, 10 are stretchable (Title, Artist, Genre, Comments)
        self.track_table.setStretchableColumns([1, 2, 7, 10])
        
        # Set fixed columns to Fixed mode (they won't stretch)
        header.setSectionResizeMode(0, QHeaderView.ResizeMode.Fixed)    # Track
        header.setSectionResizeMode(3, QHeaderView.ResizeMode.Fixed)    # Time
        header.setSectionResizeMode(4, QHeaderView.ResizeMode.Fixed)    # BPM
        header.setSectionResizeMode(5, QHeaderView.ResizeMode.Fixed)    # Key
        header.setSectionResizeMode(6, QHeaderView.ResizeMode.Fixed)    # Rating
        header.setSectionResizeMode(8, QHeaderView.ResizeMode.Fixed)    # Type
        header.setSectionResizeMode(9, QHeaderView.ResizeMode.Fixed)    # Year
        
        # Style the table
        self.track_table.setStyleSheet(f"""
            QTableWidget {{
                background-color: {Colors.qss_color(Colors.BACKGROUND)};
                color: {Colors.qss_color(Colors.FOREGROUND)};
                border: none;
                gridline-color: {Colors.qss_color(Colors.BACKGROUND_SECONDARY)};
            }}
            QTableWidget::item {{
                border: none;
                padding: 5px;
            }}
            QTableWidget::item:selected {{
                background-color: {Colors.qss_color(Colors.SELECTION_ACTIVE)};
            }}
            QHeaderView::section {{
                background-color: {Colors.qss_color(Colors.BACKGROUND_SECONDARY)};
                color: {Colors.qss_color(Colors.FOREGROUND)};
                padding: 10px;
                border: none;
                border-right: 1px solid {Colors.qss_color(Colors.BACKGROUND_TERTIARY)};
                font-weight: bold;
            }}
            QHeaderView::section:hover {{
                background-color: {Colors.qss_color(Colors.BACKGROUND_TERTIARY)};
                color: {Colors.qss_color(Colors.CYAN)};
            }}
        """)
        
        right_layout.addWidget(self.track_table)
        
        # Convert button
        convert_btn = QPushButton(f'Convert Selected to {self.target_type.title()}')
        convert_btn.setMinimumHeight(50)
        convert_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.qss_color(Colors.GREEN)};
                color: {Colors.qss_color(Colors.BACKGROUND)};
                border: none;
                border-radius: 5px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.qss_color(Colors.CYAN)};
            }}
        """)
        convert_btn.clicked.connect(self.on_convert)
        right_layout.addWidget(convert_btn)
        
        right_panel.setLayout(right_layout)
        main_layout.addWidget(right_panel)
        
        self.setLayout(main_layout)
    
    def _add_serato_crate_to_tree(self, crate: SeratoCrate, parent_item):
        text = f"📦 {crate.name} ({len(crate.tracks)})"
        item = QTreeWidgetItem(parent_item)
        item.setText(0, text)
        item.setData(0, Qt.ItemDataRole.UserRole, crate)

        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Unchecked)
        item.setExpanded(True)

        for sub in crate.subcrates:
            self._add_serato_crate_to_tree(sub, item)

    def _rb_add_playlist_to_tree(self, pl: RbPlaylist, header_item, parent_item=None):
        text = f"{pl.name} ({len(pl.tracks)})"
        item = QTreeWidgetItem()
        item.setText(0, text)
        item.setData(0, Qt.ItemDataRole.UserRole, pl)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(0, Qt.CheckState.Unchecked)

        if parent_item:
            parent_item.addChild(item)
        else:
            header_item.addChild(item)

    def _rb_add_folder_to_tree(self, folder: RbFolder, normal_header, intelligent_header, parent_item=None):
        parent_widget = parent_item if parent_item else normal_header

        folder_item = QTreeWidgetItem(parent_widget)
        folder_item.setText(0, f"📁 {folder.name}")
        folder_item.setFlags(folder_item.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
        folder_item.setCheckState(0, Qt.CheckState.Unchecked)
        folder_item.setExpanded(True)

        for sub in folder.subitems:
            if isinstance(sub, RbFolder):
                self._rb_add_folder_to_tree(sub, normal_header, intelligent_header, folder_item)
            elif isinstance(sub, RbIntelligentPlaylist):
                self._rb_add_playlist_to_tree(sub, intelligent_header, folder_item)
            elif isinstance(sub, RbPlaylist):
                self._rb_add_playlist_to_tree(sub, normal_header, folder_item)

    def update_playlist_list(self):
        """Update the playlist tree using RbPlaylist/SeratoCrate"""
        self.playlist_tree.clear()

        # Section headers
        normal_label = "Playlists" if self.source_type.lower() == 'rekordbox' else "Crates"
        intelligent_label = "Intelligent Playlists" if self.source_type.lower() == 'rekordbox' else "Smart Crates"

        normal_header = QTreeWidgetItem(self.playlist_tree)
        normal_header.setText(0, normal_label)
        normal_header.setFlags(normal_header.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
        normal_header.setCheckState(0, Qt.CheckState.Unchecked)

        intelligent_header = QTreeWidgetItem(self.playlist_tree)
        intelligent_header.setText(0, intelligent_label)
        intelligent_header.setFlags(intelligent_header.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
        intelligent_header.setCheckState(0, Qt.CheckState.Unchecked)

        if self.source_type.lower() == 'rekordbox':
            # Build lookup table so parent/child attachment works in any order
            self._playlist_by_id = {pl.id: pl for pl in self.playlists}

            # Build the tree (attach children to parents)
            for pl in self.playlists:
                if pl.parentId != "root" and pl.parentId in self._playlist_by_id:
                    parent = self._playlist_by_id[pl.parentId]
                    # Only folders can hold subitems
                    if isinstance(parent, RbFolder):
                        parent.add_subitem(pl)

            # Display root-level folders & playlists
            for pl in self.playlists:
                if pl.parentId == "root":   # root item → attach to header
                    if isinstance(pl, RbFolder):
                        self._rb_add_folder_to_tree(pl, normal_header, intelligent_header)
                    elif isinstance(pl, RbIntelligentPlaylist):
                        self._rb_add_playlist_to_tree(pl, intelligent_header)
                    elif isinstance(pl, RbPlaylist):
                        self._rb_add_playlist_to_tree(pl, normal_header)

            normal_header.setExpanded(True)
            intelligent_header.setExpanded(True)

            self.normal_header = normal_header
            self.intelligent_header = intelligent_header
        elif self.source_type.lower() == 'serato':
            header = QTreeWidgetItem(self.playlist_tree)
            header.setText(0, "Serato Crates")
            header.setFlags(header.flags() | Qt.ItemFlag.ItemIsAutoTristate | Qt.ItemFlag.ItemIsUserCheckable)
            header.setCheckState(0, Qt.CheckState.Unchecked)
            header.setExpanded(True)

            for crate in self.playlists:   # self.playlists now contains top-level SeratoCrate objects
                self._add_serato_crate_to_tree(crate, header)
        else:
            print("UNAVAILABLE OPTION SELECTED???")


    def on_playlist_selected(self, item, column):
        """Handle playlist selection"""

        # Click on section header: expand/collapse
        if item.parent() is None and column != 0:
            item.setExpanded(not item.isExpanded())
            return
        
        obj = item.data(0, Qt.ItemDataRole.UserRole)

        # Nothing stored = header/folder with no playlist object
        if obj is None:
            return

        # Rekordbox Intelligent or normal playlist
        if isinstance(obj, RbPlaylist):
            print(f"Playlist selected: {obj.name}")
            self.current_playlist = obj
            self.load_tracks()
            return

        # Rekordbox Folders
        if isinstance(obj, RbFolder) and column != 0:
            item.setExpanded(not item.isExpanded())

        # Serato Crates
        if isinstance(obj, SeratoCrate):
            self.current_playlist = obj
            self.load_tracks()
            return


    def on_item_changed(self, item, column):
        """Handle checkbox state changes - Qt's AutoTristate handles most of the logic automatically"""
        # With ItemIsAutoTristate, Qt automatically:
        # - Updates all children when parent checkbox changes
        # - Updates parent to checked/unchecked/indeterminate based on children states
        # This handler is mainly for any additional logic we might need
        if column != 0:
            return
    
    def load_tracks(self):
        """Load tracks from selected playlist"""
        if not self.current_playlist:
            print("No playlist selected")
            return
        
        # Clear current tracks
        self.track_table.setRowCount(0)
        
        # Load tracks asynchronously (in PyQt6, we use QTimer for async operations)
        QTimer.singleShot(100, self._load_tracks_async)
    
    def _load_tracks_async(self):
        try:
            if not isinstance(self.current_playlist, (RbPlaylist, SeratoCrate)):
                print("Error: No preloaded tracks found")
                msg_box = QMessageBox(self)
                msg_box.setWindowTitle("Error")
                msg_box.setText("No tracks found in this playlist")
                msg_box.setIcon(QMessageBox.Icon.Warning)
                self._style_message_box(msg_box)
                msg_box.exec()
                return
            
            tracks = self.current_playlist.tracks
            print(f"Using preloaded tracks: {len(tracks)} tracks")

            self._original_track_order = list(tracks)
            self._last_sorted_column = -1
            self._sort_order = Qt.SortOrder.AscendingOrder

            self.track_table.setRowCount(len(tracks))

            for row, track in enumerate(tracks):
                item = QTableWidgetItem()
                item.setData(Qt.ItemDataRole.DisplayRole, track.seq)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.track_table.setItem(row, 0, item)

                values = [
                    track.title,
                    track.artist,
                    self._format_time_value(track.length),
                    str(track.bpm),
                    convert_key(self._parse_key_value(track.key), self.key_format),
                    self._format_rating_value(track.rating),
                    track.genre,
                    str(track.filetype),
                    str(track.year),
                    track.comments or ''
                ]

                for col, value in enumerate(values, start=1):
                    item = QTableWidgetItem(value)
                    item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                    self.track_table.setItem(row, col, item)

            print(f"Displayed {len(tracks)} tracks in table")

        except Exception as e:
            print(f"Error loading tracks: {e}")
            import traceback
            traceback.print_exc()
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Error")
            msg_box.setText(f"Error loading tracks: {str(e)}")
            msg_box.setIcon(QMessageBox.Icon.Critical)
            self._style_message_box(msg_box)
            msg_box.exec()
    
    def on_header_clicked(self, logical_index):
        """Handle header column click for three-state sorting (ascending/descending/reset)"""
        header = self.track_table.horizontalHeader()
        
        # If clicking the same column, cycle through states
        if logical_index == self._last_sorted_column:
            if self._sort_order == Qt.SortOrder.AscendingOrder:
                # Switch to descending
                self._sort_order = Qt.SortOrder.DescendingOrder
                self.track_table.sortItems(logical_index, self._sort_order)
                header.setSortIndicator(logical_index, self._sort_order)
            elif self._sort_order == Qt.SortOrder.DescendingOrder:
                # Reset to original order
                self._reset_to_original_order()
                header.setSortIndicator(-1, Qt.SortOrder.AscendingOrder)
                self._last_sorted_column = -1
        else:
            # New column - start with ascending
            self._last_sorted_column = logical_index
            self._sort_order = Qt.SortOrder.AscendingOrder
            self.track_table.sortItems(logical_index, self._sort_order)
            header.setSortIndicator(logical_index, self._sort_order)
    
    def _reset_to_original_order(self):
        if not self._original_track_order or not self.current_playlist:
            return

        tracks = self.current_playlist.tracks
        self.track_table.setRowCount(0)
        self.track_table.setRowCount(len(self._original_track_order))

        for row, track in enumerate(self._original_track_order):
            item = QTableWidgetItem()
            item.setData(Qt.ItemDataRole.DisplayRole, track.seq)
            item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
            self.track_table.setItem(row, 0, item)

            values = [
                track.title,
                track.artist,
                self._format_time_value(track.length),
                str(track.bpm),
                convert_key(self._parse_key_value(track.key), self.key_format),
                self._format_rating_value(track.rating),
                track.genre,
                str(track.filetype),
                str(track.year),
                track.comments or ''
            ]

            for col, value in enumerate(values, start=1):
                item = QTableWidgetItem(value)
                item.setFlags(Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable)
                self.track_table.setItem(row, col, item)
    
    def on_back(self):
        """Go back to selection screen"""
        if self.parent_window:
            self.parent_window.show_selection_screen()
    
    def get_checked_playlists(self):
        """Get all playlists that are checked"""
        checked_playlists = []
        
        # Iterate through all items in the tree
        iterator = QTreeWidgetItemIterator(self.playlist_tree)
        while iterator.value():
            item = iterator.value()
            # Only check playlist items (items with UserRole data, not folders or section headers)
            if item.checkState(0) == Qt.CheckState.Checked:
                playlist_data = item.data(0, Qt.ItemDataRole.UserRole)
                if playlist_data:  # Has UserRole data means it's a playlist, not a folder
                    checked_playlists.append(playlist_data)
            iterator += 1
        
        return checked_playlists
    
    def on_settings(self):
        """Open settings dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings")
        dialog.setMinimumWidth(300)
        
        layout = QVBoxLayout()
        
        # Key format selection with toggle button
        key_format_label = QLabel("Key Display Format:")
        key_format_label.setStyleSheet(f"color: {Colors.qss_color(Colors.FOREGROUND)}; font-weight: bold;")
        layout.addWidget(key_format_label)
        
        # Toggle button for key format
        # Unchecked = Classic, Checked = Camelot
        toggle_btn = QPushButton()
        toggle_btn.setCheckable(True)
        
        # Set initial state based on current format
        if self.key_format == 'camelot':
            toggle_btn.setChecked(True)
            toggle_btn.setText("Camelot Wheel (8A, 12B)")
        else:
            toggle_btn.setChecked(False)
            toggle_btn.setText("Classic (Am, C, F#m)")
        
        # Update text when toggled
        def update_toggle_text(checked):
            if checked:
                toggle_btn.setText("Camelot Wheel (8A, 12B)")
            else:
                toggle_btn.setText("Classic (Am, C, F#m)")
        
        toggle_btn.toggled.connect(update_toggle_text)
        
        toggle_btn.setMinimumHeight(50)
        toggle_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.qss_color(Colors.BACKGROUND_SECONDARY)};
                color: {Colors.qss_color(Colors.FOREGROUND)};
                border: 2px solid {Colors.qss_color(Colors.BACKGROUND_TERTIARY)};
                border-radius: 5px;
                padding: 10px;
                font-size: 14px;
                font-weight: bold;
            }}
            QPushButton:checked {{
                background-color: {Colors.qss_color(Colors.PURPLE)};
                color: {Colors.qss_color(Colors.BACKGROUND)};
                border: 2px solid {Colors.qss_color(Colors.PURPLE)};
            }}
            QPushButton:hover {{
                background-color: {Colors.qss_color(Colors.SELECTION)};
                border: 2px solid {Colors.qss_color(Colors.CYAN)};
            }}
            QPushButton:checked:hover {{
                background-color: {Colors.qss_color(Colors.PINK)};
                border: 2px solid {Colors.qss_color(Colors.PINK)};
            }}
        """)
        
        layout.addWidget(toggle_btn)
        layout.addSpacing(20)
        
        # Close button
        close_btn = QPushButton('Close')
        close_btn.setMinimumHeight(40)
        close_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {Colors.qss_color(Colors.PURPLE)};
                color: {Colors.qss_color(Colors.BACKGROUND)};
                border: none;
                border-radius: 5px;
                padding: 8px 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {Colors.qss_color(Colors.PINK)};
            }}
        """)
        close_btn.clicked.connect(dialog.accept)
        layout.addWidget(close_btn)
        
        dialog.setLayout(layout)
        
        # Set dialog background
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.qss_color(Colors.BACKGROUND)};
            }}
        """)
        
        if dialog.exec() == QDialog.DialogCode.Accepted:
            # Update key format preference based on toggle state
            new_format = 'camelot' if toggle_btn.isChecked() else 'classic'
            
            if new_format != self.key_format:
                self.key_format = new_format
                # Reload tracks to update key display
                if self.current_playlist:
                    self.load_tracks()
    
    def _create_progress_dialog(self, title: str, total_items: int):
        """Create a progress dialog for conversion"""
        dialog = QDialog(self)
        dialog.setWindowTitle(title)
        dialog.setModal(True)
        dialog.setMinimumWidth(400)
        dialog.setMinimumHeight(200)
        
        layout = QVBoxLayout()
        
        # Playlist progress label
        playlist_label = QLabel()
        playlist_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        playlist_label.setStyleSheet(f"""
            color: {Colors.qss_color(Colors.FOREGROUND)};
            font-size: 14px;
            font-weight: bold;
            padding: 10px;
        """)
        layout.addWidget(playlist_label)
        
        # Track progress label
        track_label = QLabel()
        track_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        track_label.setStyleSheet(f"""
            color: {Colors.qss_color(Colors.FOREGROUND)};
            font-size: 12px;
            padding: 5px;
        """)
        layout.addWidget(track_label)
        
        # Overall progress bar
        overall_progress = QProgressBar()
        overall_progress.setMinimum(0)
        overall_progress.setMaximum(total_items)
        overall_progress.setValue(0)
        overall_progress.setStyleSheet(f"""
            QProgressBar {{
                border: 2px solid {Colors.qss_color(Colors.BACKGROUND_TERTIARY)};
                border-radius: 5px;
                text-align: center;
                background-color: {Colors.qss_color(Colors.BACKGROUND_SECONDARY)};
                color: {Colors.qss_color(Colors.FOREGROUND)};
                height: 25px;
            }}
            QProgressBar::chunk {{
                background-color: {Colors.qss_color(Colors.GREEN)};
                border-radius: 3px;
            }}
        """)
        layout.addWidget(overall_progress)
        
        # Store references for updates
        dialog._playlist_label = playlist_label
        dialog._track_label = track_label
        dialog._overall_progress = overall_progress
        dialog._total_items = total_items
        
        # Update methods
        def update_playlist_progress(current, total, name):
            playlist_label.setText(f"Converting {current}/{total}: {name}")
            dialog._playlist_label = playlist_label
        
        def update_track_progress(name, current, total):
            track_label.setText(f"Processing track {current}/{total}")
            dialog._track_label = track_label
        
        def set_overall_progress(current, total):
            overall_progress.setValue(current)
            overall_progress.setFormat(f"{current}/{total}")
        
        dialog.update_playlist_progress = update_playlist_progress
        dialog.update_track_progress = update_track_progress
        dialog.set_overall_progress = set_overall_progress
        
        # Dialog styling
        dialog.setStyleSheet(f"""
            QDialog {{
                background-color: {Colors.qss_color(Colors.BACKGROUND)};
            }}
        """)
        
        dialog.setLayout(layout)
        
        return dialog
    
    def on_convert(self):
        """Handle conversion button"""
        checked_playlists = self.get_checked_playlists()
        
        if not checked_playlists:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("No Selection")
            msg_box.setText("Please select at least one playlist to convert by checking the boxes.")
            msg_box.setIcon(QMessageBox.Icon.Warning)
            self._style_message_box(msg_box)
            msg_box.exec()
            return
        
        # Show confirmation dialog
        playlist_names = [p.name for p in checked_playlists]
        
        # Determine conversion direction and message
        if self.source_type.lower() == 'rekordbox' and self.target_type.lower() == 'serato':
            confirm_msg = f"Convert {len(checked_playlists)} playlist(s) to Serato crates?\n\n{', '.join(playlist_names[:5])}{'...' if len(playlist_names) > 5 else ''}"
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Confirm Conversion")
            msg_box.setText(confirm_msg)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)
            msg_box.setIcon(QMessageBox.Icon.Question)
            self._style_message_box(msg_box)
            reply = msg_box.exec()
            if reply != QMessageBox.StandardButton.Yes:
                return
            self._convert_rekordbox_to_serato(checked_playlists)
        elif self.source_type.lower() == 'serato' and self.target_type.lower() == 'rekordbox':
            confirm_msg = f"Convert {len(checked_playlists)} crate(s) to Rekordbox playlists?\n\n{', '.join(playlist_names[:5])}{'...' if len(playlist_names) > 5 else ''}"
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Confirm Conversion")
            msg_box.setText(confirm_msg)
            msg_box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            msg_box.setDefaultButton(QMessageBox.StandardButton.No)
            msg_box.setIcon(QMessageBox.Icon.Question)
            self._style_message_box(msg_box)
            reply = msg_box.exec()
            if reply != QMessageBox.StandardButton.Yes:
                return
            self._convert_serato_to_rekordbox(checked_playlists)
        else:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Conversion")
            msg_box.setText(f"Conversion from {self.source_type} to {self.target_type} is not yet supported.\n\nCurrently supported:\n• Rekordbox → Serato\n• Serato → Rekordbox")
            msg_box.setIcon(QMessageBox.Icon.Information)
            self._style_message_box(msg_box)
            msg_box.exec()
            return
    
    def _convert_rekordbox_to_serato(self, playlists):
        """Convert Rekordbox playlists to Serato crates"""
        from utils.converter_utils import convert_rekordbox_playlist_to_serato, detect_serato_directory
        
        # Detect Serato directory
        serato_dir = detect_serato_directory()
        if not serato_dir:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Serato Directory Not Found")
            msg_box.setText("Could not find Serato crate directory.\n\nPlease set the SERATO_CRATE_DIR environment variable or ensure Serato is installed.")
            msg_box.setIcon(QMessageBox.Icon.Critical)
            self._style_message_box(msg_box)
            msg_box.exec()
            return
        
        # Create progress dialog
        progress_dialog = self._create_progress_dialog("Converting Playlists", len(playlists))
        progress_dialog.show()
        
        # Convert each playlist
        results = []
        success_count = 0
        fail_count = 0
        
        try:
            for idx, playlist in enumerate(playlists):
                playlist_name = playlist.name
                
                # Update playlist progress
                progress_dialog.update_playlist_progress(idx + 1, len(playlists), playlist_name)
                
                # Convert playlist
                track_progress_callback = self._create_track_progress_callback(progress_dialog)
                result = convert_rekordbox_playlist_to_serato(
                    playlist,
                    serato_dir=serato_dir,
                    progress_callback=track_progress_callback
                )
                
                results.append(result)
                
                if result['success']:
                    success_count += 1
                    print(f"✓ {result['message']}")
                else:
                    fail_count += 1
                    print(f"✗ {result['message']}")
                
                # Update overall progress bar
                progress_dialog.set_overall_progress(idx + 1, len(playlists))
        finally:
            progress_dialog.close()
        
        # Show results
        self._show_conversion_results(results, success_count, fail_count, 'crate_name', 'serato')
    
    def _convert_serato_to_rekordbox(self, crates):
        """Convert Serato crates to Rekordbox playlists"""
        from utils.converter_utils import convert_serato_crate_to_rekordbox
        from pyrekordbox import Rekordbox6Database
        
        # Open database connection (reuse for all conversions)
        try:
            db = Rekordbox6Database()
        except Exception as e:
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Database Error")
            msg_box.setText(f"Could not open Rekordbox database.\n\nError: {str(e)}\n\nPlease ensure Rekordbox is installed and the database is accessible.")
            msg_box.setIcon(QMessageBox.Icon.Critical)
            self._style_message_box(msg_box)
            msg_box.exec()
            return
        
        # Create progress dialog
        progress_dialog = self._create_progress_dialog("Converting Crates", len(crates))
        progress_dialog.show()
        
        # Convert each crate
        results = []
        success_count = 0
        fail_count = 0
        
        try:
            for idx, crate in enumerate(crates):
                crate_name = crate.name
                
                # Update crate progress
                progress_dialog.update_playlist_progress(idx + 1, len(crates), crate_name)
                
                # Convert crate
                track_progress_callback = self._create_track_progress_callback(progress_dialog)
                result = convert_serato_crate_to_rekordbox(
                    crate,
                    db=db,  # Reuse same database connection
                    progress_callback=track_progress_callback
                )
                
                results.append(result)
                
                if result['success']:
                    success_count += 1
                    print(f"✓ {result['message']}")
                else:
                    fail_count += 1
                    print(f"✗ {result['message']}")
                
                # Update overall progress bar
                progress_dialog.set_overall_progress(idx + 1, len(crates))
        finally:
            progress_dialog.close()
            # Close database connection
            try:
                db.close()
            except:
                pass
        
        # Show results
        self._show_conversion_results(results, success_count, fail_count, 'playlist_name', 'rekordbox')

