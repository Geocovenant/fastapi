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
    size: int = Query(100, ge=1, le=100, description="Tamaño de página"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """
    Obtiene los miembros de una comunidad.
    Muestra solo usuarios que han elegido ser visibles (is_public=True).
    No incluye al usuario autenticado si tiene is_public=False.
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
    
    # Consulta que solo selecciona miembros con is_public=True
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
    
    # Ejecutar consulta y procesar resultados - solo usuarios públicos
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
    
    # Contar el número total de miembros públicos
    total_public_query = select(func.count()).where(
        UserCommunityLink.community_id == community_id,
        UserCommunityLink.is_public == True
    ).select_from(UserCommunityLink)
    total_public_result = db.exec(total_public_query).first()
    total_public = total_public_result if total_public_result is None else total_public_result[0]
    
    # Contar el número total de miembros anónimos (is_public=False)
    total_anonymous_query = select(func.count()).where(
        UserCommunityLink.community_id == community_id,
        UserCommunityLink.is_public == False
    ).select_from(UserCommunityLink)
    total_anonymous_result = db.exec(total_anonymous_query).first()
    total_anonymous = total_anonymous_result if total_anonymous_result is None else total_anonymous_result[0]
    
    # Verificar si el usuario actual está configurado como no público en esta comunidad
    current_user_is_public = True
    current_user_is_member = False
    
    if current_user:
        # Modificar esta consulta para asegurar que devuelve exactamente el campo que necesitamos
        user_community_query = select(UserCommunityLink.is_public).where(
            UserCommunityLink.user_id == current_user.id,
            UserCommunityLink.community_id == community_id
        )
        user_community_result = db.exec(user_community_query).first()
        
        # Verificar si obtuvimos un resultado y acceder al valor de is_public de manera segura
        if user_community_result:
            # El usuario es miembro de la comunidad
            current_user_is_member = True
            # Acceder directamente al campo seleccionado
            current_user_is_public = user_community_result[0]
    
    # Calcular número de páginas basado solo en usuarios públicos
    total_pages = (total_public + size - 1) // size if total_public > 0 else 1
    
    # Construir la respuesta
    response = {
        "items": user_list,
        "total_public": total_public,
        "total_anonymous": total_anonymous,
        "page": page,
        "size": size,
        "pages": total_pages
    }
    
    # Añadir información sobre el usuario actual solo si está autenticado
    if current_user:
        # Añadir la clave a nivel raíz solicitada
        response["is_public_current_user"] = current_user_is_public if current_user_is_member else False
        
        response["current_user"] = {
            "is_member": current_user_is_member,
            "is_public": current_user_is_member and current_user_is_public
        }
    
    return response

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