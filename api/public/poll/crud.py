import random
import string
from sqlmodel import Session, select, func, distinct
from api.public.poll.models import Poll, PollOption, PollCreate, PollVote, PollReaction, ReactionType, PollCustomResponse
from api.public.community.models import Community
from slugify import slugify
from datetime import datetime
from fastapi import HTTPException, status
from api.public.poll.models import PollStatus, PollType
from api.public.user.models import User
from api.public.poll.models import PollComment
from api.utils.generic_models import PollCommunityLink
from api.public.country.models import Country
from api.public.region.models import Region
from math import ceil
from api.public.tag.crud import get_tag_by_name, create_tag
from api.public.tag.models import Tag
from api.utils.generic_models import PollTagLink

def get_all_polls(
    db: Session, 
    scope: str | None = None, 
    current_user_id: int | None = None,
    page: int = 1,
    size: int = 10
):
    """
    Gets all polls with pagination
    """
    # Calculate offset for pagination
    offset = (page - 1) * size

    # First get the total number of polls for pagination
    total_query = select(func.count(Poll.id))
    if scope:
        total_query = total_query.where(Poll.scope == scope)
    total = db.exec(total_query).first()
    total_pages = ceil(total / size)

    # Main query to get only the polls first
    polls_query = select(Poll, User).join(User, Poll.creator_id == User.id)
    
    if scope:
        polls_query = polls_query.where(Poll.scope == scope)
    
    # Add sorting and pagination
    polls_query = polls_query.order_by(Poll.created_at.desc()).offset(offset).limit(size)
    
    polls_results = db.exec(polls_query).all()

    # Get poll IDs for related queries
    poll_ids = [poll.id for poll, _ in polls_results]

    # Get options for these polls
    options = db.exec(
        select(PollOption)
        .where(PollOption.poll_id.in_(poll_ids))
    ).all()

    # Group options by poll_id
    options_by_poll = {}
    for option in options:
        if option.poll_id not in options_by_poll:
            options_by_poll[option.poll_id] = []
        options_by_poll[option.poll_id].append(option)

    # Get tags for all polls
    tags_by_poll = {}
    tags_query = db.exec(
        select(PollTagLink.poll_id, Tag.name)
        .join(Tag, PollTagLink.tag_id == Tag.id)
        .where(PollTagLink.poll_id.in_(poll_ids))
    ).all()
    
    for poll_id, tag_name in tags_query:
        if poll_id not in tags_by_poll:
            tags_by_poll[poll_id] = []
        tags_by_poll[poll_id].append(tag_name)

    # First get the reaction count by type for each poll
    reactions_count = db.exec(
        select(
            PollReaction.poll_id,
            PollReaction.reaction,
            func.count(PollReaction.id).label('count')
        ).group_by(
            PollReaction.poll_id,
            PollReaction.reaction
        )
    ).all()
    
    # Create a dictionary to store counts
    reactions_dict = {}
    for reaction in reactions_count:
        if reaction.poll_id not in reactions_dict:
            reactions_dict[reaction.poll_id] = {'LIKE': 0, 'DISLIKE': 0}
        reactions_dict[reaction.poll_id][reaction.reaction] = reaction.count

    # Get comment count by poll
    comments_count = db.exec(
        select(
            PollComment.poll_id,
            func.count(PollComment.id).label('comments_count')
        ).group_by(
            PollComment.poll_id
        )
    ).all()
    
    comments_dict = {
        comment.poll_id: comment.comments_count 
        for comment in comments_count
    }

    # Get current user's votes if authenticated
    user_votes = {}
    if current_user_id:
        user_votes_query = select(PollVote).where(
            PollVote.user_id == current_user_id
        )
        user_votes_result = db.exec(user_votes_query).all()
        for vote in user_votes_result:
            if vote.poll_id not in user_votes:
                user_votes[vote.poll_id] = set()
            user_votes[vote.poll_id].add(vote.option_id)

    # Get current user's reactions if authenticated
    user_reactions = {}
    if current_user_id:
        user_reactions_query = select(PollReaction).where(
            PollReaction.user_id == current_user_id
        )
        user_reactions_result = db.exec(user_reactions_query).all()
        user_reactions = {
            reaction.poll_id: reaction.reaction 
            for reaction in user_reactions_result
        }

    # Process results
    polls_dict = {}
    for poll, user in polls_results:
        poll_dict = poll.dict()
        
        # Replace creator_id with creator object
        if not poll.is_anonymous and user:
            poll_dict['creator'] = {
                'id': user.id,
                'username': user.username,
                'image': user.image
            }
        else:
            poll_dict['creator'] = None
        
        del poll_dict['creator_id']
        
        poll_dict['reactions'] = reactions_dict.get(poll.id, {'LIKE': 0, 'DISLIKE': 0})
        poll_dict['comments_count'] = comments_dict.get(poll.id, 0)
        poll_dict['user_reaction'] = user_reactions.get(poll.id, None)
        poll_dict['user_voted_options'] = list(user_votes.get(poll.id, set())) if current_user_id else None
        
        # Add countries if scope is INTERNATIONAL
        if poll.scope == "INTERNATIONAL":
            countries = db.exec(
                select(Country.cca2)
                .join(Community, Community.id == Country.community_id)
                .join(PollCommunityLink)
                .where(PollCommunityLink.poll_id == poll.id)
                .distinct()
            ).all()
            poll_dict['countries'] = [country for country in countries if country]
        
        # Add poll options
        poll_dict['options'] = []
        for option in options_by_poll.get(poll.id, []):
            option_dict = option.dict()
            option_dict['voted'] = False
            if current_user_id and poll.id in user_votes:
                option_dict['voted'] = option.id in user_votes[poll.id]
            poll_dict['options'].append(option_dict)
        
        # Add tags
        poll_dict['tags'] = tags_by_poll.get(poll.id, [])
        
        polls_dict[poll.id] = poll_dict

    return {
        "items": list(polls_dict.values()),
        "total": total,
        "page": page,
        "size": size,
        "pages": total_pages
    }

