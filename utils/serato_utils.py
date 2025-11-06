"""
Utilities for working with Serato data
"""

import os
import platform
from pathlib import Path
from typing import List, Dict
from .metadata_utils import get_audio_metadata, get_basic_metadata

try:
    from serato_tools.crate import Crate
    from serato_tools.smart_crate import SmartCrate
    from serato_tools.utils import SERATO_DIR
except ImportError as e:
    raise ImportError(
        "serato-tools is required but not installed. "
        "Install it with: pip install serato-tools"
    ) from e


def _locate_serato_dirs() -> List[str]:
    system = platform.system()
    serato_dirs = [SERATO_DIR]
    if system == "Windows":
        # handle windows search
        from string import ascii_uppercase
        for drive_letter in ascii_uppercase:
            path = os.path.join(f"{drive_letter}:", "_Serato_")
            if os.path.exists(path):
                serato_dirs.append(path)
    elif system == "darwin":
        try:
            for drive in os.listdir("/Volumes"):
                path = os.path.join("/Volumes", drive, "_Serato_")
                if os.path.isdir(path):
                    serato_dirs.append(path)
        except Exception as e:
            print(f"Unable to look for serato folders: {e}")
    else:
        print(f"Non supported system!")
    return serato_dirs


def _get_serato_subcrates_dir() -> str:
    """Get the Serato Subcrates directory path"""
    return os.path.join(SERATO_DIR, Crate.DIR)


def _extract_folder_path_from_crate_path(crate_path: str) -> List[str]:
    """
    Extract folder path from crate file path using %% separator format
    
    Serato uses %% separator format for subcrates:
    - Format: Parent%%Child.crate -> folder_path = ['Parent']
    - Format: Folder1%%Folder2%%Crate.crate -> folder_path = ['Folder1', 'Folder2']
    
    Args:
        crate_path: Full path to the crate file
    
    Returns:
        List of folder names from root to parent (empty list if at root or no %% separator)
    """
    try:
        # Get filename without extension
        filename = Path(crate_path).stem
        
        # Check if filename contains %% separator (Serato subcrate naming)
        if '%%' in filename:
            # Split by %% separator
            # Format: Parent%%Child.crate -> folder_path = ['Parent']
            # Format: Folder1%%Folder2%%Crate.crate -> folder_path = ['Folder1', 'Folder2']
            parts = filename.split('%%')
            if len(parts) > 1:
                # All parts except the last one are folder names
                # The last part is the actual crate name
                folder_path = parts[:-1]
                return [folder for folder in folder_path if folder]
        
        # No %% separator means crate is at root level
        return []
    except Exception as e:
        print(f"Error extracting folder path from {crate_path}: {e}")
        return []


def _load_tracks_from_paths(track_paths):
    """Helper to load track metadata from file paths"""
    tracks = []
    for track_path in track_paths:
        if os.path.exists(track_path):
            track_info = get_audio_metadata(track_path)
            tracks.append(track_info)
        else:
            # Track path might be relative or stored differently
            track_info = get_basic_metadata(track_path)
            tracks.append(track_info)
    return tracks


def _extract_crate_name(crate_path):
    """Extract and process crate name, handling %% format"""
    crate_name = Path(crate_path).stem
    # If name contains %%, use only the last part as the crate name
    # Example: "my folder%%Afro%%crate 2%%wild" -> "wild"
    if '%%' in crate_name:
        parts = crate_name.split('%%')
        # The last part is always the actual crate name
        crate_name = parts[-1] if parts else crate_name
    return crate_name


def load_serato_crates(progress_callback=None) -> List[Dict]:
    """Load crates from Serato using serato_tools"""
    playlists = []
    
    # Load regular crates
    try:
        if progress_callback:
            progress_callback(status="", progress="Loading crates...", debug="")
        
        # Get all files and filter by .crate extension
        all_files = Crate.get_serato_crate_files()
        crate_paths = [f for f in all_files if f.endswith(Crate.EXTENSION)]
        
        if progress_callback:
            progress_callback(status="", progress=f"Found {len(crate_paths)} crates", debug="")
        
        for idx, crate_path in enumerate(crate_paths):
            try:
                if progress_callback:
                    progress_callback(
                        status="",
                        progress=f"Loading crate {idx + 1}/{len(crate_paths)}: {Path(crate_path).stem}",
                        debug=""
                    )
                
                # Load crate using serato_tools
                crate = Crate(crate_path)
                track_paths = crate.get_track_paths(include_drive=True)
                tracks = _load_tracks_from_paths(track_paths)
                
                # Extract folder path from %% format and crate name
                folder_path = _extract_folder_path_from_crate_path(crate_path)
                crate_name = _extract_crate_name(crate_path)
                
                playlists.append({
                    'name': crate_name,
                    'path': crate_path,
                    'type': 'serato',
                    'track_count': len(tracks),
                    'tracks': tracks,
                    'is_smart': False,
                    'folder_path': folder_path
                })
            except Exception as e:
                print(f"Error loading crate {crate_path}: {e}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"Error listing crates: {e}")
        import traceback
        traceback.print_exc()
    
    # Load smart crates
    try:
        if progress_callback:
            progress_callback(status="", progress="Loading smart crates...", debug="")
        
        # Get all files and filter by .scrate extension
        all_files = SmartCrate.get_serato_crate_files()
        smart_crate_paths = [f for f in all_files if f.endswith(SmartCrate.EXTENSION)]
        
        if progress_callback:
            progress_callback(status="", progress=f"Found {len(smart_crate_paths)} smart crates", debug="")
        
        for idx, smart_crate_path in enumerate(smart_crate_paths):
            try:
                if progress_callback:
                    progress_callback(
                        status="",
                        progress=f"Loading smart crate {idx + 1}/{len(smart_crate_paths)}: {Path(smart_crate_path).stem}",
                        debug=""
                    )
                
                # Load smart crate using serato_tools
                smart_crate = SmartCrate(smart_crate_path)
                track_paths = smart_crate.get_track_paths(include_drive=True)
                tracks = _load_tracks_from_paths(track_paths)
                
                # Smart crates are always at root level, no folder structure
                crate_name = _extract_crate_name(smart_crate_path)
                
                playlists.append({
                    'name': crate_name,
                    'path': smart_crate_path,
                    'type': 'serato',
                    'track_count': len(tracks),
                    'tracks': tracks,
                    'is_smart': True,
                    'folder_path': []  # Smart crates have no folder structure
                })
            except Exception as e:
                print(f"Error loading smart crate {smart_crate_path}: {e}")
                import traceback
                traceback.print_exc()
        
    except Exception as e:
        print(f"Error listing smart crates: {e}")
        import traceback
        traceback.print_exc()
    
    return playlists
