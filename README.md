# Rexato - Rekordbox/Serato Playlist Converter

A modern, cross-platform GUI application for converting playlists between Rekordbox and Serato DJ software. Built with PyQt6.

**For DJs ❤️ by DJs 🎧**

![PyQt6](https://img.shields.io/badge/PyQt6-6.0+-green.svg)
![Python](https://img.shields.io/badge/Python-3.12+-blue.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

- 🎨 **Modern UI** - PyDracula themed interface with smooth interactions
- 🔍 **Auto-Detection** - Automatically finds Rekordbox database and Serato directories
- 🔄 **Bidirectional Conversion** - Convert playlists between Rekordbox and Serato DJ
- 📁 **Folder Structure Support** - Preserves folder hierarchies and subcrate organization during conversion

## Requirements

- Python 3.12 or higher
- Rekordbox installed
- Serato DJ installed

**Tested Versions:**
- Rekordbox: 7.2.2
- Serato DJ: 3.2.2

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/winson0123/Rexato
   cd rexato
   ```

2. Install dependencies:
   ```bash
   python -m pip install -r requirements.txt
   ```

3. Run the application:
   ```bash
   python main.py
   ```

## Usage

1. Select conversion direction (Rekordbox ↔ Serato)
2. Wait for playlists/crates to load
3. Select items to convert using checkboxes
4. Click "Convert Selected" and confirm
5. Review conversion results

## How It Works

The application automatically detects:
- **Rekordbox database** via `pyrekordbox` (checks default locations)
- **Serato crates directory** in common locations:
  - Windows: `%USERPROFILE%\Music\_Serato_\Subcrates`
  - macOS: `~/Music/_Serato_/Subcrates`
  - Linux: `~/Music/_Serato_/Subcrates`

### Conversion Process

- **Rekordbox → Serato**: Reads playlists and creates `.crate` files
- **Serato → Rekordbox**: Reads crates and creates playlists in Rekordbox database

Both directions preserve track order and match tracks by file path.

> [!IMPORTANT]
> The conversion process ports the playlist/crate structure with tracks in order. Track analysis (BPM detection, key detection, beatgrids, waveforms) is not transferred and must be performed by the destination software (Rekordbox or Serato) after conversion.

### Intelligent Playlist / Smart Crate Support

- Rekordbox intelligent/smart playlists → converted to regular crates
- Serato Smart crates → converted to regular playlists

> [!NOTE]
> Smart/intelligent rules are not preserved during conversion.

## Future Features Planned

- USB detection for conversion
- Porting beatgrid analysis (including dynamic beatgrids)
- Porting hot cues/memory loops

## Credits

- **pyrekordbox** - Rekordbox database access
- **serato-tools** - Serato crate file format support
- **PyQt6** - GUI framework
- **PyDracula** - Theme inspiration
