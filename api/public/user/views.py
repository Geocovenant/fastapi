from fastapi import APIRouter, Depends, HTTPException, Path, Body, Query, status
from sqlmodel import Session, select, func
from typing import Optional
import re
import random
from api.database import get_session
from api.auth.dependencies import get_current_user, get_current_user_optional
from api.public.user.models import User, UserFollowLink, UserUpdateSchema, UsernameUpdateSchema, GenerateUsernameSchema
from api.public.community.models import Community
from api.utils.generic_models import UserFollowLink, UserCommunityLink

# Imports for activity statistics
from api.public.debate.models import Debate, Opinion, PointOfView
from api.public.poll.models import Poll, PollVote
from api.public.project.models import Project, ProjectCommitment, ProjectDonation
from api.public.issue.models import Issue, IssueSupport, IssueComment

router = APIRouter()

@router.get("/me")
def read_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Get information about the currently authenticated user.
    Authentication required.
    Includes the list of communities the user belongs to.
    """
    # Convert the current user to a dictionary
    user_data = current_user.dict()

    # Get the user's communities with visibility information
    communities_query = select(
        Community, UserCommunityLink.is_public
    ).join(
        UserCommunityLink
    ).where(
        UserCommunityLink.user_id == current_user.id
    )
    
    communities_result = db.exec(communities_query).all()
    
    # Format the communities for the response
    user_data["communities"] = [
        {
            "id": community.id,
            "name": community.name,
            "level": community.level,
            "description": community.description,
            "is_public": is_public
        }
        for community, is_public in communities_result
    ]

    return user_data

@router.get("/{username}")
def get_user_profile(
    username: str = Path(..., description="Username to query"),
    current_user: Optional[User] = Depends(get_current_user_optional),
    db: Session = Depends(get_session)
):
    """
    Get information about a user profile by username.
    No authentication required, but if the user is authenticated, 
    additional information will be included such as if they follow the user.
    For communities:
    - If viewing own profile: shows all communities
    - If viewing other profile: shows only public communities
    """
    # Find user by username
    user = db.exec(select(User).where(User.username == username)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with username '{username}' not found"
        )
    
    # Create a copy of the user to manipulate the response
    user_data = user.dict()
    
    # Count followers and following
    followers_count = db.exec(
        select(func.count()).where(UserFollowLink.followed_id == user.id)
    ).first()
    
    following_count = db.exec(
        select(func.count()).where(UserFollowLink.follower_id == user.id)
    ).first()
    
    # Add counts to the response
    user_data["followers_count"] = followers_count or 0
    user_data["following_count"] = following_count or 0
    
    # Add is_following field (default to False if not authenticated)
    user_data["is_following"] = False
    
    # If there is an authenticated user, check if they follow the queried user
    if current_user and current_user.id != user.id:  # Don't check if user follows themselves
        # Check if the authenticated user follows the queried user
        is_following = db.exec(
            select(UserFollowLink).where(
                UserFollowLink.follower_id == current_user.id,
                UserFollowLink.followed_id == user.id
            )
        ).first() is not None
        
        # Update is_following field in the response
        user_data["is_following"] = is_following
    
    # Get the user's communities
    communities_query = select(
        Community, UserCommunityLink.is_public
    ).join(
        UserCommunityLink
    ).where(
        UserCommunityLink.user_id == user.id
    )
    
    # If not the user's own profile, filter only public communities
    if not current_user or current_user.id != user.id:
        communities_query = communities_query.where(UserCommunityLink.is_public == True)
    
    communities_result = db.exec(communities_query).all()
    
    # Format the communities for the response
    user_data["communities"] = [
        {
            "id": community.id,
            "name": community.name,
            "level": community.level,
            "description": community.description,
            "is_public": is_public
        }
        for community, is_public in communities_result
    ]
    
    # Add activity statistics on the platform
    
    # Poll statistics
    polls_created_count = db.exec(
        select(func.count()).where(func.poll.c.creator_id == user.id)
    ).first() or 0
    
    polls_voted_count = db.exec(
        select(func.count()).where(func.poll_vote.c.user_id == user.id)
    ).first() or 0
    
    # Debate statistics
    debates_created_count = db.exec(
        select(func.count()).where(func.debate.c.creator_id == user.id)
    ).first() or 0
    
    debate_opinions_count = db.exec(
        select(func.count())
        .select_from(
            select(Opinion)
            .join(PointOfView)
            .where(Opinion.user_id == user.id)
            .subquery()
        )
    ).first() or 0
    
    # Project statistics
    projects_created_count = db.exec(
        select(func.count()).where(func.project.c.creator_id == user.id)
    ).first() or 0
    
    project_commitments_count = db.exec(
        select(func.count()).where(func.project_commitment.c.user_id == user.id)
    ).first() or 0
    
    project_donations_count = db.exec(
        select(func.count()).where(func.project_donation.c.user_id == user.id)
    ).first() or 0
    
    # Issue statistics
    issues_created_count = db.exec(
        select(func.count()).where(func.issue.c.creator_id == user.id)
    ).first() or 0
    
    issue_supports_count = db.exec(
        select(func.count()).where(func.issue_support.c.user_id == user.id)
    ).first() or 0
    
    issue_comments_count = db.exec(
        select(func.count()).where(func.issue_comment.c.user_id == user.id)
    ).first() or 0
    
    # Add all statistics to the response object
    user_data["activity_stats"] = {
        "polls": {
            "created": polls_created_count,
            "voted": polls_voted_count,
            "total_participation": polls_created_count + polls_voted_count
        },
        "debates": {
            "created": debates_created_count,
            "opinions": debate_opinions_count,
            "total_participation": debates_created_count + debate_opinions_count
        },
        "projects": {
            "created": projects_created_count,
            "commitments": project_commitments_count,
            "donations": project_donations_count,
            "total_participation": projects_created_count + project_commitments_count + project_donations_count
        },
        "issues": {
            "created": issues_created_count,
            "supports": issue_supports_count,
            "comments": issue_comments_count,
            "total_participation": issues_created_count + issue_supports_count + issue_comments_count
        },
        "total_activity": (
            polls_created_count + polls_voted_count +
            debates_created_count + debate_opinions_count +
            projects_created_count + project_commitments_count + project_donations_count +
            issues_created_count + issue_supports_count + issue_comments_count
        )
    }
    
    return user_data

@router.post("/{username}/follow", status_code=status.HTTP_200_OK)
def follow_user(
    username: str = Path(..., description="Username to follow"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Follow a user. Authentication required.
    """
    # You can't follow yourself
    if current_user.username == username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot follow yourself"
        )
    
    # Find user to follow
    user_to_follow = db.exec(select(User).where(User.username == username)).first()
    if not user_to_follow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found"
        )
    
    # Check if already following
    existing_follow = db.exec(
        select(UserFollowLink).where(
            UserFollowLink.follower_id == current_user.id,
            UserFollowLink.followed_id == user_to_follow.id
        )
    ).first()
    
    if existing_follow:
        return {"message": f"You are already following {username}"}
    
    # Create follow relationship
    new_follow = UserFollowLink(follower_id=current_user.id, followed_id=user_to_follow.id)
    db.add(new_follow)
    db.commit()
    
    return {"message": f"You are now following {username}"}

