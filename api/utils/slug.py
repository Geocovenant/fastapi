import re
import unicodedata
from typing import Optional

def create_slug(text: str, max_length: Optional[int] = 100) -> str:
    """
    Converts a text into a suitable slug for URLs.
    
    Args:
        text: Text to convert into slug
        max_length: Maximum length of the slug (default 100 characters)
        
    Returns:
        A suitable slug for URLs
    """
    # Normalize text (remove accents and convert to compatible form)
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ascii')
    
    # Convert to lowercase
    text = text.lower()
    
    # Replace spaces with hyphens
    text = re.sub(r'\s+', '-', text)
    
    # Remove special characters except hyphens and alphanumeric characters
    text = re.sub(r'[^a-z0-9\-]', '', text)
    
    # Remove multiple consecutive hyphens
    text = re.sub(r'-+', '-', text)
    
    # Remove hyphens at the beginning or end
    text = text.strip('-')
    
    # Limit length if necessary
    if max_length and len(text) > max_length:
        text = text[:max_length].rstrip('-')
    
    # Ensure it is not empty
    if not text:
        text = "untitled"
    
    return text
