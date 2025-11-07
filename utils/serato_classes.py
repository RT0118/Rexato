CRATE_SEPARATOR = "%%"
SERATO_BASE_FOLDER = "_Serato_"
SUBCRATES_FOLDER = "SubCrates"


class SeratoTrack:
    def __init__(self, track_number, filepath, title, artist, album, length, bpm, key, rating, genre, filetype, year, comments):
        self.filepath = filepath
        self.seq = track_number

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
        # to add: Groupings

    def to_string(self) -> str:
        return f"SeratoTrack<{self.title}> seq={self.seq}; path={self.filepath}"


class SeratoCrate():
    def __init__(self, crate_filepath, crate_name):
        self.crate_filepath = crate_filepath # resolves to original crate filename in disk
        self.name = crate_name
        self.tracks = []        # List[SeratoTrack]
        self.subcrates = []     # List[SeratoCrate]

    def add_track(self, track: SeratoTrack):
        self.tracks.append(track)
    
    def add_subcrate(self, crate: SeratoCrate):
         self.subcrates.append(crate)

    def to_string(self):
        return f"SeratoCrate<{self.name}> crate_filepath={self.crate_filepath}; tracks={len(self.tracks)}; subcrates={len(self.subcrates)}"
