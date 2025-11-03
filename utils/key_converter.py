"""
Key conversion utilities between Camelot Wheel and Classic musical notation
"""

# Camelot Wheel mapping
CAMELOT_TO_CLASSIC = {
    '1A': 'Abm', '1B': 'B',
    '2A': 'Ebm', '2B': 'Gb',
    '3A': 'Bbm', '3B': 'Db',
    '4A': 'Fm', '4B': 'Ab',
    '5A': 'Cm', '5B': 'Eb',
    '6A': 'Gm', '6B': 'Bb',
    '7A': 'Dm', '7B': 'F',
    '8A': 'Am', '8B': 'C',
    '9A': 'Em', '9B': 'G',
    '10A': 'Bm', '10B': 'D',
    '11A': 'F#m', '11B': 'A',
    '12A': 'C#m', '12B': 'E',
}

# Reverse mapping
CLASSIC_TO_CAMELOT = {v: k for k, v in CAMELOT_TO_CLASSIC.items()}

# Classic notation variations (handle sharps/flats and minor notations)
CLASSIC_VARIANTS = {
    # Major keys
    'C': '8B', 'C#': '3B', 'Db': '3B',
    'D': '10B', 'D#': '5B', 'Eb': '5B',
    'E': '12B', 'F': '7B',
    'F#': '11B', 'Gb': '11B',
    'G': '9B', 'G#': '2B', 'Ab': '2B',
    'A': '11B', 'A#': '4B', 'Bb': '4B',
    'B': '1B',
    # Minor keys
    'Am': '8A', 'A#m': '3A', 'Bbm': '3A',
    'Bm': '10A', 'B#m': '6A', 'Cm': '5A',
    'C#m': '12A', 'Dbm': '12A',
    'Dm': '7A', 'D#m': '2A', 'Ebm': '2A',
    'Em': '9A', 'Fm': '4A',
    'F#m': '11A', 'Gbm': '11A',
    'Gm': '6A', 'G#m': '1A', 'Abm': '1A',
}

# Also handle with flats/sharps in different formats
CLASSIC_VARIANTS.update({
    'Dâ™¯': '5B', 'Eâ™­': '5B',
    'Fâ™¯': '11B', 'Gâ™­': '11B',
    'Gâ™¯': '2B', 'Aâ™­': '2B',
    'Aâ™¯': '4B', 'Bâ™­': '4B',
    'Dâ™¯m': '2A', 'Eâ™­m': '2A',
    'Fâ™¯m': '11A', 'Gâ™­m': '11A',
    'Gâ™¯m': '1A', 'Aâ™­m': '1A',
})


def classic_to_camelot(classic_key: str) -> str:
    """Convert classic notation to Camelot Wheel notation"""
    if not classic_key or classic_key == 'N/A':
        return 'N/A'
    
    classic_key = classic_key.strip()
    
    # Check direct mapping first
    if classic_key in CLASSIC_TO_CAMELOT:
        return CLASSIC_TO_CAMELOT[classic_key]
    
    # Check variants (case-insensitive)
    classic_key_upper = classic_key.capitalize()
    if classic_key_upper in CLASSIC_VARIANTS:
        return CLASSIC_VARIANTS[classic_key_upper]
    
    # Check if already Camelot format
    if classic_key in CAMELOT_TO_CLASSIC:
        return classic_key
    
    # Try to match with regex for minor keys (e.g., "Am", "D#m")
    # This handles edge cases
    for variant, camelot in CLASSIC_VARIANTS.items():
        if classic_key_upper == variant or classic_key_upper.replace('#', 'â™¯').replace('b', 'â™­') == variant:
            return camelot
    
    # If we can't convert, return original
    return classic_key


def camelot_to_classic(camelot_key: str) -> str:
    """Convert Camelot Wheel notation to classic notation"""
    if not camelot_key or camelot_key == 'N/A':
        return 'N/A'
    
    camelot_key = camelot_key.strip()
    
    # Check direct mapping
    if camelot_key in CAMELOT_TO_CLASSIC:
        return CAMELOT_TO_CLASSIC[camelot_key]
    
    # Check if already classic format
    if camelot_key in CLASSIC_TO_CAMELOT or camelot_key in CLASSIC_VARIANTS.values():
        return camelot_key
    
    # If we can't convert, return original
    return camelot_key


def convert_key(key_value: str, target_format: str) -> str:
    """
    Convert key between formats
    
    Args:
        key_value: The key value to convert
        target_format: 'camelot' or 'classic'
    
    Returns:
        Converted key value
    """
    if not key_value or key_value == 'N/A':
        return 'N/A'
    
    key_value = key_value.strip()
    
    import re
    
    # Normalize to uppercase for Camelot format checking
    key_upper = key_value.upper()
    
    # Check if it matches Camelot pattern (1-2 digits followed by A or B)
    camelot_pattern = re.compile(r'^(\d{1,2}[AB])$', re.IGNORECASE)
    
    if target_format.lower() == 'camelot':
        # Try to detect if it's already Camelot (format like "8A", "12B")
        if key_upper in CAMELOT_TO_CLASSIC:
            return key_upper  # Already Camelot, return uppercase
        # Check if it matches Camelot pattern but with different case
        if camelot_pattern.match(key_value):
            return key_upper  # Convert to uppercase
        # Otherwise, assume it's classic and convert
        return classic_to_camelot(key_value)
    
    elif target_format.lower() == 'classic':
        # Check if it's Camelot format
        if key_upper in CAMELOT_TO_CLASSIC:
            return camelot_to_classic(key_upper)
        # Check if it matches Camelot pattern
        if camelot_pattern.match(key_value):
            return camelot_to_classic(key_upper)
        # Otherwise, assume it's already classic (preserve original case)
        return key_value
    
    # Unknown format, return original
    return key_value


def detect_key_format(key_value: str) -> str:
    """
    Detect if a key is in Camelot or Classic format
    
    Returns:
        'camelot', 'classic', or 'unknown'
    """
    if not key_value or key_value == 'N/A':
        return 'unknown'
    
    key_value = key_value.strip()
    
    # Check if it's Camelot format (numbers + letter, like "8A", "12B")
    if key_value in CAMELOT_TO_CLASSIC:
        return 'camelot'
    
    # Check if it's classic format (musical notation like "Am", "C", "F#m")
    if key_value in CLASSIC_TO_CAMELOT or key_value in CLASSIC_VARIANTS:
        return 'classic'
    
    # Try pattern matching for Camelot (1-2 digits followed by A or B)
    import re
    if re.match(r'^(\d{1,2}[AB])$', key_value, re.IGNORECASE):
        return 'camelot'
    
    # Check if it contains musical notation patterns
    if re.match(r'^[A-G][#â™¯bâ™­]?[m]?$', key_value, re.IGNORECASE):
        return 'classic'
    
    return 'unknown'

