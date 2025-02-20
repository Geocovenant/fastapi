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
    Obtiene el usuario actual basado en el token de sesión enviado en el header Authorization.
    
    Args:
        authorization: Token de sesión enviado en el header
        db: Sesión de base de datos
    
    Returns:
        User: Usuario autenticado
    
    Raises:
        HTTPException: Si no hay token de sesión o si el token es inválido
    """
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="No se ha proporcionado token de sesión"
        )

    # Extraer el token del header (por si viene como "Bearer <token>")
    session_token = authorization.replace("Bearer ", "")

    # Buscar la sesión activa usando el modelo de Auth.js
    query = select(UserSession, User).join(User).where(
        UserSession.sessionToken == session_token,
        UserSession.expires > datetime.utcnow()
    )
    result = db.exec(query).first()

    if not result:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Sesión inválida o expirada"
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
