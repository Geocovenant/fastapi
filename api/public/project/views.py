from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlmodel import Session, select
from datetime import datetime
from typing import Optional
from api.database import get_session
from api.auth.dependencies import get_current_user, get_current_user_optional
from api.public.user.models import User, UserRole
from api.public.project.models import (
    ProjectCreate, ProjectRead, ProjectUpdate, 
    ProjectStatus, ProjectCommitmentCreate,
    ProjectDonationCreate, ProjectComment, ProjectCommentCreate, ProjectCommentRead
)
from api.public.project.crud import (
    get_all_projects, create_project, get_project_by_id_or_slug, 
    update_project, delete_project, add_project_commitment,
    add_project_donation, get_project_by_filters
)
from api.utils.slug import create_slug
from api.public.user.models import UserCommunityLink
from api.public.project.models import ProjectCommunityLink
from api.utils.shared_models import UserMinimal

router = APIRouter()

@router.get("/")
def read_projects(
    status: Optional[ProjectStatus] = None,
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
    Get projects with optional filters and pagination.
    - status: Filter by project status
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
    if any([country_code, region_id, subregion_id, locality_id]):
        return get_project_by_filters(
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
    
    return get_all_projects(
        db, 
        status=status,
        scope=scope,
        community_id=community_id,
        creator_id=creator_id,
        search=search,
        current_user_id=current_user.id if current_user else None,
        page=page,
        size=size
    )

@router.post("/", response_model=ProjectRead, status_code=status.HTTP_201_CREATED)
def create_new_project(
    project_data: ProjectCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Create a new project.
    Authentication required.
    """
    return create_project(db, project_data, current_user.id)

@router.get("/{project_id_or_slug}", response_model=ProjectRead)
def get_project(
    project_id_or_slug: str,
    current_user: User | None = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """
    Get a specific project by ID or slug.
    No authentication required.
    """
    project = get_project_by_id_or_slug(db, project_id_or_slug)
    
    # Increment view counter
    project.views_count += 1
    db.add(project)
    db.commit()
    db.refresh(project)
    
    return project

@router.patch("/{project_id}", response_model=ProjectRead)
def update_project_details(
    project_id: int,
    project_data: ProjectUpdate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Update an existing project.
    Only the creator or an administrator can edit the project.
    """
    project = get_project_by_id_or_slug(db, str(project_id))
    
    # Verify permissions
    if project.creator_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to edit this project"
        )
    
    return update_project(db, project_id, project_data)

@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_project_endpoint(
    project_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Delete a project.
    Only the creator or an administrator can delete the project.
    """
    project = get_project_by_id_or_slug(db, str(project_id))
    
    # Verify permissions
    if project.creator_id != current_user.id and current_user.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You don't have permission to delete this project"
        )
    
    delete_project(db, project_id)

@router.post("/{project_id}/commitments", status_code=status.HTTP_201_CREATED)
def add_commitment(
    project_id: int,
    commitment_data: ProjectCommitmentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Add a commitment to a project.
    Authentication and membership in the project's community are required.
    """
    project = get_project_by_id_or_slug(db, str(project_id))
    
    # Verify that the user is a member of at least one of the project's communities
    user_communities = db.exec(
        select(UserCommunityLink.community_id)
        .where(UserCommunityLink.user_id == current_user.id)
    ).all()
    user_community_ids = set(uc.community_id for uc in user_communities)
    
    project_communities = db.exec(
        select(ProjectCommunityLink.community_id)
        .where(ProjectCommunityLink.project_id == project_id)
    ).all()
    project_community_ids = set(pc.community_id for pc in project_communities)
    
    if not user_community_ids.intersection(project_community_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of the community to commit to this project"
        )
    
    # Verify that the project is open
    if project.status != ProjectStatus.OPEN:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Commitments can only be added to open projects"
        )
    
    return add_project_commitment(db, project_id, current_user.id, commitment_data)

@router.post("/{project_id}/donations", status_code=status.HTTP_201_CREATED)
def add_donation(
    project_id: int,
    donation_data: ProjectDonationCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Add a donation to a project.
    Authentication and membership in the project's community are required.
    """
    project = get_project_by_id_or_slug(db, str(project_id))
    
    # Verify that the user is a member of at least one of the project's communities
    user_communities = db.exec(
        select(UserCommunityLink.community_id)
        .where(UserCommunityLink.user_id == current_user.id)
    ).all()
    user_community_ids = set(uc.community_id for uc in user_communities)
    
    project_communities = db.exec(
        select(ProjectCommunityLink.community_id)
        .where(ProjectCommunityLink.project_id == project_id)
    ).all()
    project_community_ids = set(pc.community_id for pc in project_communities)
    
    if not user_community_ids.intersection(project_community_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of the community to donate to this project"
        )
    
    # Verify that the project is open or in progress
    if project.status not in [ProjectStatus.OPEN, ProjectStatus.IN_PROGRESS]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Donations can only be made to open or in-progress projects"
        )
    
    return add_project_donation(db, project_id, current_user.id, donation_data)

@router.post("/{project_id}/comments", response_model=ProjectCommentRead)
def add_project_comment(
    project_id: int,
    comment_data: ProjectCommentCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Add a comment to a project.
    Authentication and membership in the project's community are required.
    """
    project = get_project_by_id_or_slug(db, str(project_id))
    
    # Verify that the user is a member of at least one of the project's communities
    user_communities = db.exec(
        select(UserCommunityLink.community_id)
        .where(UserCommunityLink.user_id == current_user.id)
    ).all()
    user_community_ids = set(uc.community_id for uc in user_communities)
    
    project_communities = db.exec(
        select(ProjectCommunityLink.community_id)
        .where(ProjectCommunityLink.project_id == project_id)
    ).all()
    project_community_ids = set(pc.community_id for pc in project_communities)
    
    if not user_community_ids.intersection(project_community_ids):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You must be a member of the community to comment on this project"
        )
    
    new_comment = ProjectComment(
        project_id=project_id,
        user_id=current_user.id,
        content=comment_data.content,
        created_at=datetime.utcnow()
    )
    
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    
    return ProjectCommentRead(
        id=new_comment.id,
        content=new_comment.content,
        created_at=new_comment.created_at,
        user=UserMinimal(
            id=current_user.id,
            username=current_user.username,
            image=current_user.image
        ),
        can_edit=True
    )