def generate_unique_slug(db: Session, title: str) -> str:
    # Generate base slug
    base_slug = slugify(title)
    slug = base_slug
    
    # Check if slug exists
    while db.query(Poll).filter(Poll.slug == slug).first() is not None:
        # If it exists, add a random suffix
        random_suffix = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
        slug = f"{base_slug}-{random_suffix}"
    
    return slug

def create_poll(db: Session, poll_data: PollCreate, user_id: int) -> Poll:
    # Generate a unique slug
    unique_slug = generate_unique_slug(db, poll_data.title)
    
    # Get current time
    current_time = datetime.utcnow()
    
    # Create the poll
    db_poll = Poll(
        **poll_data.dict(exclude={'options', 'community_ids', 'country_codes', 'country_code', 'region_id', 'subregion_id', 'tags'}),
        creator_id=user_id,
        slug=unique_slug,
        created_at=current_time,
        updated_at=current_time
    )
    db.add(db_poll)
    db.commit()
    db.refresh(db_poll)
    
    # Create poll options
    for option_data in poll_data.options:
        db_option = PollOption(
            poll_id=db_poll.id,
            **option_data.dict()
        )
        db.add(db_option)
    
    # Add tags
    for tag_name in poll_data.tags:
        tag = get_tag_by_name(db, tag_name)
        if not tag:
            tag = create_tag(db, tag_name)
        db_poll.tags.append(tag)
    
    # Associate communities with the poll based on scope
    if poll_data.scope == "INTERNATIONAL" and poll_data.country_codes:
        # Find communities associated with country codes
        communities = db.exec(
            select(Community)
            .join(Country, Country.community_id == Community.id)
            .where(Country.cca2.in_(poll_data.country_codes))
        ).all()
        
        if not communities:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No communities found for the provided country codes"
            )
            
        db_poll.communities.extend(communities)
    elif poll_data.scope == "NATIONAL" and poll_data.country_code:
        # Find community associated with national country code
        country = db.exec(
            select(Country)
            .where(Country.cca2 == poll_data.country_code)
        ).first()
        
        if not country or not country.community_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No community found for country {poll_data.country_code}"
            )
            
        community = db.get(Community, country.community_id)
        if community:
            db_poll.communities.append(community)
    elif poll_data.scope == "REGIONAL" and poll_data.region_id:
        # Find community associated with region
        region = db.get(Region, poll_data.region_id)
        if not region or not region.community_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No community found for region with ID {poll_data.region_id}"
            )
            
        community = db.get(Community, region.community_id)
        if community:
            db_poll.communities.append(community)
    elif poll_data.scope == "SUBREGIONAL" and poll_data.subregion_id:
        # Find community associated with national subdivision
        from api.public.subregion.models import Subregion
        
        subregion = db.get(Subregion, poll_data.subregion_id)
        if not subregion or not subregion.community_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"No community found for national subdivision with ID {poll_data.subregion_id}"
            )
            
        community = db.get(Community, subregion.community_id)
        if community:
            db_poll.communities.append(community)
    elif poll_data.community_ids:
        # For other scopes, use community_ids directly
        communities = db.exec(
            select(Community).where(Community.id.in_(poll_data.community_ids))
        ).all()
        db_poll.communities.extend(communities)
    
    db.commit()
    db.refresh(db_poll)
    return db_poll