@router.delete("/{username}/follow", status_code=status.HTTP_200_OK)
def unfollow_user(
    username: str = Path(..., description="Username to unfollow"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Unfollow a user. Authentication required.
    """
    # You can't unfollow yourself
    if current_user.username == username:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You cannot unfollow yourself"
        )
    
    # Find user to unfollow
    user_to_unfollow = db.exec(select(User).where(User.username == username)).first()
    if not user_to_unfollow:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User '{username}' not found"
        )
    
    # Find follow relationship
    follow = db.exec(
        select(UserFollowLink).where(
            UserFollowLink.follower_id == current_user.id,
            UserFollowLink.followed_id == user_to_unfollow.id
        )
    ).first()
    
    if not follow:
        return {"message": f"You are not following {username}"}
    
    # Remove follow relationship
    db.delete(follow)
    db.commit()
    
    return {"message": f"You have unfollowed {username}"}

@router.patch("/me", status_code=status.HTTP_200_OK)
def update_profile(
    update_data: UserUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Update the authenticated user's profile data. Authentication required.
    """
    # Get current user from database to ensure we have the most recent version
    user = db.get(User, current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update fields if present in the request
    user_data = update_data.dict(exclude_unset=True)
    for key, value in user_data.items():
        setattr(user, key, value)
    
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user

@router.post("/generate-username", status_code=status.HTTP_200_OK)
def generate_and_update_username(
    data: GenerateUsernameSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Generate and update the username for the authenticated user.
    Takes a proposed username and tries to assign it to the user.
    If the username is invalid or already taken, generates an alternative.
    Also adds the user to the global community (ID 1) if not already a member.
    """
    proposed_username = data.base_name.strip()
    
    # List of reserved words that cannot be used as a username
    reserved_words = ["anonymous", "admin", "system", "moderator", "support"]
    
    # Inappropriate words that should not be allowed
    inappropriate_words = ["profanity1", "profanity2", "badword"]  # Replace with real words
    
    # Check if the proposed username is in the list of reserved words
    if proposed_username.lower() in reserved_words:
        is_valid = False
    else:
        # Check if the proposed username contains inappropriate words
        contains_inappropriate = any(word.lower() in proposed_username.lower() for word in inappropriate_words)
        if contains_inappropriate:
            is_valid = False
        else:
            # Check if the proposed username is valid
            is_valid = re.match(r'^[a-zA-Z][a-zA-Z0-9_]{2,29}$', proposed_username) is not None
    
    # If proposed username is valid, check if it's available
    if is_valid:
        # Don't check against the current user's username
        username_exists = db.exec(
            select(User).where(
                User.username == proposed_username,
                User.id != current_user.id
            )
        ).first() is not None
        
        # If valid and available, update the user's username
        if not username_exists:
            user = db.get(User, current_user.id)
            user.username = proposed_username
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Check if the user is already a member of the global community (ID 1)
            # And add them if not
            _add_user_to_global_community(db, current_user.id)
            
            return {"username": proposed_username, "generated": False, "user": user}
    
    # If we're here, either the username is invalid or already taken
    # Clean the base name (remove special chars, replace spaces with underscore)
    base_username = re.sub(r'[^\w\s]', '', proposed_username.lower())
    base_username = re.sub(r'\s+', '_', base_username)
    
    # Ensure it starts with a letter (if it doesn't, add 'user_' prefix)
    if not base_username or not base_username[0].isalpha():
        base_username = f"user_{base_username}"
    
    # Ensure minimum length
    if len(base_username) < 3:
        base_username = f"{base_username}{'_' * (3 - len(base_username))}"
    
    # Truncate if too long
    if len(base_username) > 25:  # Leave room for potential numbers
        base_username = base_username[:25]
    
    # Check if generated username exists (excluding the current user)
    username_exists = db.exec(
        select(User).where(
            User.username == base_username,
            User.id != current_user.id
        )
    ).first() is not None
    
    # If base username is available, update the user
    if not username_exists:
        user = db.get(User, current_user.id)
        user.username = base_username
        db.add(user)
        db.commit()
        db.refresh(user)
        
        # Add user to the global community (ID 1)
        _add_user_to_global_community(db, current_user.id)
        
        return {"username": base_username, "generated": True, "user": user}
    
    # Try with numbers
    attempts = 0
    max_attempts = 20  # Prevent infinite loop
    
    while attempts < max_attempts:
        attempts += 1
        # First try sequential numbers, then random numbers for variety
        if attempts <= 10:
            new_username = f"{base_username}{attempts}"
        else:
            new_username = f"{base_username}{random.randint(1, 9999)}"
        
        username_exists = db.exec(
            select(User).where(
                User.username == new_username,
                User.id != current_user.id
            )
        ).first() is not None
        
        if not username_exists:
            user = db.get(User, current_user.id)
            user.username = new_username
            db.add(user)
            db.commit()
            db.refresh(user)
            
            # Add user to the global community (ID 1)
            _add_user_to_global_community(db, current_user.id)
            
            return {"username": new_username, "generated": True, "user": user}
    
    # If we reach here, we couldn't find an available username
    raise HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail="Could not generate a unique username. Please try with a different base name."
    )

# Helper function to add the user to the global community (ID 1)
def _add_user_to_global_community(db: Session, user_id: int):
    """
    Adds the user to the global community (ID 1) if they are not already a member.
    """
    # Check if the user is already a member of the global community
    existing_membership = db.exec(
        select(UserCommunityLink).where(
            UserCommunityLink.user_id == user_id,
            UserCommunityLink.community_id == 1  # ID 1 = global community
        )
    ).first()
    
    # If not a member, add them with private visibility (is_public=False)
    if not existing_membership:
        # Check that the global community exists
        community = db.exec(select(Community).where(Community.id == 1)).first()
        if community:  # Only add if the community exists
            new_membership = UserCommunityLink(
                user_id=user_id,
                community_id=1,
                is_public=False  # By default, the user is private in the community
            )
            db.add(new_membership)
            db.commit()

@router.patch("/me/username", status_code=status.HTTP_200_OK)
def update_username(
    update_data: UsernameUpdateSchema,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Update the username. Authentication required.
    Username must follow the format requirements and be unique.
    """
    # Validation is already handled by the UsernameUpdateSchema validator
    
    # Check if the new username already exists
    existing_user = db.exec(
        select(User).where(User.username == update_data.username)
    ).first()
    
    if existing_user and existing_user.id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username is already in use"
        )
    
    # Get current user from database
    user = db.get(User, current_user.id)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Update username
    user.username = update_data.username
    db.add(user)
    db.commit()
    db.refresh(user)
    
    return user

@router.patch("/me/community/{community_id}/visibility", status_code=status.HTTP_200_OK)
def update_community_visibility(
    community_id: int,
    is_public: bool = Body(..., embed=True),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_session)
):
    """
    Update the user's visibility in a specific community.
    """
    # Check that the community exists
    community = db.exec(select(Community).where(Community.id == community_id)).first()
    if not community:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Community with ID {community_id} not found"
        )
    
    # Check that the user is a member of the community
    user_community_link = db.exec(
        select(UserCommunityLink).where(
            UserCommunityLink.user_id == current_user.id,
            UserCommunityLink.community_id == community_id
        )
    ).first()
    
    if not user_community_link:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="You are not a member of this community"
        )
    
    # Update the visibility
    user_community_link.is_public = is_public
    db.add(user_community_link)
    db.commit()
    
    return {"message": "Visibility updated successfully"}