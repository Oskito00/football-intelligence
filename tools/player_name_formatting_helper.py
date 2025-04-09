import re

def normalise_player_name(player_name):
    """Normalises the player name to a format that can be used to search for the player on the fifa ratings website"""
    # removes apostrophes or ``
    player_name = re.sub(r"['`]", "", player_name)  # Remove apostrophes and backticks using regex
    # removes any non-alphanumeric characters
    return player_name.lower()

def format_player_name(player_name):
    """Convert names with multiple last names to hyphenated format"""
    # Handle comma-separated names (Last, First Middle)
    if ", " in player_name:
        parts = player_name.split(", ", 1)
        last_names = parts[0].strip().split()  # Split multiple last names
        first_parts = parts[1].strip().split()
        
        # Combine first parts with hyphenated last names
        return '-'.join(
            [part.lower() for part in first_parts] +
            [name.lower() for name in last_names]
        )
    
    # Handle names without commas but with spaces
    return '-'.join(player_name.strip().split()).lower()