def create_vote(db: Session, poll_id: int, option_ids: list[int], user_id: int, custom_response: str | None = None) -> Poll:
    # Verify poll exists
    poll = db.get(Poll, poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )
    
    # Verify poll is published
    if poll.status != PollStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot vote on a poll that is not published"
        )
    
    # Verify options belong to the poll
    valid_options = db.exec(
        select(PollOption).where(
            PollOption.poll_id == poll_id,
            PollOption.id.in_(option_ids)
        )
    ).all()
    
    if len(valid_options) != len(option_ids):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Some options are not valid for this poll"
        )
    
    # Verify voting type
    if poll.type == PollType.BINARY or poll.type == PollType.SINGLE_CHOICE:
        if len(option_ids) > 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This poll only allows one option"
            )
    
    # Find existing user votes in this poll
    existing_votes = db.exec(
        select(PollVote).where(
            PollVote.poll_id == poll_id,
            PollVote.user_id == user_id
        )
    ).all()
    
    # Remove previous votes
    for vote in existing_votes:
        # Decrement vote counter for previous option
        old_option = db.get(PollOption, vote.option_id)
        old_option.votes = max(0, old_option.votes - 1)  # Avoid negative numbers
        db.delete(vote)
    
    # Create new votes
    for option_id in option_ids:
        vote = PollVote(
            poll_id=poll_id,
            option_id=option_id,
            user_id=user_id
        )
        db.add(vote)
        
        # Increment vote counter for new option
        option = db.get(PollOption, option_id)
        option.votes += 1
    
    # If there's a custom response, verify the option allows custom responses
    if custom_response:
        option = db.get(PollOption, option_ids[0])
        if not option or not option.is_custom_option:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="This option does not allow custom responses"
            )
            
        # Create custom response
        custom = PollCustomResponse(
            option_id=option.id,
            user_id=user_id,
            response_text=custom_response
        )
        db.add(custom)
    
    db.commit()
    db.refresh(poll)
    return poll

