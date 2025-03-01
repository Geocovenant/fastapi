import re
import unicodedata
from typing import Optional

def create_slug(text: str, max_length: Optional[int] = 100) -> str:
    """
    Convierte un texto en un slug adecuado para URLs.
    
    Args:
        text: Texto a convertir en slug
        max_length: Longitud máxima del slug (por defecto 100 caracteres)
        
    Returns:
        Un slug adecuado para URLs
    """
    # Normalizar texto (eliminar acentos y convertir a forma compatible)
    text = unicodedata.normalize('NFKD', text).encode('ASCII', 'ignore').decode('ascii')
    
    # Convertir a minúsculas
    text = text.lower()
    
    # Reemplazar espacios con guiones
    text = re.sub(r'\s+', '-', text)
    
    # Eliminar caracteres especiales excepto guiones y alfanuméricos
    text = re.sub(r'[^a-z0-9\-]', '', text)
    
    # Eliminar guiones múltiples consecutivos
    text = re.sub(r'-+', '-', text)
    
    # Eliminar guiones al principio o final
    text = text.strip('-')
    
    # Limitar longitud si es necesario
    if max_length and len(text) > max_length:
        text = text[:max_length].rstrip('-')
    
    # Asegurar que no esté vacío
    if not text:
        text = "untitled"
    
    return text
