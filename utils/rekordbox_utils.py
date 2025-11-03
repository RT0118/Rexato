"""
Utilities for working with Rekordbox data
"""

import os
from typing import List, Dict, Optional


def _open_database():
    """Open a new database connection"""
    from pyrekordbox import Rekordbox6Database
    
    # Open database normally without suppression
    db = Rekordbox6Database()
    
    return db


def load_rekordbox_playlists(progress_callback=None):
    """Load playlists from Rekordbox database"""
    db = None
    try:
        # Open database once at the start
        db = _open_database()
        
        playlists_raw = db.get_playlist()
        
        # Filter playlists first
        filtered_playlists = []
        for playlist in playlists_raw:
            playlist_name = getattr(playlist, 'Name', getattr(playlist, 'name', 'Unknown'))
            # Include both regular playlists and smart playlists, but not folders
            is_regular_playlist = hasattr(playlist, 'is_playlist') and playlist.is_playlist
            is_smart = hasattr(playlist, 'is_smart_playlist') and playlist.is_smart_playlist
            
            if is_regular_playlist or is_smart:
                filtered_playlists.append((playlist, playlist_name, is_smart))
        
        if progress_callback:
            progress_callback(status="", progress=f"Found {len(filtered_playlists)} playlists", debug="")
        
        # Build folder hierarchy
        folder_map = {}  # folder_id -> folder_info
        playlists_raw_all = db.get_playlist()
        for pl in playlists_raw_all:
            if hasattr(pl, 'is_folder') and pl.is_folder:
                folder_name = getattr(pl, 'Name', getattr(pl, 'name', 'Unknown'))
                folder_id = getattr(pl, 'ID', None)
                parent_id = getattr(pl, 'ParentID', None)
                folder_map[folder_id] = {
                    'name': folder_name,
                    'id': folder_id,
                    'parent_id': parent_id,
                    'path': []  # Will build full path later
                }
        
        # Build folder paths
        def get_folder_path(folder_id, visited=None):
            """Get the full path from root to this folder"""
            if visited is None:
                visited = set()
            if folder_id in visited or folder_id not in folder_map:
                return []
            visited.add(folder_id)
            folder = folder_map[folder_id]
            parent_id = folder['parent_id']
            if parent_id and parent_id in folder_map:
                parent_path = get_folder_path(parent_id, visited)
                return parent_path + [folder['name']]
            return [folder['name']]
        
        # Build full paths for all folders
        for folder_id in folder_map:
            folder_map[folder_id]['path'] = get_folder_path(folder_id)
        
        playlists = []
        for idx, (playlist, playlist_name, is_smart) in enumerate(filtered_playlists):
            if progress_callback:
                progress_callback(
                    status="",
                    progress=f"Loading playlist {idx + 1}/{len(filtered_playlists)}: {playlist_name}",
                    debug=""
                )
            
            # Get track count and preload tracks for this playlist
            try:
                contents = db.get_playlist_contents(playlist).all()
                track_count = len(contents)
            except Exception as e:
                print(f"Error getting track count for playlist {playlist_name}: {e}")
                track_count = 0
            
            # Preload track data to avoid reloading when selected
            tracks = get_rekordbox_tracks(db, playlist)
            
            # Get parent folder info
            parent_id = getattr(playlist, 'ParentID', None)
            folder_path = []
            if parent_id and parent_id in folder_map:
                folder_path = folder_map[parent_id]['path']
            
            playlists.append({
                'name': playlist_name,
                'object': playlist,
                'type': 'rekordbox',
                'track_count': track_count,
                'is_smart': is_smart,
                'tracks': tracks,  # Preload tracks
                'folder_path': folder_path,  # List of folder names from root to parent
                'parent_id': parent_id
            })
        
        return playlists
    except Exception as e:
        print(f"Error loading Rekordbox playlists: {e}")
        import traceback
        traceback.print_exc()
        return []
    finally:
        # Close database connection when done
        if db is not None:
            try:
                db.close()
            except:
                pass


