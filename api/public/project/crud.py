from sqlmodel import Session, select, func, distinct
from api.public.project.models import (
    Project, ProjectStep, ProjectResource, ProjectCommitment, 
    ProjectDonation, ProjectCreate, ProjectUpdate, 
    ProjectCommitmentCreate, ProjectDonationCreate, ProjectRead,
    UserMinimal, CommunityMinimal, ProjectStepRead, 
    ProjectResourceRead, ProjectCommitmentRead, ProjectDonationRead
)
from api.public.community.models import Community
from api.public.user.models import User
from api.utils.slug import create_slug
from datetime import datetime
from fastapi import HTTPException, status
from api.public.community.crud import get_community_by_id
from api.public.country.crud import get_country_by_code
from api.public.region.crud import get_region_by_id
from api.public.subregion.crud import get_subregion_by_id
from api.public.locality.models import Locality
from api.utils.generic_models import ProjectCommunityLink
from api.public.country.models import Country
from math import ceil
import random
import string

def get_all_projects(
    db: Session, 
    status = None,
    scope = None,
    community_id = None,
    creator_id = None,
    search = None,
    current_user_id = None,
    page: int = 1,
    size: int = 10
):
    """
    Retrieves all projects with pagination and optional filters
    """
    # Calculate offset for pagination
    offset = (page - 1) * size

    # First, get the total number of projects for pagination
    total_query = select(func.count(Project.id)).where(Project.id > 0)  # Base condition to add filters
    
    if status:
        total_query = total_query.where(Project.status == status)
    
    if scope:
        total_query = total_query.where(Project.scope == scope)
    
    if community_id:
        total_query = total_query.join(ProjectCommunityLink).where(ProjectCommunityLink.community_id == community_id)
    
    if creator_id:
        total_query = total_query.where(Project.creator_id == creator_id)
    
    if search:
        total_query = total_query.where(
            Project.title.contains(search) | Project.description.contains(search)
        )
    
    total = db.exec(total_query).first() or 0
    total_pages = ceil(total / size)

    # Main query to get the projects
    projects_query = select(Project).where(Project.id > 0)
    
    if status:
        projects_query = projects_query.where(Project.status == status)
    
    if scope:
        projects_query = projects_query.where(Project.scope == scope)
    
    if community_id:
        projects_query = projects_query.join(ProjectCommunityLink).where(ProjectCommunityLink.community_id == community_id)
    
    if creator_id:
        projects_query = projects_query.where(Project.creator_id == creator_id)
    
    if search:
        projects_query = projects_query.where(
            Project.title.contains(search) | Project.description.contains(search)
        )
    
    # Add sorting and pagination
    projects_query = projects_query.order_by(Project.created_at.desc()).offset(offset).limit(size)
    
    projects = db.exec(projects_query).all()
    
    return {
        "items": [enrich_project(db, project) for project in projects],
        "total": total,
        "page": page,
        "size": size,
        "pages": total_pages
    }

