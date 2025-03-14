from fastapi import Depends, HTTPException, status, Header
from sqlmodel import Session, select
from api.database import get_session
from api.public.user.models import User, Session as UserSession
from typing import Optional
from datetime import datetime

async def get_current_user(
    authorization: str = Header(...),
    db: Session = Depends(get_session)
) -> User:
    """
    Gets the current user based on the session token sent in the Authorization header.
    
    Args:
        authorization: Session token sent in the header
        db: Database session
    
    Returns:
        User: Authenticated user
    
    Raises:
        HTTPException: If there is no session token or if the token is invalid
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No session token provided"
        )

    # Extract the token from the header (in case it comes as "Bearer <token>")
    session_token = authorization.replace("Bearer ", "")

    # Look for the active session using the Auth.js model
    query = select(UserSession, User).join(User).where(
        UserSession.sessionToken == session_token,
        UserSession.expires > datetime.utcnow()
    )
    result = db.exec(query).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired session"
        )
    
    session, user = result
    return user

async def get_current_user_optional(
    authorization: str | None = Header(default=None),
    db: Session = Depends(get_session)
) -> User | None:
    if not authorization:
        return None
    try:
        return await get_current_user(authorization=authorization, db=db)
    except HTTPException:
        return None
