from enum import Enum

class RbPlaylistAttribute(Enum):
    """Enum for djmdPlaylist::Attribute"""
    PLAYLIST = 0
    FOLDER = 1
    INTELLIGENT_PLAYLIST = 4

class RbTrackFileType(Enum):
    """Enum for djmdContent::FileType"""
    MP3_0 = 0
    MP3_1 = 1
    M4A = 4
    FLAC = 5
    WAV = 11
    AIFF = 12
    

class RbLibraryBase:
    def __init__(self, id, seq):
        self.id = id
        self.seq = seq

    def to_string(self):
        return f"id={self.id}, seq={self.seq}"

class RbTrack(RbLibraryBase):
    def __init__(self, id, track_number, filepath, artist, title, album, genre, bpm, length, key, rating, year, comments, filetype):
        super().__init__(id, track_number)
        self.filepath = filepath

        # track specific metadata
        self.artist = artist
        self.title = title
        self.album = album
        self.genre = genre
        self.bpm = bpm
        self.length = length
        self.key = key
        self.rating = rating
        self.year = year
        self.comments = comments
        self.filetype = filetype
        # to add: MyTags

    def to_string(self):
        return f"RbTrack<{super().to_string()}>: title={self.title}"


class RbFolder(RbLibraryBase):
    def __init__(self, id, parentId, name, sequence):
        super().__init__(id, sequence)
        self.parentId = parentId
        self.name = name
        self.subitems = [] # can be RbFolder, RbPlaylist, RbIntelligentPlaylist
    
    def add_subitem(self, item: RbLibraryBase):
        self.subitems.append(item)

    def sort(self):
        # sort items by their sequence number (following Rekordbox)
        self.subitems.sort(key=lambda x: x.seq)
    
    def to_string(self):
        return f"RbFolder<{super().to_string()}>: parentId={self.parentId}, title={self.name}"


class RbPlaylist(RbLibraryBase):
    def __init__(self, id, parentId, name, sequence):
        super().__init__(id, sequence)
        self.parentId = parentId
        self.name = name
        self.tracks = []

    def add_track(self, track: RbTrack):
        self.tracks.append(track)

    def sort(self):
        # sort tracks by their track number
        self.tracks.sort(key=lambda x: x.track_number)

    def to_string(self):
        return f"RbPlaylist<{super().to_string()}>: parentId={self.parentId}, title={self.name}"

class RbIntelligentPlaylist(RbPlaylist):
    def __init__(self, id, parentId, name, sequence, smartlist_string):
        super().__init__(id, parentId, name, sequence)
        self.smartlist_xml_conditions = smartlist_string