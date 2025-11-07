"""
Utilities for working with Rekordbox data
"""

import os
from typing import List, Dict, Optional
from .rekordbox_classes import RbLibraryBase, RbFolder, RbIntelligentPlaylist, RbPlaylist, RbTrack, RbPlaylistAttribute, RbTrackFileType
from pyrekordbox import Rekordbox6Database
from .metadata_utils import get_artist, get_genre, get_album, format_bpm, format_time, get_key

def _open_database():
    """Open a new database connection"""
    
    # Open database normally without suppression
    db = Rekordbox6Database()
    
    return db

def _fill_intelligent_playlist_with_tracks(pl: RbPlaylist, playlist_track_info_raw):
    try:
        for idx, track_info in enumerate(playlist_track_info_raw):
            track = RbTrack(track_info.ID, idx, track_info.FileNameL, get_artist(track_info), track_info.Title, \
                get_album(track_info), get_genre(track_info), format_bpm(track_info.BPM), format_time(track_info.Length), \
                get_key(track_info), track_info.Rating, track_info.ReleaseYear, track_info.Commnt, track_info.FileType)
            pl.add_track(track)
    except Exception as e:
        print(e)


def _fill_playlist_with_tracks(db: Rekordbox6Database, pl: RbPlaylist, idx, total, progress_callback=None):
    if progress_callback:
        progress_callback(status="", progress=f"Loading playlist {idx}/{total}: {pl.name}", caller_function=f"_fill_playlist_with_tracks")
    print(f"Loading playlist {idx}/{total}: {pl.to_string()}")

    try:
        playlist_tracklisting_raw = db.get_playlist_songs(PlaylistID=pl.id).all()   # gives List[djmdSongPlaylist]
        playlist_track_info_raw = db.get_playlist_contents(pl.id).all()             # gives List[djmdContent]
        if len(playlist_tracklisting_raw) == 0:
            # likely an intelligent playlist
            _fill_intelligent_playlist_with_tracks(pl, playlist_track_info_raw)
        track_by_id = {x.ID: x for x in playlist_track_info_raw}
        for track_raw in playlist_tracklisting_raw:
            track_info = track_by_id.get(track_raw.ContentID)
            if track_info:
                track = RbTrack(track_info.ID, track_raw.TrackNo, track_info.FileNameL, get_artist(track_info), track_info.Title, get_album(track_info), \
                    get_genre(track_info), format_bpm(track_info.BPM), format_time(track_info.Length), get_key(track_info), track_info.Rating, track_info.ReleaseYear, track_info.Commnt, track_info.FileType)
                #print(f"Got: {track.to_string()}")
                pl.add_track(track)
            else:
                print(f"Unable to get info for track: {track_raw}")
    except Exception as e:
        print(e)

    if len(pl.tracks) < 1:
        print(f"Something went wrong: {pl.to_string()} {type(pl)}")
    
    print(f"Loaded {len(pl.tracks)} tracks")


def _fill_folder_with_playlists(folders: List[RbFolder], playlists: List[RbPlaylist]):
    folder_by_id = {x.id: x for x in folders}
    for playlist in playlists:
        parent_folder = folder_by_id.get(playlist.parentId)
        if parent_folder:
            parent_folder.add_subitem(playlist)
        else:
            print(f"Unable to find parent of: {playlist.to_string()}")
        
        
def _create_folder_structure(folders: List[RbFolder]) -> List[RbLibraryBase]:
    folder_by_id = {x.id: x for x in folders}
    roots = []
    for folder in folders:
        if folder.parentId == 'root':
            roots.append(folder)
        else:
            parent = folder_by_id.get(folder.parentId)
            if parent:
                parent.add_subitem(folder)
            else:
                print(f"[_create_folder_structure]: Unable to find parent of {folder.to_string()}")

    return roots


# OOP Version
def load_rekordbox_playlists(progress_callback=None) -> List[RbLibraryBase]:
    db = None
    library = []
    try:
        db = _open_database()
        
        # get all folders/playlists, store into a list
        playlists_all_raw = db.get_playlist()
        folders = []
        playlists = []
        for playlist_raw in playlists_all_raw:
            #print(f"Parse: {playlist_raw}")
            pl_type = RbPlaylistAttribute(playlist_raw.Attribute)
            if pl_type == RbPlaylistAttribute.FOLDER:
                item = RbFolder(playlist_raw.ID, playlist_raw.ParentID, playlist_raw.Name, playlist_raw.Seq)
                folders.append(item)
            elif pl_type == RbPlaylistAttribute.PLAYLIST:
                item = RbPlaylist(playlist_raw.ID, playlist_raw.ParentID, playlist_raw.Name, playlist_raw.Seq)
                playlists.append(item)
            elif pl_type == RbPlaylistAttribute.INTELLIGENT_PLAYLIST:
                item = RbIntelligentPlaylist(playlist_raw.ID, playlist_raw.ParentID, playlist_raw.Name, playlist_raw.Seq, playlist_raw.SmartList)
                playlists.append(item)

        if progress_callback:
            progress_callback(status="", progress=f"Found {len(playlists)} playlists", caller_function="load_rekordbox_playlists")
        else:
            print(f"[load_rekordbox_playlists_OOP] found: {len(folders)} folders | {len(playlists)} playlists")


        # from playlists discovered, add all tracks into them
        total = len(playlists)
        for idx, playlist in enumerate(playlists):
            _fill_playlist_with_tracks(db, playlist, idx, total, progress_callback)

        # from folders list, add all playlists into folders
        _fill_folder_with_playlists(folders, playlists)

        # from folders list, create the folder structure
        library = _create_folder_structure(folders)

        # return final library
        return library
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