def create_or_update_reaction(db: Session, poll_id: int, user_id: int, reaction_type: ReactionType) -> Poll:
    """
    Creates or updates a reaction on a poll.
    If the reaction already exists and is of the same type, it is removed.
    If the reaction already exists and is of a different type, it is updated.
    """
    # Verify poll exists
    poll = db.get(Poll, poll_id)
    if not poll:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Poll not found"
        )
    
    # Verify poll is published
    if poll.status != PollStatus.PUBLISHED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot react to a poll that is not published"
        )
    
    # Check if user already has a reaction
    existing_reaction = db.exec(
        select(PollReaction).where(
            PollReaction.poll_id == poll_id,
            PollReaction.user_id == user_id
        )
    ).first()
    
    if existing_reaction:
        if existing_reaction.reaction == reaction_type:
            # If reaction is the same, remove it
            db.delete(existing_reaction)
        else:
            # If reaction is different, update it
            existing_reaction.reaction = reaction_type
            existing_reaction.reacted_at = datetime.utcnow()
            db.add(existing_reaction)
    else:
        # Create new reaction
        new_reaction = PollReaction(
            poll_id=poll_id,
            user_id=user_id,
            reaction=reaction_type,
            reacted_at=datetime.utcnow()
        )
        db.add(new_reaction)
    
    db.commit()
    
    # Get updated poll with all its information
    query = select(Poll, PollOption, User).join(PollOption).join(User, Poll.creator_id == User.id).where(Poll.id == poll_id)
    result = db.exec(query).first()
    
    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Error getting updated poll"
        )
    
    poll, option, user = result
    
    # Get updated reaction count
    reactions_count = db.exec(
        select(
            PollReaction.reaction,
            func.count(PollReaction.id).label('count')
        ).where(
            PollReaction.poll_id == poll_id
        ).group_by(
            PollReaction.reaction
        )
    ).all()
    
    # Create poll dictionary
    poll_dict = poll.dict()
    if not poll.is_anonymous:
        poll_dict['creator_username'] = user.username
        del poll_dict['creator_id']
    else:
        del poll_dict['creator_id']
    
    # Add reaction count
    reactions_dict = {'LIKE': 0, 'DISLIKE': 0}
    for reaction in reactions_count:
        reactions_dict[reaction.reaction] = reaction.count
    
    poll_dict['reactions'] = reactions_dict
    
    # Get all poll options
    options = db.exec(
        select(PollOption).where(PollOption.poll_id == poll_id)
    ).all()
    poll_dict['options'] = [option.dict() for option in options]
    
    # Get communities associated with the poll
    communities = [
        {"id": c.id, "name": c.name, "description": c.description}
        for c in poll.communities
    ]
    poll_dict['communities'] = communities
    
    return poll_dict

