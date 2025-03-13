from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from datetime import datetime
from typing import Optional
from api.database import get_session
from api.auth.dependencies import get_current_user, get_current_user_optional
from api.public.user.models import User, UserRole
from api.public.issue.models import (
    Issue, IssueCreate, IssueRead, IssueUpdate, 
    IssueStatus, IssueCommentCreate, IssueUpdateCreate,
    IssueCommentRead, IssueUpdateRead
)
from api.public.issue.crud import (
    get_all_issues, create_issue, get_issue_by_id_or_slug, 
    update_issue, delete_issue, add_issue_comment,
    add_issue_support, add_issue_update
)
from api.utils.generic_models import UserCommunityLink, IssueCommunityLink

router = APIRouter()

@router.get("/")
def read_issues(
    status: Optional[IssueStatus] = None,
    scope: Optional[str] = None,
    community_id: Optional[int] = None,
    country_code: Optional[str] = None,
    region_id: Optional[int] = None,
    subregion_id: Optional[int] = None,
    locality_id: Optional[int] = None,
    creator_id: Optional[int] = None,
    search: Optional[str] = None,
    page: int = Query(default=1, ge=1, description="Page number"),
    size: int = Query(default=10, ge=1, le=100, description="Items per page"),
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """
    Get issues with optional filters and pagination.
    - status: Filter by issue status
    - scope: Filter by scope (e.g., 'LOCAL', 'REGIONAL', etc.)
    - community_id: Filter by community ID
    - country_code: Filter by country code (CCA2)
    - region_id: Filter by region ID
    - subregion_id: Filter by subdivision ID
    - locality_id: Filter by locality ID
    - creator_id: Filter by creator
    - search: Search by text in title or description
    - page: Page number (default: 1)
    - size: Items per page (default: 10, max: 100)
    """
    # Filtrar parámetros indefinidos o nulos
    if country_code == "undefined" or country_code == "null":
        country_code = None
    
    if community_id == "undefined" or community_id == "null" or community_id == 0:
        community_id = None
        
    if region_id == "undefined" or region_id == "null" or region_id == 0:
        region_id = None
        
    if subregion_id == "undefined" or subregion_id == "null" or subregion_id == 0:
        subregion_id = None
        
    if locality_id == "undefined" or locality_id == "null" or locality_id == 0:
        locality_id = None
    
    try:
        return get_all_issues(
            db, 
            status=status,
            scope=scope,
            community_id=community_id,
            country_code=country_code,
            region_id=region_id,
            subregion_id=subregion_id,
            locality_id=locality_id,
            creator_id=creator_id,
            search=search,
            current_user_id=current_user.id if current_user else None,
            page=page,
            size=size
        )
    except Exception as e:
        # Registrar el error para depuración
        print(f"Error al obtener issues: {str(e)}")
        # Devolver una respuesta amigable
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Error al procesar los parámetros de consulta. Verifique que los valores sean correctos."
        )

@router.post("/", response_model=IssueRead, status_code=status.HTTP_201_CREATED)
def create_new_issue(
    issue_data: IssueCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Create a new issue.
    Authentication required.
    """
    return create_issue(db, issue_data, current_user.id)

@router.get("/{issue_id_or_slug}", response_model=IssueRead)
def get_issue(
    issue_id_or_slug: str,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """
    Get a specific issue by ID or slug.
    No authentication required.
    """
    issue = get_issue_by_id_or_slug(
        db, 
        issue_id_or_slug, 
        current_user_id=current_user.id if current_user else None
    )
    
    # Increment view counter
    db_issue = db.get(Issue, issue.id)
    if db_issue:
        db_issue.views_count += 1
        db.add(db_issue)
        db.commit()
    
    return issue

@router.patch("/{issue_id}", response_model=IssueRead)
def update_issue_details(
    issue_id: int,
    issue_data: IssueUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Update an existing issue.
    Only the creator or an administrator can edit the issue.
    """
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    # Verify permissions
    if issue.creator_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this issue"
        )
    
    return update_issue(db, issue_id, issue_data, current_user.id)

@router.delete("/{issue_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_issue_endpoint(
    issue_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Delete an issue.
    Only the creator or an administrator can delete the issue.
    """
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    # Verify permissions
    if issue.creator_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this issue"
        )
    
    delete_issue(db, issue_id)

@router.post("/{issue_id}/comments", response_model=IssueCommentRead, status_code=status.HTTP_201_CREATED)
def add_comment(
    issue_id: int,
    comment_data: IssueCommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Add a comment to an issue.
    Authentication and community membership required.
    """
    # Verify that the issue exists
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )

    # Verify that the user is a member of at least one of the issue's communities
    user_communities = db.exec(
        select(UserCommunityLink.community_id)
        .where(UserCommunityLink.user_id == current_user.id)
    ).all()
    user_community_ids = set(uc.community_id for uc in user_communities)
    
    issue_communities = db.exec(
        select(IssueCommunityLink.community_id)
        .where(IssueCommunityLink.issue_id == issue_id)
    ).all()
    issue_community_ids = set(ic.community_id for ic in issue_communities)
    
    if not user_community_ids.intersection(issue_community_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of the community to comment on this issue"
        )

    return add_issue_comment(db, issue_id, current_user.id, comment_data)

@router.post("/{issue_id}/support")
def toggle_support(
    issue_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Toggle support for an issue. If the user already supports the issue,
    their support is removed. If not, it is added.
    Authentication and community membership required.
    """
    # Verify that the issue exists
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )

    # Verify that the user is a member of at least one of the issue's communities
    user_communities = db.exec(
        select(UserCommunityLink.community_id)
        .where(UserCommunityLink.user_id == current_user.id)
    ).all()
    user_community_ids = set(uc.community_id for uc in user_communities)
    
    issue_communities = db.exec(
        select(IssueCommunityLink.community_id)
        .where(IssueCommunityLink.issue_id == issue_id)
    ).all()
    issue_community_ids = set(ic.community_id for ic in issue_communities)
    
    if not user_community_ids.intersection(issue_community_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of the community to support this issue"
        )

    return add_issue_support(db, issue_id, current_user.id)

@router.post("/{issue_id}/updates", response_model=IssueUpdateRead, status_code=status.HTTP_201_CREATED)
def add_update(
    issue_id: int,
    update_data: IssueUpdateCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Add an update to an issue.
    Authentication and community membership required.
    Only the creator or an administrator can add updates.
    """
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )

    # Verify that the user is a member of at least one of the issue's communities
    user_communities = db.exec(
        select(UserCommunityLink.community_id)
        .where(UserCommunityLink.user_id == current_user.id)
    ).all()
    user_community_ids = set(uc.community_id for uc in user_communities)
    
    issue_communities = db.exec(
        select(IssueCommunityLink.community_id)
        .where(IssueCommunityLink.issue_id == issue_id)
    ).all()
    issue_community_ids = set(ic.community_id for ic in issue_communities)
    
    if not user_community_ids.intersection(issue_community_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of the community to update this issue"
        )
    
    # Verify permissions to add updates
    if issue.creator_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to add updates to this issue"
        )
    
    return add_issue_update(db, issue_id, current_user.id, update_data) 