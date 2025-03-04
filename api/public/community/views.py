from fastapi import APIRouter, Depends, Query, HTTPException, status
from sqlmodel import Session
from api.public.community.models import CommunityRead
from api.public.community.crud import get_community
from api.database import get_session
from sqlalchemy import select, func
from api.public.user.models import User, UserCommunityLink
from api.auth.dependencies import get_current_user_optional, get_current_user
from typing import Optional

router = APIRouter()

@router.get("/{community_id}", response_model=CommunityRead)
def read(community_id: int, db: Session = Depends(get_session)):
    return get_community(community_id, db)

@router.get("/{community_id}/members")
def get_community_members(
    community_id: int,
    page: int = Query(1, ge=1, description="Número de página"),
    size: int = Query(20, ge=1, le=100, description="Tamaño de página"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """
    Obtiene los miembros de una comunidad.
    Muestra solo usuarios que han elegido ser visibles o el usuario autenticado.
    No requiere autenticación, pero si el usuario está autenticado, se incluirá
    en la lista incluso si ha elegido no ser visible.
    """
    # Primero verifica si la comunidad existe, sin verificar membresía
    community = get_community(community_id, db, check_membership=False, current_user=current_user)
    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comunidad con ID {community_id} no encontrada"
        )
    
    # Calcular offset para paginación
    offset = (page - 1) * size
    
    # Consulta modificada que selecciona los datos que necesitamos directamente
    query = select(
        User.id,
        User.username,
        User.name,
        User.image,
        UserCommunityLink.is_public
    ).join(UserCommunityLink).where(
        UserCommunityLink.community_id == community_id,
        UserCommunityLink.is_public == True
    )
    
    # Si hay un usuario autenticado, incluirlo en los resultados aunque no sea visible
    if current_user:
        query = select(
            User.id,
            User.username,
            User.name,
            User.image,
            UserCommunityLink.is_public
        ).join(UserCommunityLink).where(
            UserCommunityLink.community_id == community_id,
            (UserCommunityLink.is_public == True) | (User.id == current_user.id)
        )
    
    # Ejecutar consulta y procesar resultados
    rows = db.exec(query.offset(offset).limit(size)).all()
    user_list = []
    for row in rows:
        user_data = {
            "id": row.id,
            "username": row.username,
            "name": row.name,
            "image": row.image,
            "is_current_user": current_user and row.id == current_user.id,
            "is_public": row.is_public
        }
        user_list.append(user_data)
    
    return {
        "items": user_list,
        "total": len(user_list),
        "page": page,
        "size": size,
        "pages": (len(user_list) + size - 1) // size
    }

@router.post("/{community_id}/join", status_code=status.HTTP_200_OK)
def join_community(
    community_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Permite al usuario unirse a una comunidad.
    Por defecto, el usuario se une en modo privado (is_public=False).
    """
    # Verificar que la comunidad existe
    community = get_community(community_id, db, check_membership=False, current_user=current_user)
    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Comunidad con ID {community_id} no encontrada"
        )
    
    # Verificar si el usuario ya es miembro
    existing_membership = db.exec(
        select(UserCommunityLink).where(
            UserCommunityLink.user_id == current_user.id,
            UserCommunityLink.community_id == community_id
        )
    ).first()
    
    if existing_membership:
        return {"message": "Ya eres miembro de esta comunidad"}
    
    # Crear la relación usuario-comunidad (por defecto en modo privado)
    new_membership = UserCommunityLink(
        user_id=current_user.id,
        community_id=community_id,
        is_public=False  # Por defecto, el usuario es privado en la comunidad
    )
    
    db.add(new_membership)
    db.commit()
    
    return {"message": "Te has unido a la comunidad correctamente"}

@router.delete("/{community_id}/join", status_code=status.HTTP_200_OK)
def leave_community(
    community_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Permite al usuario abandonar una comunidad.
    """
    # Verificar que existe la membresía
    membership = db.exec(
        select(UserCommunityLink).where(
            UserCommunityLink.user_id == current_user.id,
            UserCommunityLink.community_id == community_id
        )
    ).first()
    
    if not membership:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No eres miembro de esta comunidad"
        )
    
    # Eliminar la membresía
    db.delete(membership)
    db.commit()
    
    return {"message": "Has abandonado la comunidad correctamente"}