"""
Shared utilities for checking library availability
"""

# Check Rekordbox availability
try:
    from pyrekordbox import Rekordbox6Database
    REKORDBOX_AVAILABLE = True
except ImportError:
    REKORDBOX_AVAILABLE = False
except Exception as e:
    REKORDBOX_AVAILABLE = False
    print(f"Warning: Error importing pyrekordbox: {type(e).__name__}: {e}")

# Check Serato tools availability
try:
    from serato_tools.crate import Crate
    from serato_tools.smart_crate import SmartCrate
    SERATO_TOOLS_AVAILABLE = True
except ImportError:
    SERATO_TOOLS_AVAILABLE = False
except Exception as e:
    SERATO_TOOLS_AVAILABLE = False
    print(f"Warning: Error importing serato-tools: {type(e).__name__}: {e}")

