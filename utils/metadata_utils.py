"""
Utilities for extracting and processing audio metadata
"""

import os
from typing import Optional


def get_attr(obj, *attrs):
    """Get attribute from object trying multiple names"""
    for attr in attrs:
        # Only try if attr is a string (attribute name), not a default value
        if isinstance(attr, str) and hasattr(obj, attr):
            try:
                return getattr(obj, attr)
            except (AttributeError, TypeError):
                continue
    # Return the last item if it's not a string (default value) or None
    if attrs:
        last = attrs[-1]
        if not isinstance(last, str):
            return last
    return None


def get_album(content):
    """Get album name from djmdContent -> djmdAlbum"""
    try:
        djmdAlbum = content.Album
        if djmdAlbum and djmdAlbum.Name:
            return djmdAlbum.Name
        return 'Unknown'
    except Exception as e:
        print(f"Error getting artist: {e}")
    return 'Unknown'

def get_artist(content):
    """Get artist name from djmdContent -> djmdArtist"""
    try:
        djmdArtist = content.Artist
        if djmdArtist and djmdArtist.Name:
            return djmdArtist.Name
        return 'Unknown'
    except Exception as e:
        print(f"Error getting artist: {e}")
    return 'Unknown'


def get_genre(content):
    """Get genre from djmdContent -> djmdGenre"""
    try:
        djmdGenre = content.Genre
        if djmdGenre and djmdGenre.Name:
            return djmdGenre.Name
        return 'N/A'
    except Exception as e:
        print(f"Error getting genre: {e}")
    return 'N/A'


def get_key(content):
    """Get key from djmdContent -> djmdKey"""
    try:
        djmdKey = content.Key
        if djmdKey and djmdKey.ScaleName:
            return djmdKey.ScaleName
        return 'N/A'
    except Exception as e:
        print(f"Error getting genre: {e}")
    return 'N/A'


def get_file_extension(file_path):
    """Get file extension from path"""
    if not file_path:
        return 'N/A'
    ext = os.path.splitext(file_path)[1]
    return ext[1:].upper() if ext else 'N/A'


