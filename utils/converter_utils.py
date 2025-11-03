"""
Utilities for converting between Rekordbox and Serato formats
"""

import os
import sys
import copy
from pathlib import Path
from typing import List, Dict, Optional, Callable
from serato_tools.crate import Crate
from serato_tools.utils import SERATO_DIR
from pyrekordbox import Rekordbox6Database


def _normalize_path(track_path: str) -> str:
    """Normalize track path by removing file:// prefixes and normalizing separators"""
    if not track_path:
        return track_path
    normalized = track_path.replace('file://localhost/', '').replace('file:///', '')
    normalized = os.path.normpath(normalized)
    return normalized


def _extract_track_paths_from_tracks(tracks: List[Dict]) -> List[str]:
    """Extract and normalize file paths from track dictionaries"""
    track_paths = []
    for track in tracks:
        # Check various possible path fields
        track_path = (track.get('path') or track.get('location') or 
                     track.get('filepath') or track.get('file_path'))
        
        if track_path:
            track_path = _normalize_path(track_path)
            # Windows-specific: try backslash version if forward slash doesn't exist
            if sys.platform == "win32" and not os.path.exists(track_path):
                track_path_bs = track_path.replace('/', '\\')
                if os.path.exists(track_path_bs):
                    track_path = track_path_bs
            
            if os.path.exists(track_path):
                track_paths.append(track_path)
            else:
                print(f"Warning: Track file not found: {track_path}")
    
    return track_paths


def _find_rekordbox_content(db, track_path: str):
    """Find Rekordbox content entry for a given track path"""
    normalized_path = track_path.replace('\\', '/')
    
    # Try exact match first
    content = db.get_content(FolderPath=normalized_path).first()
    
    # Try with backslashes on Windows
    if not content and sys.platform == "win32":
        normalized_path_bs = track_path.replace('/', '\\')
        content = db.get_content(FolderPath=normalized_path_bs).first()
    
    # Case-insensitive search as fallback
    if not content:
        all_content = db.get_content()
        track_path_normalized = track_path.replace('\\', '/')
        for cont in all_content:
            if cont.FolderPath:
                rb_path = cont.FolderPath.replace('\\', '/')
                if rb_path.lower() == track_path_normalized.lower():
                    return cont
    
    return content


def detect_serato_directory() -> Optional[str]:
    """
    Detect Serato crate directory
    
    Returns:
        Path to Serato Subcrates directory or None if not found
    """
    # Check the SERATO_DIR from serato_tools first
    serato_crates_dir = os.path.join(SERATO_DIR, Crate.DIR)
    
    if os.path.exists(serato_crates_dir):
        return serato_crates_dir
    
    # Fallback: check common locations
    possible_paths = []
    
    if sys.platform == "win32":
        music_dir = os.path.join(os.environ.get("USERPROFILE", ""), "Music")
        possible_paths = [
            os.path.join(music_dir, "_Serato_", "Subcrates"),
            os.path.join(os.environ.get("USERPROFILE", ""), "Documents", "_Serato_", "Subcrates"),
        ]
    elif sys.platform == "darwin":
        music_dir = os.path.join(os.environ.get("HOME", ""), "Music")
        possible_paths = [
            os.path.join(music_dir, "_Serato_", "Subcrates"),
        ]
    else:
        music_dir = os.path.join(os.environ.get("HOME", ""), "Music")
        possible_paths = [
            os.path.join(music_dir, "_Serato_", "Subcrates"),
        ]
    
    # Also check environment variable
    env_dir = os.environ.get('SERATO_CRATE_DIR')
    if env_dir:
        possible_paths.insert(0, os.path.expanduser(env_dir))
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    return None