def get_rekordbox_tracks(db, playlist):
    """Extract track information from Rekordbox playlist
    
    Args:
        db: The Rekordbox6Database instance
        playlist: The playlist object to extract tracks from
    """
    from .metadata_utils import get_artist, get_genre, get_file_extension, format_time
    
    tracks = []
    
    try:
        # Get contents from playlist using the database method
        # This properly handles the relationship between DjmdPlaylist -> DjmdSongPlaylist -> DjmdContent
        # and also handles smart playlists
        try:
            contents = db.get_playlist_contents(playlist).all()
        except ValueError as e:
            # Playlist might be a folder
            print(f"Cannot get contents from playlist (might be folder): {e}")
            return []
        
        # Get playlist name for debug output
        playlist_name = getattr(playlist, 'Name', getattr(playlist, 'name', 'Unknown'))
        print(f"Found {len(contents)} tracks in playlist '{playlist_name}'")
        
        for content in contents:
            try:
                # Extract metadata - pyrekordbox uses direct attribute access
                # For linked fields (Artist, Genre, Key), we need to access the related objects
                title = getattr(content, 'Title', None) or 'Unknown'
                
                # Get artist - may be a linked object
                artist_name = get_artist(content)
                
                # Get time from Length field
                # Rekordbox stores Length in SECONDS in the database (not milliseconds)
                length_value = None
                
                # Try to get Length attribute - handle both direct access and potential None values
                try:
                    length_value = getattr(content, 'Length', None)
                except AttributeError:
                    # Try lowercase variant
                    try:
                        length_value = getattr(content, 'length', None)
                    except AttributeError:
                        pass
                
                # Length is already in seconds, no conversion needed
                if length_value is None:
                    time_seconds = 0
                else:
                    try:
                        length_int = int(length_value)
                        if length_int > 0:
                            # Length is already in seconds
                            time_seconds = float(length_int)
                        else:
                            time_seconds = 0
                    except (ValueError, TypeError) as e:
                        # If conversion fails, log for debugging
                        if len(tracks) < 3:
                            print(f"Warning: Could not convert Length value '{length_value}' to integer: {e}")
                        time_seconds = 0
                
                # Get BPM - format to nearest integer
                from .metadata_utils import format_bpm
                bpm = getattr(content, 'BPM', None)
                bpm_str = format_bpm(bpm)
                
                # Get key - might be linked object via KeyID
                key_value = 'N/A'
                try:
                    if hasattr(content, 'Key') and content.Key:
                        key_obj = content.Key
                        key_value = getattr(key_obj, 'Name', getattr(key_obj, 'name', str(key_obj) if key_obj else 'N/A'))
                    elif hasattr(content, 'KeyID') and content.KeyID:
                        # Key is stored as ID, would need to query database to get name
                        key_value = 'N/A'
                    else:
                        key_value = 'N/A'
                except:
                    key_value = 'N/A'
                
                # Get rating
                rating = getattr(content, 'Rating', None)
                rating_str = str(rating) if rating is not None else '0'
                
                # Get genre
                genre_name = get_genre(content)
                
                # Get file location and type
                folder_path = getattr(content, 'FolderPath', None) or ''
                file_name = getattr(content, 'FileNameL', None) or ''
                # FolderPath should contain the full path, but if not, try to construct it
                file_path = folder_path if folder_path and os.path.exists(folder_path) else ''
                if not file_path and folder_path and file_name:
                    # Try to join them
                    file_path = os.path.join(folder_path, file_name) if folder_path else file_name
                
                file_type_id = getattr(content, 'FileType', None)
                # FileType is an integer, map common values according to pyrekordbox FileType enum:
                # MP3 = 1, M4A = 4, FLAC = 5, WAV = 11, AIF/AIFF = 12
                file_type_map = {1: 'MP3', 4: 'M4A', 5: 'FLAC', 11: 'WAV', 12: 'AIF'}
                location = folder_path or file_name or ''
                filetype = file_type_map.get(file_type_id, 'N/A') if file_type_id is not None else get_file_extension(location)
                
                # Get year
                year = getattr(content, 'ReleaseYear', None)
                year_str = str(year) if year is not None else 'N/A'
                
                # Get comments
                comments = getattr(content, 'Commnt', None) or getattr(content, 'Comment', None) or ''
                
                track_info = {
                    'title': title,
                    'artist': artist_name,
                    'time': format_time(time_seconds),
                    'bpm': bpm_str,
                    'key': key_value,
                    'rating': rating_str,
                    'genre': genre_name,
                    'filetype': filetype,
                    'year': year_str,
                    'comments': str(comments) if comments else '',
                    'path': file_path,  # Include file path for conversion
                    'content_id': getattr(content, 'ID', None),  # Store content ID for potential lookup
                }
                tracks.append(track_info)
                
            except Exception as e:
                print(f"Error processing track: {e}")
                import traceback
                traceback.print_exc()
                continue
                
    except Exception as e:
        print(f"Error getting tracks: {e}")
        import traceback
        traceback.print_exc()
    
    return tracks