def get_country_polls(
    db: Session, 
    country_code: str, 
    scope: str | None = None, 
    current_user_id: int | None = None,
    page: int = 1,
    size: int = 10
):
    """
    Gets all polls associated with a specific country with pagination.
    """
    # Calculate offset for pagination
    offset = (page - 1) * size

    # Verify country exists
    country = db.exec(
        select(Country).where(Country.cca2 == country_code)
    ).first()
    
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Country with code {country_code} not found"
        )

    # Get total polls for pagination
    total_query = (
        select(func.count(distinct(Poll.id)))
        .join(PollCommunityLink)
        .join(Community)
        .join(Country)
        .where(Country.cca2 == country_code)
    )
    
    if scope:
        total_query = total_query.where(Poll.scope == scope)
    
    total = db.exec(total_query).first()
    total_pages = ceil(total / size)

    # Modify main query to include pagination
    query = (
        select(Poll, PollOption, User)
        .join(PollOption)
        .join(User, Poll.creator_id == User.id)
        .join(PollCommunityLink)
        .join(Community)
        .join(Country)
        .where(Country.cca2 == country_code)
    )

    if scope:
        query = query.where(Poll.scope == scope)

    query = query.order_by(Poll.created_at.desc()).offset(offset).limit(size)

    # Get polls
    results = db.exec(query).all()

    # Get poll IDs
    poll_ids = [poll.id for poll, _, _ in results]
    
    # Get tags for all polls
    from api.public.tag.models import Tag
    from api.utils.generic_models import PollTagLink
    
    tags_by_poll = {}
    tags_query = db.exec(
        select(PollTagLink.poll_id, Tag.name)
        .join(Tag, PollTagLink.tag_id == Tag.id)
        .where(PollTagLink.poll_id.in_(poll_ids))
    ).all()
    
    for poll_id, tag_name in tags_query:
        if poll_id not in tags_by_poll:
            tags_by_poll[poll_id] = []
        tags_by_poll[poll_id].append(tag_name)

    # Get reaction counts
    reactions_count = db.exec(
        select(
            PollReaction.poll_id,
            PollReaction.reaction,
            func.count(PollReaction.id).label('count')
        ).group_by(
            PollReaction.poll_id,
            PollReaction.reaction
        )
    ).all()

    # Create reactions dictionary
    reactions_dict = {}
    for reaction in reactions_count:
        if reaction.poll_id not in reactions_dict:
            reactions_dict[reaction.poll_id] = {'LIKE': 0, 'DISLIKE': 0}
        reactions_dict[reaction.poll_id][reaction.reaction] = reaction.count

    # Get comments count
    comments_count = db.exec(
        select(
            PollComment.poll_id,
            func.count(PollComment.id).label('comments_count')
        ).group_by(
            PollComment.poll_id
        )
    ).all()
    
    comments_dict = {
        comment.poll_id: comment.comments_count 
        for comment in comments_count
    }

    # Get current user votes if authenticated
    user_votes = {}
    if current_user_id:
        user_votes_query = select(PollVote).where(
            PollVote.user_id == current_user_id
        )
        user_votes_result = db.exec(user_votes_query).all()
        for vote in user_votes_result:
            if vote.poll_id not in user_votes:
                user_votes[vote.poll_id] = set()
            user_votes[vote.poll_id].add(vote.option_id)

    # Get current user reactions if authenticated
    user_reactions = {}
    if current_user_id:
        user_reactions_query = select(PollReaction).where(
            PollReaction.user_id == current_user_id
        )
        user_reactions_result = db.exec(user_reactions_query).all()
        user_reactions = {
            reaction.poll_id: reaction.reaction 
            for reaction in user_reactions_result
        }

    # Process results
    polls_dict = {}
    for poll, option, user in results:
        if poll.id not in polls_dict:
            poll_dict = poll.dict()
            if not poll.is_anonymous:
                poll_dict['creator_username'] = user.username
                del poll_dict['creator_id']
            else:
                del poll_dict['creator_id']
            
            poll_dict['reactions'] = reactions_dict.get(poll.id, {'LIKE': 0, 'DISLIKE': 0})
            poll_dict['comments_count'] = comments_dict.get(poll.id, 0)
            poll_dict['user_reaction'] = user_reactions.get(poll.id, None)
            poll_dict['user_voted_options'] = list(user_votes.get(poll.id, set())) if current_user_id else None
            
            # Add countries if scope is INTERNATIONAL
            if poll.scope == "INTERNATIONAL":
                countries = db.exec(
                    select(Country.cca2)
                    .join(Community, Community.id == Country.community_id)
                    .join(PollCommunityLink)
                    .where(PollCommunityLink.poll_id == poll.id)
                    .distinct()
                ).all()
                poll_dict['countries'] = [country for country in countries if country]
            
            # Add tags
            poll_dict['tags'] = tags_by_poll.get(poll.id, [])
            
            polls_dict[poll.id] = poll_dict
            polls_dict[poll.id]['options'] = []

        option_dict = option.dict()
        option_dict['voted'] = False
        if current_user_id and poll.id in user_votes:
            option_dict['voted'] = option.id in user_votes[poll.id]
        
        polls_dict[poll.id]['options'].append(option_dict)
    
    return {
        "items": list(polls_dict.values()),
        "total": total,
        "page": page,
        "size": size,
        "pages": total_pages
    }