def convert_rekordbox_playlist_to_serato(playlist: Dict, serato_dir: Optional[str] = None, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> Dict:
    """
    Convert a Rekordbox playlist to a Serato crate
    
    Args:
        playlist: Playlist dictionary with 'name', 'tracks', etc.
        serato_dir: Directory to save Serato crates. If None, will try to detect.
    
    Returns:
        Dictionary with 'success', 'crate_name', 'track_count', 'message', 'error'
    """
    try:
        # Get Serato directory
        if not serato_dir:
            serato_dir = detect_serato_directory()
        
        if not serato_dir:
            return {
                'success': False,
                'crate_name': playlist.get('name', 'Unknown'),
                'track_count': 0,
                'message': 'Serato directory not found',
                'error': 'Could not find Serato crate directory. Please ensure Serato is installed or set SERATO_CRATE_DIR environment variable.'
            }
        
        # Ensure directory exists
        os.makedirs(serato_dir, exist_ok=True)
        
        # Get playlist name and tracks
        playlist_name = playlist.get('name', 'Unknown')
        tracks = playlist.get('tracks', [])
        
        # Get track file paths from tracks
        track_paths = _extract_track_paths_from_tracks(tracks)
        
        if not track_paths:
            return {
                'success': False,
                'crate_name': playlist_name,
                'track_count': 0,
                'message': 'No valid tracks found',
                'error': 'No tracks with valid file paths found in playlist.'
            }
        
        # Create crate name (sanitize for filesystem)
        crate_name = sanitize_crate_name(playlist_name)
        
        # Handle folder structure: If playlist is in a folder, use %% format for subcrates
        # Serato stores subcrates using "Parent%%Child.crate" format in the filename
        folder_path = playlist.get('folder_path', [])
        if folder_path and len(folder_path) > 0:
            # Use %% separator format: Parent%%Child.crate
            # For nested folders, join with %% (e.g., Folder1%%Folder2%%Playlist.crate)
            parent_name = '%%'.join([sanitize_crate_name(folder) for folder in folder_path])
            full_crate_name = f"{parent_name}%%{crate_name}"
            crate_path = os.path.join(serato_dir, f"{full_crate_name}.crate")
            print(f"Creating subcrate: {full_crate_name}.crate")
        else:
            # No folder - create crate directly in Subcrates directory
            crate_path = os.path.join(serato_dir, f"{crate_name}.crate")
            print(f"Creating crate: {crate_name}.crate")
        
        # If crate already exists, remove it first to avoid appending
        if os.path.exists(crate_path):
            try:
                os.remove(crate_path)
            except Exception as e:
                print(f"Warning: Could not remove existing crate {crate_path}: {e}")
        
        # Create new crate - pass the filepath to instantiate
        # Since we removed it if it existed, this will create a fresh crate with DEFAULT_ENTRIES
        crate = Crate(crate_path)
        
        # CRITICAL FIX: DEFAULT_ENTRIES is a shared class variable (a list), and when SeratoBinFile
        # does `self.entries = self.DEFAULT_ENTRIES`, all instances share the same list object.
        # We need to create a deep copy to avoid shared state between different crate instances.
        crate.entries = copy.deepcopy(crate.entries)
        
        # Add all tracks to crate
        added_count = 0
        total_tracks = len(track_paths)
        for track_idx, track_path in enumerate(track_paths):
            try:
                if progress_callback:
                    progress_callback(playlist_name, track_idx + 1, total_tracks)
                crate.add_track(track_path)
                added_count += 1
            except Exception as e:
                print(f"Warning: Could not add track {track_path}: {e}")
                continue
        
        if added_count == 0:
            return {
                'success': False,
                'crate_name': crate_name,
                'track_count': 0,
                'message': 'Failed to add tracks',
                'error': 'No tracks could be added to the crate.'
            }
        
        # Save the crate
        crate.save()
        
        return {
            'success': True,
            'crate_name': crate_name,
            'track_count': added_count,
            'message': f'Successfully created crate "{crate_name}.crate" with {added_count} tracks',
            'error': None,
            'crate_path': crate_path
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'crate_name': playlist.get('name', 'Unknown'),
            'track_count': 0,
            'message': f'Conversion failed: {str(e)}',
            'error': str(e)
        }


def sanitize_crate_name(name: str) -> str:
    """
    Sanitize crate name for filesystem
    
    Args:
        name: Original crate/playlist name
    
    Returns:
        Sanitized name safe for use as filename
    """
    # Replace invalid filesystem characters
    invalid_chars = ['<', '>', ':', '"', '/', '\\', '|', '?', '*']
    sanitized = name
    for char in invalid_chars:
        sanitized = sanitized.replace(char, '_')
    
    # Remove leading/trailing dots and spaces
    sanitized = sanitized.strip('. ')
    
    # Limit length (Windows has 255 char limit for paths, but keep it reasonable)
    if len(sanitized) > 100:
        sanitized = sanitized[:100]
    
    return sanitized or "Untitled"


def convert_serato_crate_to_rekordbox(crate: Dict, db: Optional[Rekordbox6Database] = None, progress_callback: Optional[Callable[[str, int, int], None]] = None) -> Dict:
    """
    Convert a Serato crate to a Rekordbox playlist
    
    Args:
        crate: Crate dictionary with 'name', 'tracks', etc.
        db: Rekordbox6Database instance. If None, will open a new connection.
    
    Returns:
        Dictionary with 'success', 'playlist_name', 'track_count', 'message', 'error'
    """
    db_should_close = False
    try:
        # Open database if not provided
        if db is None:
            db = Rekordbox6Database()
            db_should_close = True
        
        # Get crate name
        crate_name = crate.get('name', 'Unknown')
        
        # Get track paths directly from crate to maintain order
        # The crate's track_paths list maintains the order from the crate file
        crate_path = crate.get('path')
        if not crate_path:
            return {
                'success': False,
                'playlist_name': crate_name,
                'track_count': 0,
                'message': 'No crate path found',
                'error': 'Crate path not found in crate dictionary.'
            }
        
        # Load crate to get tracks in correct order
        serato_crate = Crate(crate_path)
        track_paths_raw = serato_crate.get_track_paths(include_drive=True)
        
        # Filter to only existing tracks and normalize paths
        track_paths = []
        for track_path in track_paths_raw:
            normalized_path = _normalize_path(track_path)
            if os.path.exists(normalized_path):
                track_paths.append(normalized_path)
            else:
                print(f"Warning: Track file not found: {normalized_path}")
        
        if not track_paths:
            return {
                'success': False,
                'playlist_name': crate_name,
                'track_count': 0,
                'message': 'No valid tracks found',
                'error': 'No tracks with valid file paths found in crate.'
            }
        
        # Get folder path from crate (if crate is in a folder/subcrate)
        folder_path = crate.get('folder_path', [])
        parent_folder = None
        
        # Create parent folders if they exist
        if folder_path and len(folder_path) > 0:
            current_parent = None
            for folder_name in folder_path:
                # Check if folder already exists at this level
                # Search for folders with this name and parent
                existing_folders = db.get_playlist()
                existing_folder = None
                for pl in existing_folders:
                    if (hasattr(pl, 'is_folder') and pl.is_folder and 
                        getattr(pl, 'Name', '') == folder_name):
                        # Check if parent matches
                        pl_parent_id = getattr(pl, 'ParentID', None)
                        if current_parent is None:
                            # Looking for root-level folder
                            if not pl_parent_id or pl_parent_id == 'root':
                                existing_folder = pl
                                break
                        else:
                            # Looking for folder with specific parent
                            if pl_parent_id == current_parent.ID:
                                existing_folder = pl
                                break
                
                if existing_folder:
                    # Use existing folder
                    current_parent = existing_folder
                    print(f"Using existing folder: {folder_name}")
                else:
                    # Create new folder
                    current_parent = db.create_playlist_folder(folder_name, parent=current_parent)
                    print(f"Created folder: {folder_name}")
                    db.commit()  # Commit folder creation
            
            parent_folder = current_parent
        
        # Check if playlist with same name already exists in the same folder
        playlist_name = crate_name
        existing_playlist = None
        
        # Search for existing playlist with same name and same parent
        playlists = db.get_playlist()
        for pl in playlists:
            if (hasattr(pl, 'is_playlist') and pl.is_playlist and 
                getattr(pl, 'Name', '') == playlist_name):
                pl_parent_id = getattr(pl, 'ParentID', None)
                if parent_folder is None:
                    # Looking for root-level playlist
                    if not pl_parent_id or pl_parent_id == 'root':
                        existing_playlist = pl
                        break
                else:
                    # Looking for playlist with specific parent
                    if pl_parent_id == parent_folder.ID:
                        existing_playlist = pl
                        break
        
        if existing_playlist:
            # Use existing playlist and clear existing tracks
            playlist = existing_playlist
            print(f"Replacing tracks in existing playlist: {playlist_name}")
            
            # Delete all existing songs from the playlist
            from pyrekordbox.db6 import tables as rb_tables
            existing_songs = db.query(rb_tables.DjmdSongPlaylist).filter_by(PlaylistID=playlist.ID).all()
            for song in existing_songs:
                db.session.delete(song)
            db.commit()  # Commit the deletions before adding new tracks
        else:
            # Create new playlist in the parent folder (if any)
            playlist = db.create_playlist(playlist_name, parent=parent_folder)
            print(f"Created playlist: {playlist_name}" + (f" in folder: {parent_folder.Name}" if parent_folder else ""))
        
        # Find content entries in Rekordbox database for each track path
        # Maintain track order by adding tracks sequentially with explicit track numbers
        # Use added_count + 1 to ensure continuous numbering even if some tracks fail to be added
        added_count = 0
        total_tracks = len(track_paths)
        for track_idx, track_path in enumerate(track_paths):
            if progress_callback:
                progress_callback(crate_name, track_idx + 1, total_tracks)
            try:
                content = _find_rekordbox_content(db, track_path)
                
                if content:
                    db.add_to_playlist(playlist, content, track_no=added_count + 1)
                    added_count += 1
                else:
                    print(f"Warning: Track not found in Rekordbox database: {track_path}")
            except Exception as e:
                print(f"Warning: Could not add track {track_path}: {e}")
                continue
        
        if added_count == 0:
            # Delete the empty playlist we created
            try:
                db.session.delete(playlist)
                db.commit()
            except:
                pass
            
            return {
                'success': False,
                'playlist_name': playlist_name,
                'track_count': 0,
                'message': 'Failed to add tracks',
                'error': 'No tracks from the crate were found in Rekordbox database.'
            }
        
        # Commit changes
        db.commit()
        
        return {
            'success': True,
            'playlist_name': playlist_name,
            'track_count': added_count,
            'message': f'Successfully created playlist "{playlist_name}" with {added_count} tracks',
            'error': None
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            'success': False,
            'playlist_name': crate.get('name', 'Unknown'),
            'track_count': 0,
            'message': f'Conversion failed: {str(e)}',
            'error': str(e)
        }
    finally:
        # Close database if we opened it
        if db_should_close and db is not None:
            try:
                db.close()
            except:
                pass
