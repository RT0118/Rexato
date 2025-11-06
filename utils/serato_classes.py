from os import sep as OS_SEPARATOR


CRATE_SEPARATOR = "%%"
SERATO_BASE_FOLDER = "_Serato_"
SUBCRATES_FOLDER = "SubCrates"


class SeratoTrack:
    def __init__(self, path):
        self.path = path
        # get track's metadata using mutagen
    
    def to_string(self):
        return f"SeratoTrack<{self.path}>"

class SeratoCrate():
    def __init__(self, path):
        self.filepath = path

        parent_crate_name, crate_name = self._split_crate_to_parent_child(path)
        self.crate_name = crate_name
        self.parent_crate_name = parent_crate_name
        self.tracks = []        # List[SeratoTrack]
        self.subcrates = []     # List[SeratoCrate]

    def add_track(self, track: SeratoTrack):
        self.tracks.append(track)


    def _split_crate_to_parent_child(self, path):
            """Split the full crate file name into <parent_crate>%%<child_crate>.crate"""
            crate_full = path.split(OS_SEPARATOR)[-1]
            split = crate_full.rsplit(CRATE_SEPARATOR)
            if len(split) == 1:
                # crate is a parent crate
                return "root", split[0][:-6] # remove .crate from string
            else:
                return split[0], split[1][:-6]
            

    def to_string(self):
        return f"SeratoCrate<{self.crate_name}>"