def get_regional_polls(
    db: Session,
    region_id: int,
    scope: str | None = None,
    current_user_id: int | None = None,
    page: int = 1,
    size: int = 10
):
    """
    Get all polls associated with a specific region with pagination.
    """
    # First get the community associated with the region
    region_community = db.exec(
        select(Community)
        .join(Region, Community.id == Region.community_id)
        .where(Region.id == region_id)
    ).first()

    if not region_community:
        return []

    offset = (page - 1) * size

    # Get total for pagination
    total_query = (
        select(func.count(distinct(Poll.id)))
        .join(PollCommunityLink)
        .where(
            PollCommunityLink.community_id == region_community.id,
            Poll.status == PollStatus.PUBLISHED
        )
    )

    if scope:
        total_query = total_query.where(Poll.scope == scope)

    total = db.exec(total_query).first()
    total_pages = ceil(total / size)

    # Modify main query
    query = (
        select(Poll)
        .distinct()
        .join(PollCommunityLink)
        .where(
            PollCommunityLink.community_id == region_community.id,
            Poll.status == PollStatus.PUBLISHED
        )
    )

    if scope:
        query = query.where(Poll.scope == scope)

    query = query.order_by(Poll.created_at.desc()).offset(offset).limit(size)

    polls = db.exec(query).all()
    
    return {
        "items": [
            enrich_poll(db, poll, current_user_id)
            for poll in polls
        ],
        "total": total,
        "page": page,
        "size": size,
        "pages": total_pages
    }

def enrich_poll(db: Session, poll: Poll, current_user_id: int | None = None) -> dict:
    """
    Enriches a poll with additional information:
    - Options and votes
    - Reactions
    - Creator information
    - Comments count and full comments
    - Current user voting status
    """
    # Get creator
    creator = db.get(User, poll.creator_id)
    
    # Get options with vote counts, ordered by ID to maintain consistency
    options = db.exec(
        select(PollOption)
        .where(PollOption.poll_id == poll.id)
        .order_by(PollOption.id)
    ).all()

    # Count votes per option
    for option in options:
        votes_count = db.exec(
            select(func.count())
            .where(PollVote.option_id == option.id)
        ).first()
        option.votes = votes_count or 0

    # Get reactions
    reactions = db.exec(
        select(
            PollReaction.reaction,
            func.count(PollReaction.id).label('count')
        )
        .where(PollReaction.poll_id == poll.id)
        .group_by(PollReaction.reaction)
    ).all()
    
    reactions_dict = {'LIKE': 0, 'DISLIKE': 0}
    for reaction in reactions:
        reactions_dict[reaction.reaction] = reaction.count

    # Get comments count
    comments_count = db.exec(
        select(func.count(PollComment.id))
        .where(PollComment.poll_id == poll.id)
    ).first()

    # Get full comments with user info
    comments = db.exec(
        select(PollComment, User)
        .join(User)
        .where(PollComment.poll_id == poll.id)
        .order_by(PollComment.created_at.desc())
    ).all()
    
    comments_list = [
        {
            **comment.dict(),
            "username": user.username,
            "can_edit": current_user_id and current_user_id == comment.user_id
        }
        for comment, user in comments
    ]

    # Get current user votes if authenticated
    user_voted_options = []  # Initialize as empty list instead of None
    if current_user_id:
        votes = db.exec(
            select(PollVote.option_id)
            .where(
                PollVote.poll_id == poll.id,
                PollVote.user_id == current_user_id
            )
        ).all()
        if votes:
            user_voted_options = [vote for vote in votes]

    # Get current user reaction if authenticated
    user_reaction = None
    if current_user_id:
        reaction = db.exec(
            select(PollReaction)
            .where(
                PollReaction.poll_id == poll.id,
                PollReaction.user_id == current_user_id
            )
        ).first()
        if reaction:
            user_reaction = reaction.reaction

    # Build poll dictionary
    poll_dict = poll.dict()
    
    # Add creator information in standardized format
    if not poll.is_anonymous and creator:
        poll_dict['creator'] = {
            'id': creator.id,
            'username': creator.username,
            'image': creator.image
        }
    else:
        poll_dict['creator'] = None
    
    del poll_dict['creator_id']

    # Add options with voting status
    poll_dict['options'] = [
        {
            **option.dict(),
            'voted': option.id in user_voted_options if user_voted_options else False
        }
        for option in options
    ]

    # Add reactions and comments
    poll_dict['reactions'] = reactions_dict
    poll_dict['comments_count'] = comments_count or 0
    poll_dict['comments'] = comments_list
    poll_dict['user_reaction'] = user_reaction
    poll_dict['user_voted_options'] = user_voted_options

    # Add tags
    poll_dict['tags'] = [tag.name for tag in poll.tags]

    return poll_dict