def format_time(seconds):
    """Format seconds to MM:SS"""
    try:
        seconds = float(seconds)
        mins = int(seconds // 60)
        secs = int(seconds % 60)
        return f"{mins}:{secs:02d}"
    except (ValueError, TypeError):
        return 'N/A'


def format_bpm(bpm_value):
    """Format BPM to nearest integer, max 3 digits.
    
    Rekordbox stores BPM as integer where 128.5 BPM = 12850 (multiplied by 100).
    Normal BPM range is 60-200, so when multiplied by 100, that's 6000-20000.
    This function detects and handles the Rekordbox format.
    """
    if bpm_value is None:
        return 'N/A'
    
    try:
        # Convert to float first
        bpm_float = float(bpm_value)
        
        # Rekordbox stores BPM multiplied by 100 (e.g., 12850 = 128.5 BPM)
        # Normal BPM range is 60-200, so multiplied values are 6000-20000 (4-5 digits)
        # If the value is >= 1000 (which covers all realistic multiplied BPMs), divide by 100
        # This handles values like 12850, 13000, etc. converting to 128.5, 130.0, etc.
        if bpm_float >= 1000:
            bpm_float = bpm_float / 100.0
        
        # Round to nearest integer
        bpm_int = int(round(bpm_float))
        
        # Return as string (will be 1-3 digits for normal BPM ranges 60-200)
        return str(bpm_int)
    except (ValueError, TypeError):
        # If conversion fails, return N/A
        return 'N/A'


def get_audio_metadata(file_path):
    """Get metadata from audio file using mutagen or similar"""
    try:
        # Try to use mutagen for metadata extraction
        try:
            from mutagen import File as MutagenFile
            audio_file = MutagenFile(file_path)
            
            if audio_file is None:
                return get_basic_metadata(file_path)
            
            # Determine if file uses ID3 tags (MP3) or Vorbis comments (FLAC, Ogg, etc.)
            # Check by trying to access tags differently
            # For ID3 (MP3): Use TIT2, TPE1, etc.
            # For Vorbis (FLAC, Ogg): Use TITLE, ARTIST, etc.
            
            # Helper function to safely get tag value
            def get_tag(*keys, default=''):
                """Try multiple tag keys and return first found value"""
                for key in keys:
                    try:
                        value = audio_file.get(key)
                        if value:
                            if isinstance(value, list):
                                if value and len(value) > 0:
                                    return str(value[0])
                            else:
                                return str(value)
                    except (KeyError, IndexError, AttributeError, TypeError):
                        continue
                return default
            
            # Try ID3 tags first (MP3)
            title = get_tag('TIT2', 'TITLE')
            artist = get_tag('TPE1', 'ARTIST')
            genre = get_tag('TCON', 'GENRE')
            
            # For date/year, try multiple formats
            year = get_tag('TDRC', 'TORY', 'DATE', 'YEAR')
            # Extract year from date if it's a full date string
            if year and year != 'N/A' and len(year) > 4:
                try:
                    # Try to extract year from date string (e.g., "2024-01-01" -> "2024")
                    year_parts = year.split('-')
                    if year_parts:
                        year = year_parts[0]
                except:
                    pass
            
            # BPM and Key - try both ID3 and Vorbis formats
            bpm = get_tag('TBPM', 'BPM')
            key = get_tag('TKEY', 'INITIALKEY', 'KEY')
            
            # Comments
            comments = get_tag('COMM', 'COMMENT', 'DESCRIPTION')
            
            # Get rating - try multiple methods
            rating = '0'
            try:
                # Method 1: Try ID3 POPM frame (MP3 files)
                # POPM stores rating as 0-255, need to convert to 0-5 stars
                if hasattr(audio_file, 'tags') and audio_file.tags:
                    try:
                        from mutagen.id3 import ID3FileType, POPM
                        if isinstance(audio_file, ID3FileType):
                            # Get all POPM frames (there might be multiple for different users)
                            popm_frames = audio_file.tags.getall('POPM')
                            if popm_frames:
                                # Use the first POPM frame (usually represents the main rating)
                                # If multiple exist, some players use the first one
                                popm_frame = popm_frames[0]
                                if hasattr(popm_frame, 'rating') and popm_frame.rating is not None:
                                    popm_rating = int(popm_frame.rating)
                                    # Convert 0-255 scale to 0-5 stars
                                    # Common mapping: 0=0, 51=1, 102=2, 153=3, 204=4, 255=5
                                    # Using thresholds that match common player behavior
                                    if popm_rating == 0:
                                        rating = '0'
                                    elif popm_rating <= 51:
                                        rating = '1'
                                    elif popm_rating <= 102:
                                        rating = '2'
                                    elif popm_rating <= 153:
                                        rating = '3'
                                    elif popm_rating <= 204:
                                        rating = '4'
                                    else:
                                        rating = '5'
                    except (ImportError, AttributeError, KeyError, TypeError, IndexError):
                        pass
                
                # Method 2: Try standard rating tags (if POPM not found or not ID3)
                if rating == '0':
                    rating_tag = get_tag('RATING', 'RATE', 'RATING_STARS', 'RATING_WFMU')
                    if rating_tag:
                        try:
                            # Try to parse as integer or float
                            rating_val = float(rating_tag)
                            # Convert to 0-5 scale if needed
                            if rating_val > 5:
                                # Might be on 0-255 scale or 0-100 scale
                                if rating_val > 100:
                                    # 0-255 scale
                                    rating_val = int((rating_val / 255) * 5)
                                else:
                                    # 0-100 scale
                                    rating_val = int((rating_val / 100) * 5)
                            else:
                                rating_val = int(rating_val)
                            rating = str(max(0, min(5, int(rating_val))))
                        except (ValueError, TypeError):
                            pass
            except Exception:
                rating = '0'
            
            # Title fallback to filename
            if not title:
                title = os.path.splitext(os.path.basename(file_path))[0]
            
            # Get duration from info
            duration = 0
            if hasattr(audio_file, 'info') and audio_file.info:
                duration = getattr(audio_file.info, 'length', 0) or 0
            
            # return track info as dict
            return {
                'title': title or os.path.splitext(os.path.basename(file_path))[0],
                'artist': artist or 'Unknown',
                'time': format_time(duration),
                'bpm': format_bpm(bpm),
                'key': key or 'N/A',
                'rating': rating,
                'genre': genre or 'N/A',
                'filetype': get_file_extension(file_path),
                'year': year or 'N/A',
                'comments': comments or '',
                'path': file_path,  # Include file path for conversion
                'album': '', # NOT IMPLEMENTED 
            }
        except ImportError:
            return get_basic_metadata(file_path)
    except Exception as e:
        print(f"Error reading metadata: {e}")
        import traceback
        traceback.print_exc()
        return get_basic_metadata(file_path)


def get_basic_metadata(file_path):
    """Get basic metadata from filename"""
    filename = os.path.splitext(os.path.basename(file_path))[0]
    return {
        'title': filename,
        'artist': 'Unknown',
        'time': 'N/A',
        'bpm': format_bpm(None),
        'key': 'N/A',
        'rating': '0',
        'genre': 'N/A',
        'filetype': get_file_extension(file_path),
        'year': 'N/A',
        'comments': '',
        'path': file_path,  # Include file path for conversion
    }

