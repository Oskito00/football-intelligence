"""
Helper utility functions for the chatbot.
"""

import sys
import time

def print_banner():
    """Print a welcome banner for the chatbot."""
    banner = """
⚽ ═══════════════════════════════════════════════════════════════════════════ ⚽
                        INBETMENTS CHATBOT                               
        Powered by AI • Predictions & Analytics • Betting Tips                    
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
    """
    print(banner)

def format_match_time(datetime_str):
    """
    Format a datetime string for display.
    
    Args:
        datetime_str: ISO format datetime string
        
    Returns:
        Formatted time string
    """
    try:
        from datetime import datetime
        dt = datetime.fromisoformat(datetime_str.replace('Z', '+00:00'))
        return dt.strftime("%A, %B %d at %I:%M %p")
    except:
        return datetime_str

def format_probability(prob):
    """
    Format a probability as a percentage.
    
    Args:
        prob: Probability value (0-1)
        
    Returns:
        Formatted percentage string
    """
    try:
        return f"{prob:.1%}"
    except:
        return "N/A"

def format_confidence(confidence):
    """
    Format confidence score with descriptive text.
    
    Args:
        confidence: Confidence value (0-1)
        
    Returns:
        Formatted confidence string
    """
    try:
        percentage = confidence * 100
        if percentage >= 80:
            level = "Very High"
        elif percentage >= 65:
            level = "High"
        elif percentage >= 50:
            level = "Medium"
        elif percentage >= 35:
            level = "Low"
        else:
            level = "Very Low"
        
        return f"{percentage:.1f}% ({level})"
    except:
        return "N/A"

def truncate_text(text, max_length=100):
    """
    Truncate text to a maximum length.
    
    Args:
        text: Text to truncate
        max_length: Maximum length
        
    Returns:
        Truncated text
    """
    if len(text) <= max_length:
        return text
    return text[:max_length-3] + "..."

def create_simple_table(headers, rows):
    """
    Create a simple ASCII table.
    
    Args:
        headers: List of header strings
        rows: List of row data (each row is a list)
        
    Returns:
        Formatted table string
    """
    if not headers or not rows:
        return ""
    
    # Calculate column widths
    col_widths = [len(str(h)) for h in headers]
    
    for row in rows:
        for i, cell in enumerate(row):
            if i < len(col_widths):
                col_widths[i] = max(col_widths[i], len(str(cell)))
    
    # Create separator
    separator = "+" + "+".join("-" * (w + 2) for w in col_widths) + "+"
    
    # Format header
    header_row = "|" + "|".join(f" {str(h):<{col_widths[i]}} " for i, h in enumerate(headers)) + "|"
    
    # Format data rows
    data_rows = []
    for row in rows:
        row_str = "|" + "|".join(f" {str(row[i] if i < len(row) else ''):<{col_widths[i]}} " for i in range(len(col_widths))) + "|"
        data_rows.append(row_str)
    
    # Combine all parts
    table_parts = [separator, header_row, separator] + data_rows + [separator]
    return "\n".join(table_parts)

def validate_team_name(team_name):
    """
    Basic validation for team names.
    
    Args:
        team_name: Team name string
        
    Returns:
        Boolean indicating if valid
    """
    if not team_name or not isinstance(team_name, str):
        return False
    
    # Remove extra whitespace
    team_name = team_name.strip()
    
    # Check length
    if len(team_name) < 2 or len(team_name) > 50:
        return False
    
    # Check for basic validity (letters, spaces, common punctuation)
    import re
    pattern = r'^[A-Za-z0-9\s\.\-\']+$'
    return bool(re.match(pattern, team_name))

def safe_divide(numerator, denominator, default=0):
    """
    Safely divide two numbers, returning default if division by zero.
    
    Args:
        numerator: Number to divide
        denominator: Number to divide by
        default: Default value if division by zero
        
    Returns:
        Division result or default
    """
    try:
        if denominator == 0:
            return default
        return numerator / denominator
    except:
        return default

def typewriter_print(text, delay=0.005):
    """
    Print text with a typewriter effect (character by character).
    
    Args:
        text: Text to print
        delay: Delay between characters in seconds (default: 0.03)
    """
    for char in text:
        sys.stdout.write(char)
        sys.stdout.flush()
        time.sleep(delay)
    print()  # Add newline at the end 