import os

def save_html(html_content, file_path):
    """Save HTML content to a file with proper encoding and directory structure"""
    # Create parent directory if it doesn't exist
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Write HTML content with UTF-8 encoding
    with open(file_path, 'w', encoding='utf-8') as file:
        file.write(html_content)

def read_html(file_path):
    """Read HTML content from a file with proper encoding"""
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()
