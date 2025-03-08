from sqlmodel import Session, select, func, distinct
from api.public.issue.models import (
    Issue, IssueCreate, IssueUpdate, 
    IssueComment, IssueCommentCreate, IssueSupport,
    IssueUpdate as IssueUpdateModel, IssueUpdateCreate,
    IssueRead, IssueCommentRead, IssueUpdateRead,
    UserMinimal
)
from api.public.community.models import Community
from api.public.user.models import User
from api.public.organization.models import Organization
from api.public.organization.crud import get_organization_by_id
from api.utils.slug import create_slug
from datetime import datetime
from fastapi import HTTPException, status
from api.public.community.crud import get_community_by_id
from api.public.country.crud import get_country_by_code
from api.public.region.crud import get_region_by_id
from api.public.subregion.crud import get_subregion_by_id
from api.public.locality.models import Locality
from api.public.country.models import Country
from math import ceil
import random
import string

def get_all_issues(
    db: Session,
    status = None,
    scope = None,
    community_id = None,
    country_code = None,
    region_id = None,
    subregion_id = None,
    locality_id = None,
    creator_id = None,
    search = None,
    current_user_id = None,
    page: int = 1,
    size: int = 10
):
    """
    Retrieves all issues with pagination and optional filters
    """
    # Calculate offset for pagination
    offset = (page - 1) * size

    # First, get the total number of issues for pagination
    total_query = select(func.count(Issue.id)).where(Issue.id > 0)  # Base condition to add filters
    
    if status:
        total_query = total_query.where(Issue.status == status)
    
    if community_id:
        total_query = total_query.join(IssueCommunityLink).where(IssueCommunityLink.community_id == community_id)
    
    if creator_id:
        total_query = total_query.where(Issue.creator_id == creator_id)
    
    if search:
        total_query = total_query.where(
            Issue.title.contains(search) | Issue.description.contains(search)
        )
    
    # Apply geographic filters
    if country_code:
        country = get_country_by_code(db, country_code)
        if country and country.community:
            total_query = total_query.join(IssueCommunityLink).where(IssueCommunityLink.community_id == country.community.id)
    
    if region_id:
        region = get_region_by_id(db, region_id)
        if region and region.community:
            total_query = total_query.join(IssueCommunityLink).where(IssueCommunityLink.community_id == region.community.id)
    
    if subregion_id:
        subregion = get_subregion_by_id(db, subregion_id)
        if subregion and subregion.community:
            total_query = total_query.join(IssueCommunityLink).where(IssueCommunityLink.community_id == subregion.community.id)
    
    if locality_id:
        locality = db.get(Locality, locality_id)
        if locality and locality.community:
            total_query = total_query.join(IssueCommunityLink).where(IssueCommunityLink.community_id == locality.community.id)
    
    total = db.exec(total_query).first() or 0
    total_pages = ceil(total / size)

    # Main query to get the issues
    issues_query = select(Issue).where(Issue.id > 0)
    
    if status:
        issues_query = issues_query.where(Issue.status == status)
    
    if community_id:
        issues_query = issues_query.join(IssueCommunityLink).where(IssueCommunityLink.community_id == community_id)
    
    if creator_id:
        issues_query = issues_query.where(Issue.creator_id == creator_id)
    
    if search:
        issues_query = issues_query.where(
            Issue.title.contains(search) | Issue.description.contains(search)
        )
    
    # Apply the same geographic filters to the main query
    if country_code:
        country = get_country_by_code(db, country_code)
        if country and country.community:
            issues_query = issues_query.join(IssueCommunityLink).where(IssueCommunityLink.community_id == country.community.id)
    
    if region_id:
        region = get_region_by_id(db, region_id)
        if region and region.community:
            issues_query = issues_query.join(IssueCommunityLink).where(IssueCommunityLink.community_id == region.community.id)
    
    if subregion_id:
        subregion = get_subregion_by_id(db, subregion_id)
        if subregion and subregion.community:
            issues_query = issues_query.join(IssueCommunityLink).where(IssueCommunityLink.community_id == subregion.community.id)
    
    if locality_id:
        locality = db.get(Locality, locality_id)
        if locality and locality.community:
            issues_query = issues_query.join(IssueCommunityLink).where(IssueCommunityLink.community_id == locality.community.id)
    
    # Add sorting and pagination
    issues_query = issues_query.order_by(Issue.created_at.desc()).offset(offset).limit(size)
    
    issues = db.exec(issues_query).all()
    
    return {
        "items": [enrich_issue(db, issue, current_user_id) for issue in issues],
        "total": total,
        "page": page,
        "size": size,
        "pages": total_pages
    }

