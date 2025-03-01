from sqlmodel import Session, select
from typing import Optional
from api.public.tag.models import Tag

def get_tag_by_name(session: Session, name: str) -> Optional[Tag]:
    """
    Get a tag by its name
    
    Args:
        session: Database session
        name: Name of the tag to search for
        
    Returns:
        Tag object if found, None otherwise
    """
    return session.exec(select(Tag).where(Tag.name == name)).first()

def create_tag(session: Session, name: str) -> Tag:
    """
    Create a new tag
    
    Args:
        session: Database session
        name: Name of the tag to create
        
    Returns:
        Created Tag object
    """
    tag = Tag(name=name)
    session.add(tag)
    session.commit()
    session.refresh(tag)
    return tag

def get_all_tags(session: Session, skip: int = 0, limit: int = 100) -> list[Tag]:
    """
    Get all tags with pagination
    
    Args:
        session: Database session
        skip: Number of records to skip
        limit: Maximum number of records to return
        
    Returns:
        List of Tag objects
    """
    return session.exec(select(Tag).offset(skip).limit(limit)).all()

def delete_tag(session: Session, tag_id: int) -> None:
    """
    Delete a tag by its ID
    
    Args:
        session: Database session
        tag_id: ID of the tag to delete
    """
    tag = session.get(Tag, tag_id)
    if tag:
        session.delete(tag)
        session.commit() 