def get_project_by_filters(
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
    Retrieves projects with specific geographic filters (country, region, etc.)
    """
    # Calculate offset for pagination
    offset = (page - 1) * size

    # Base for the queries
    base_query = select(Project).where(Project.id > 0)
    count_query = select(func.count(Project.id)).where(Project.id > 0)
    
    # Apply common filters
    if status:
        base_query = base_query.where(Project.status == status)
        count_query = count_query.where(Project.status == status)
    
    if scope:
        base_query = base_query.where(Project.scope == scope)
        count_query = count_query.where(Project.scope == scope)
    
    if creator_id:
        base_query = base_query.where(Project.creator_id == creator_id)
        count_query = count_query.where(Project.creator_id == creator_id)
    
    if search:
        search_filter = Project.title.contains(search) | Project.description.contains(search)
        base_query = base_query.where(search_filter)
        count_query = count_query.where(search_filter)

    # Apply geographic filters
    if community_id:
        base_query = base_query.join(ProjectCommunityLink).where(ProjectCommunityLink.community_id == community_id)
        count_query = count_query.join(ProjectCommunityLink).where(ProjectCommunityLink.community_id == community_id)
    
    if country_code:
        country = get_country_by_code(db, country_code)
        if country and country.community:
            base_query = base_query.join(ProjectCommunityLink).where(ProjectCommunityLink.community_id == country.community.id)
            count_query = count_query.join(ProjectCommunityLink).where(ProjectCommunityLink.community_id == country.community.id)
    
    if region_id:
        region = get_region_by_id(db, region_id)
        if region and region.community:
            base_query = base_query.join(ProjectCommunityLink).where(ProjectCommunityLink.community_id == region.community.id)
            count_query = count_query.join(ProjectCommunityLink).where(ProjectCommunityLink.community_id == region.community.id)
    
    if subregion_id:
        subregion = get_subregion_by_id(db, subregion_id)
        if subregion and subregion.community:
            base_query = base_query.join(ProjectCommunityLink).where(ProjectCommunityLink.community_id == subregion.community.id)
            count_query = count_query.join(ProjectCommunityLink).where(ProjectCommunityLink.community_id == subregion.community.id)
    
    if locality_id:
        locality = db.get(Locality, locality_id)
        if locality and locality.community:
            base_query = base_query.join(ProjectCommunityLink).where(ProjectCommunityLink.community_id == locality.community.id)
            count_query = count_query.join(ProjectCommunityLink).where(ProjectCommunityLink.community_id == locality.community.id)
    
    # Execute count query
    total = db.exec(count_query).first() or 0
    total_pages = ceil(total / size)
    
    # Finalize and execute main query
    projects_query = base_query.order_by(Project.created_at.desc()).offset(offset).limit(size)
    projects = db.exec(projects_query).all()
    
    return {
        "items": [enrich_project(db, project) for project in projects],
        "total": total,
        "page": page,
        "size": size,
        "pages": total_pages
    }

def create_project(db: Session, project_data: ProjectCreate, user_id: int) -> Project:
    """
    Creates a new project with its steps and resources
    """
    # Generate unique slug
    slug = create_slug(project_data.title)
    
    # Check if the slug already exists
    existing = db.exec(select(Project).where(Project.slug == slug)).first()
    if existing:
        # Add random suffix if the slug already exists
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        slug = f"{slug}-{random_suffix}"
    
    # Create project
    new_project = Project(
        title=project_data.title,
        description=project_data.description,
        status=project_data.status,
        goal_amount=project_data.goal_amount,
        current_amount=0.0,
        scope=project_data.scope,
        slug=slug,
        creator_id=user_id,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )
    db.add(new_project)
    db.flush()  # Get generated ID
    
    # Add communities based on the project's scope
    if project_data.scope == "INTERNATIONAL" and project_data.country_codes:
        for code in project_data.country_codes:
            country = get_country_by_code(db, code)
            if country and country.community:
                new_project.communities.append(country.community)
    
    elif project_data.scope == "NATIONAL" and project_data.country_code:
        country = get_country_by_code(db, project_data.country_code)
        if country and country.community:
            new_project.communities.append(country.community)
    
    elif project_data.scope == "REGIONAL" and project_data.region_id:
        region = get_region_by_id(db, project_data.region_id)
        if region and region.community:
            new_project.communities.append(region.community)
    
    elif project_data.scope == "SUBREGIONAL" and project_data.subregion_id:
        subregion = get_subregion_by_id(db, project_data.subregion_id)
        if subregion and subregion.community:
            new_project.communities.append(subregion.community)
    
    elif project_data.scope == "LOCAL" and project_data.locality_id:
        locality = db.get(Locality, project_data.locality_id)
        if locality and locality.community:
            new_project.communities.append(locality.community)
    
    # Add additional communities
    for community_id in project_data.community_ids:
        community = get_community_by_id(db, community_id)
        if community:
            new_project.communities.append(community)
    
    # Create project steps with their resources
    for step_data in project_data.steps:
        new_step = ProjectStep(
            project_id=new_project.id,
            title=step_data.title,
            description=step_data.description,
            order=step_data.order,
            status=step_data.status
        )
        db.add(new_step)
        db.flush()  # Get generated ID
        
        # Add resources to the step
        for resource_data in step_data.resources:
            new_resource = ProjectResource(
                step_id=new_step.id,
                type=resource_data.type,
                description=resource_data.description,
                quantity=resource_data.quantity,
                unit=resource_data.unit
            )
            db.add(new_resource)
    
    db.commit()
    db.refresh(new_project)
    
    return enrich_project(db, new_project)

def get_project_by_id_or_slug(db: Session, id_or_slug: str) -> Project:
    """
    Retrieves a project by ID or slug
    """
    # Determine if it is ID or slug
    if id_or_slug.isdigit():
        project = db.get(Project, int(id_or_slug))
    else:
        project = db.exec(select(Project).where(Project.slug == id_or_slug)).first()
    
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    return project

def update_project(db: Session, project_id: int, project_data: ProjectUpdate) -> Project:
    """
    Updates an existing project
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Update basic fields
    update_data = project_data.dict(exclude_unset=True)
    
    # Handle communities if provided
    if "community_ids" in update_data:
        community_ids = update_data.pop("community_ids")
        # Clear current communities
        project.communities = []
        # Add new communities
        for community_id in community_ids:
            community = get_community_by_id(db, community_id)
            if community:
                project.communities.append(community)
    
    # Apply updates to basic fields
    for key, value in update_data.items():
        setattr(project, key, value)
    
    # Update timestamp
    project.updated_at = datetime.utcnow()
    
    db.add(project)
    db.commit()
    db.refresh(project)
    
    return enrich_project(db, project)

def delete_project(db: Session, project_id: int) -> None:
    """
    Deletes a project
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    db.delete(project)
    db.commit()

def add_project_commitment(db: Session, project_id: int, user_id: int, commitment_data: ProjectCommitmentCreate):
    """
    Adds a commitment to a project
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Create the commitment
    new_commitment = ProjectCommitment(
        project_id=project_id,
        user_id=user_id,
        type=commitment_data.type,
        description=commitment_data.description,
        quantity=commitment_data.quantity,
        unit=commitment_data.unit,
        fulfilled=False
    )
    
    db.add(new_commitment)
    db.commit()
    db.refresh(new_commitment)
    
    return new_commitment

def add_project_donation(db: Session, project_id: int, user_id: int, donation_data: ProjectDonationCreate):
    """
    Adds a donation to a project and updates the current amount
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Project not found"
        )
    
    # Create the donation
    new_donation = ProjectDonation(
        project_id=project_id,
        user_id=user_id,
        amount=donation_data.amount,
        donated_at=datetime.utcnow()
    )
    
    db.add(new_donation)
    
    # Update current amount of the project
    project.current_amount += donation_data.amount
    db.add(project)
    
    db.commit()
    db.refresh(new_donation)
    
    return new_donation

def enrich_project(db: Session, project: Project) -> ProjectRead:
    """
    Enriches a project with additional information to be displayed
    """
    # Get creator
    creator = db.get(User, project.creator_id)
    
    # Get project steps with their resources
    steps = []
    for step in project.steps:
        resources = []
        for resource in step.resources:
            resources.append(ProjectResourceRead(
                id=resource.id,
                type=resource.type,
                description=resource.description,
                quantity=resource.quantity,
                unit=resource.unit
            ))
        
        steps.append(ProjectStepRead(
            id=step.id,
            title=step.title,
            description=step.description,
            order=step.order,
            status=step.status,
            resources=resources
        ))
    
    # Get commitments
    commitments = []
    for commitment in project.commitments:
        user = db.get(User, commitment.user_id)
        if user:
            commitments.append(ProjectCommitmentRead(
                id=commitment.id,
                user=UserMinimal(
                    id=user.id,
                    username=user.username,
                    image=user.image
                ),
                type=commitment.type,
                description=commitment.description,
                quantity=commitment.quantity,
                unit=commitment.unit,
                fulfilled=commitment.fulfilled
            ))
    
    # Get donations
    donations = []
    for donation in project.donations:
        user = db.get(User, donation.user_id)
        if user:
            donations.append(ProjectDonationRead(
                id=donation.id,
                user=UserMinimal(
                    id=user.id,
                    username=user.username,
                    image=user.image
                ),
                amount=donation.amount,
                donated_at=donation.donated_at
            ))
    
    # Get communities
    communities = []
    for community in project.communities:
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
    
    # Build response
    return ProjectRead(
        id=project.id,
        title=project.title,
        description=project.description,
        slug=project.slug,
        status=project.status,
        goal_amount=project.goal_amount,
        current_amount=project.current_amount,
        scope=project.scope,
        views_count=project.views_count,
        created_at=project.created_at,
        updated_at=project.updated_at,
        creator=UserMinimal(
            id=creator.id,
            username=creator.username,
            image=creator.image
        ),
        steps=steps,
        commitments=commitments,
        donations=donations,
        communities=communities
    )