def create_issue(db: Session, issue_data: IssueCreate, user_id: int) -> Issue:
    """
    Creates a new issue
    """
    # Generate unique slug
    slug = create_slug(issue_data.title)
    
    # Check if the slug already exists
    existing = db.exec(select(Issue).where(Issue.slug == slug)).first()
    if existing:
        # Add random suffix if the slug already exists
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        slug = f"{slug}-{random_suffix}"
    
    # Create issue
    new_issue = Issue(
        title=issue_data.title,
        description=issue_data.description,
        status=issue_data.status,
        priority=issue_data.priority,
        scope=issue_data.scope,
        slug=slug,
        creator_id=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
        location=issue_data.location,
        images=issue_data.images,
        organization_id=issue_data.organization_id
    )
    db.add(new_issue)
    db.flush()  # Get generated ID
    
    # Add communities based on the issue's scope
    if issue_data.scope == "INTERNATIONAL" and issue_data.country_codes:
        for code in issue_data.country_codes:
            country = get_country_by_code(db, code)
            if country and country.community:
                new_issue.communities.append(country.community)
    
    elif issue_data.scope == "NATIONAL" and issue_data.country_code:
        country = get_country_by_code(db, issue_data.country_code)
        if country and country.community:
            new_issue.communities.append(country.community)
    
    elif issue_data.scope == "REGIONAL" and issue_data.region_id:
        region = get_region_by_id(db, issue_data.region_id)
        if region and region.community:
            new_issue.communities.append(region.community)
    
    elif issue_data.scope == "SUBREGIONAL" and issue_data.subregion_id:
        subregion = get_subregion_by_id(db, issue_data.subregion_id)
        if subregion and subregion.community:
            new_issue.communities.append(subregion.community)
    
    elif issue_data.scope == "LOCAL" and issue_data.locality_id:
        locality = db.get(Locality, issue_data.locality_id)
        if locality and locality.community:
            new_issue.communities.append(locality.community)
    
    # Add additional communities
    for community_id in issue_data.community_ids:
        community = get_community_by_id(db, community_id)
        if community:
            new_issue.communities.append(community)
    
    db.commit()
    db.refresh(new_issue)
    
    return enrich_issue(db, new_issue, user_id)

def get_issue_by_id_or_slug(db: Session, id_or_slug: str, current_user_id: int = None) -> Issue:
    """
    Retrieves an issue by ID or slug
    """
    # Determine if it is ID or slug
    if id_or_slug.isdigit():
        issue = db.get(Issue, int(id_or_slug))
    else:
        issue = db.exec(select(Issue).where(Issue.slug == id_or_slug)).first()
    
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    return enrich_issue(db, issue, current_user_id)

def update_issue(db: Session, issue_id: int, issue_data: IssueUpdate, current_user_id: int) -> Issue:
    """
    Updates an existing issue
    """
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    # Update basic fields
    update_data = issue_data.dict(exclude_unset=True)
    
    # Handle communities if provided
    if "community_ids" in update_data:
        community_ids = update_data.pop("community_ids")
        # Clear current communities
        issue.communities = []
        # Add new communities
        for community_id in community_ids:
            community = get_community_by_id(db, community_id)
            if community:
                issue.communities.append(community)
    
    # Apply updates to basic fields
    for key, value in update_data.items():
        setattr(issue, key, value)
    
    # Update timestamp
    issue.updated_at = datetime.utcnow()
    
    # Create an update record
    issue_update = IssueUpdateModel(
        issue_id=issue_id,
        user_id=current_user_id,
        content=f"Issue updated: {', '.join(update_data.keys())}",
        created_at=datetime.utcnow()
    )
    db.add(issue_update)
    
    db.add(issue)
    db.commit()
    db.refresh(issue)
    
    return enrich_issue(db, issue, current_user_id)

def delete_issue(db: Session, issue_id: int) -> None:
    """
    Deletes an issue
    """
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    db.delete(issue)
    db.commit()

