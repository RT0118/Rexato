"""
Utilities for working with Serato data
"""


import os
from os import sep as OS_SEPARATOR
from platform import system
from pathlib import Path
from typing import List, Dict
from .metadata_utils import get_audio_metadata, get_basic_metadata
from .serato_classes import SeratoTrack, SeratoCrate, SUBCRATES_FOLDER, SERATO_BASE_FOLDER, CRATE_SEPARATOR
from string import ascii_uppercase


try:
    from serato_tools.crate import Crate
    from serato_tools.smart_crate import SmartCrate
    from serato_tools.utils import SERATO_DIR
except ImportError as e:
    raise ImportError(
        "serato-tools is required but not installed. "
        "Install it with: pip install serato-tools"
    ) from e
        

def get_available_serato_subcrates_dir(progress_callback) -> List[str]:
    system_os = system()
    subcrates_dirs = []
    if system_os == "Windows":
        # enum for drives, search each drive
        for drive_letter in ascii_uppercase:
            if drive_letter == "C":
                drive = SERATO_DIR # use serato-tools provided dir
            else:
                drive = os.path.join(f"{drive_letter}:", SERATO_BASE_FOLDER)
            
            dir = os.path.join(drive, SUBCRATES_FOLDER)
            if dir and os.path.isdir(dir):
                progress_callback(status="", progress=f"Found subcrate directory in {dir}", caller_function="get_available_serato_subcrates_dir")
                subcrates_dirs.append(dir)

    elif system_os == "Darwin":
        # check if default serato dir exists
        dir = os.path.join(SERATO_DIR, SUBCRATES_FOLDER)
        if dir and os.path.isdir(dir):
            subcrates_dirs.append(dir)
        # enum for /Volumes
        for vols in os.listdir("/Volumes"):
            dir = os.path.join(vols, SERATO_BASE_FOLDER, SUBCRATES_FOLDER)
            if dir and os.path.isdir(dir):
                progress_callback(status="", progress=f"Found subcrate directory in {dir}", caller_function="get_available_serato_subcrates_dir")
                subcrates_dirs.append(dir)
    else:
        print(system_os)
    return subcrates_dirs


def parse_crate_path(filename: str):
    """Split crate's filename by '%%' separator"""
    name = filename.replace(".crate", "")
    parts = name.split(CRATE_SEPARATOR)
    if len(parts) == 1:
        return [], parts[-1]
    return parts[:-1], parts[-1]

def _create_serato_track_from_metadata(track_number, meta: dict):
    return SeratoTrack(track_number, meta.get('path'), meta.get('title'), meta.get('artist'), \
        meta.get('album'),meta.get('time'), meta.get('bpm'), meta.get('key'), meta.get('rating'), \
        meta.get('genre'), meta.get('filetype'), meta.get('year'), meta.get('comments'))

def _load_tracks_into_crate(crate: SeratoCrate):
    crate_data = Crate(crate.crate_filepath)
    base_drive = os.path.splitdrive(crate.crate_filepath)[0]
    tracks_in_crate = crate_data.get_track_paths()

    for idx, track_path in enumerate(tracks_in_crate):
        # get metadata
        full_path = f"{base_drive}{OS_SEPARATOR}{track_path}"
        track_info_dict = get_audio_metadata(full_path)
        track = _create_serato_track_from_metadata(idx+1, track_info_dict)
        crate.add_track(track)

def load_serato_library(directory_path: str, progress_callback) -> List[SeratoCrate]:
    """Simple one-function approach to build the crate tree"""
    path = Path(directory_path)
    all_crates = {}
    
    # Create all crate objects
    for fdr_file in path.glob("*.crate"):
        crate_filename = fdr_file.stem
        print(f"Found: {crate_filename} in {fdr_file}")

        _, name = parse_crate_path(crate_filename)

        crate = SeratoCrate(str(fdr_file), name)
        all_crates[crate_filename] = crate
    
    # Build hierarchy
    root_crates = []
    for crate_name, crate in all_crates.items():
        if CRATE_SEPARATOR in crate_name:
            # Find and add to parent
            parent_name = CRATE_SEPARATOR.join(crate_name.split(CRATE_SEPARATOR)[:-1])
            parent_crate = all_crates.get(parent_name)
            if parent_crate:
                parent_crate.add_subcrate(crate)
                #print(f"Placed {crate.to_string()} in parent {parent_crate.to_string()}")
        else:
            # This is a root-level crate
            root_crates.append(crate)
            #print(f"Added root crate {crate.to_string()}")
    
    # Parse tracks for all crates
    all_crate_values = all_crates.values()
    total = len(all_crate_values)
    for idx, crate in enumerate(all_crate_values):
        progress_callback(status="", progress=f"Loading crate {idx+1}/{total}: {crate.name}", caller_function="load_serato_library")
        _load_tracks_into_crate(crate)
    
    return root_crates


def _debug_print_crate_tree(crates: List[SeratoCrate]):
    """Debugging function to pretty print serato crates in CLI"""
    
    def _print_crate(crate: SeratoCrate, level: int, prefix: str, is_last: bool):
        # Tree connectors
        connector = "└── " if is_last else "├── "
        indent = "    " * (level - 1) if level > 0 else ""
        
        crate_name = Path(crate.crate_filepath).stem.split('%%')[-1]
        print(f"{indent}{connector}📦 {crate_name} "
              f"({len(crate.tracks)} tracks, {len(crate.subcrates)} subcrates)")
        
        # Print tracks
        if crate.tracks:
            track_indent = "    " * level
            for i, track in enumerate(crate.tracks):
                track_connector = "└── " if i == len(crate.tracks) - 1 else "├── "
                track_name = Path(track.path).name
                print(f"{track_indent}{track_connector}🎵 {track_name}")
        
        # Print subcrates
        for i, subcrate in enumerate(crate.subcrates):
            is_last_subcrate = i == len(crate.subcrates) - 1
            new_prefix = prefix + ("    " if is_last else "│   ")
            _print_crate(subcrate, level + 1, new_prefix, is_last_subcrate)
    
    for i, crate in enumerate(crates):
        is_last = i == len(crates) - 1
        _print_crate(crate, 0, "", is_last)


def load_serato_crates(progress_callback=None) -> List[SeratoCrate]:
    # look for possible locations of _Serato_ directories
    subcrate_dirs = get_available_serato_subcrates_dir(progress_callback)
    serato_library = []

    for dir in subcrate_dirs:
        root = load_serato_library(dir, progress_callback)
        if root:
            serato_library += root

    return serato_library