def add_issue_comment(db: Session, issue_id: int, user_id: int, comment_data: IssueCommentCreate):
    """
    Adds a comment to an issue
    """
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    # Create the comment
    new_comment = IssueComment(
        issue_id=issue_id,
        user_id=user_id,
        content=comment_data.content,
        created_at=datetime.utcnow()
    )
    
    db.add(new_comment)
    db.commit()
    db.refresh(new_comment)
    
    # Get user for the enriched comment
    user = db.get(User, user_id)
    
    return IssueCommentRead(
        id=new_comment.id,
        content=new_comment.content,
        created_at=new_comment.created_at,
        user=UserMinimal(
            id=user.id,
            username=user.username,
            image=user.image
        )
    )

def add_issue_support(db: Session, issue_id: int, user_id: int):
    """
    Adds support to an issue (or removes it if already supported)
    """
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    # Check if user already supports this issue
    existing_support = db.exec(
        select(IssueSupport)
        .where(
            IssueSupport.issue_id == issue_id,
            IssueSupport.user_id == user_id
        )
    ).first()
    
    if existing_support:
        # Remove support if already exists
        db.delete(existing_support)
        db.commit()
        return {"supported": False, "supports_count": issue.supports_count - 1}
    else:
        # Add support
        new_support = IssueSupport(
            issue_id=issue_id,
            user_id=user_id,
            created_at=datetime.utcnow()
        )
        db.add(new_support)
        
        # Update issue support count
        issue.supports_count += 1
        db.add(issue)
        
        db.commit()
        return {"supported": True, "supports_count": issue.supports_count}

def add_issue_update(db: Session, issue_id: int, user_id: int, update_data: IssueUpdateCreate):
    """
    Adds an update to an issue
    """
    issue = db.get(Issue, issue_id)
    if not issue:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Issue not found"
        )
    
    # Create the update
    new_update = IssueUpdateModel(
        issue_id=issue_id,
        user_id=user_id,
        content=update_data.content,
        created_at=datetime.utcnow()
    )
    
    db.add(new_update)
    db.commit()
    db.refresh(new_update)
    
    # Get user for the enriched update
    user = db.get(User, user_id)
    
    return IssueUpdateRead(
        id=new_update.id,
        content=new_update.content,
        created_at=new_update.created_at,
        user=UserMinimal(
            id=user.id,
            username=user.username,
            image=user.image
        )
    )

def enrich_issue(db: Session, issue: Issue, current_user_id: int = None) -> IssueRead:
    """
    Enriches an issue with additional information to be displayed
    """
    # Get creator
    creator = db.get(User, issue.creator_id)
    
    # Get comments
    comments = []
    for comment in issue.comments:
        user = db.get(User, comment.user_id)
        if user:
            comments.append(IssueCommentRead(
                id=comment.id,
                content=comment.content,
                created_at=comment.created_at,
                user=UserMinimal(
                    id=user.id,
                    username=user.username,
                    image=user.image
                )
            ))
    
    # Get updates
    updates = []
    for update in issue.updates:
        user = db.get(User, update.user_id)
        if user:
            updates.append(IssueUpdateRead(
                id=update.id,
                content=update.content,
                created_at=update.created_at,
                user=UserMinimal(
                    id=user.id,
                    username=user.username,
                    image=user.image
                )
            ))
    
    # Get communities
    communities = []
    for community in issue.communities:
        # Find the country associated with this community
        cca2 = None
        country = db.exec(
            select(Country)
            .where(Country.community_id == community.id)
        ).first()
        if country:
            cca2 = country.cca2
            
        communities.append(CommunityMinimal(
            id=community.id,
            name=community.name,
            cca2=cca2
        ))
    
    # Get organization
    organization = db.get(Organization, issue.organization_id)
    
    # Check if current user supports this issue
    user_supports = False
    if current_user_id:
        support = db.exec(
            select(IssueSupport)
            .where(
                IssueSupport.issue_id == issue.id,
                IssueSupport.user_id == current_user_id
            )
        ).first()
        user_supports = support is not None
    
    # Build response
    return IssueRead(
        id=issue.id,
        title=issue.title,
        description=issue.description,
        slug=issue.slug,
        status=issue.status,
        priority=issue.priority,
        scope=issue.scope,
        location=issue.location,
        images=issue.images,
        supports_count=issue.supports_count,
        views_count=issue.views_count,
        created_at=issue.created_at,
        updated_at=issue.updated_at,
        creator=UserMinimal(
            id=creator.id,
            username=creator.username,
            image=creator.image
        ),
        communities=communities,
        comments=comments,
        updates=updates,
        user_supports=user_supports,
        organization=OrganizationRead(
            id=organization.id,
            name=organization.name,
            level=organization.level
        )
    ) 