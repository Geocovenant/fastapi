"""
Centralized file that imports all application models
to facilitate access from a single place.
"""

# Community models
from api.public.community.models import (
    Community, 
    CommunityBase, 
    CommunityLevel, 
    CommunityRead
)

# Country models
from api.public.country.models import (
    Country
)

# Region models
from api.public.region.models import (
    Region
)

# Subregion models
from api.public.subregion.models import (
    Subregion
)

# Locality models
from api.public.locality.models import (
    Locality
)

# User models
from api.public.user.models import (
    User,
    UserRole
)

# Tag models
from api.public.tag.models import (
    Tag,
    TagBase,
    TagCreate,
    TagRead,
    TagUpdate,
    TagDelete
)

# Debate models
from api.public.debate.models import (
    Debate, 
    DebateBase,
    DebateCreate, 
    DebateRead, 
    DebateUpdate,
    DebateType,
    DebateStatus,
    DebateChangeLog,
    PointOfView, 
    PointOfViewCreate,
    PointOfViewRead,
    Opinion,
    OpinionCreate,
    OpinionRead,
    OpinionVote, 
    OpinionVoteCreate,
    UserMinimal,
    CommunityMinimal,
    LanguageCode
)

# Generic models and relationships
from api.utils.generic_models import (
    UserCommunityLink,
    PollCommunityLink,
    DebateCommunityLink,
    DebateTagLink,
    PollTagLink,
    ProjectCommunityLink
)

# Project models
from api.public.project.models import (
    Project,
    ProjectBase,
    ProjectCreate,
    ProjectRead,
    ProjectUpdate,
    ProjectStep,
    ProjectStepCreate,
    ProjectStepRead,
    ProjectCommitment,
    ProjectCommitmentCreate,
    ProjectCommitmentRead,
    ProjectDonation,
    ProjectDonationCreate,
    ProjectDonationRead,
    ProjectResource,
    ProjectResourceCreate,
    ProjectResourceRead,
    ProjectStepRead,
    ProjectUpdate,
    ProjectStatus,
    ResourceType,
    CommitmentType
)

# Issue models
from api.public.issue.models import (
    Issue,
    IssueBase,
    IssueCreate,
    IssueRead,
    IssueCategory,
    IssueCategoryBase,
    IssueCategoryCreate,
    IssueCategoryRead,
    Institution,
    InstitutionBase,
    InstitutionCreate,
    InstitutionRead,
    IssueSupport,
    IssueComment,
    IssueCommentBase,
    IssueCommentCreate,
    IssueCommentRead,
    IssueUpdate,
    IssueUpdateBase,
    IssueUpdateCreate,
    IssueUpdateRead,
    IssueStatus,
    InstitutionLevel,
    IssueImage
)

# Report models
from api.public.report.models import (
    Report,
    ReportBase,
    ReportCreate,
    ReportResponse,
    ReportType,
    ReportStatus,
    ReportReason
)

# Centralized import of all models 
# to resolve circular references

# Import basic models first
from api.public.user.models import User
from api.public.tag.models import Tag
from api.public.community.models import Community

# Then import models that depend on the basics
from api.public.poll.models import Poll, PollOption, PollVote, PollReaction, PollComment, PollCustomResponse
from api.public.debate.models import Debate, PointOfView, Opinion, OpinionVote, DebateChangeLog
from api.public.project.models import Project, ProjectStep, ProjectResource, ProjectCommitment, ProjectDonation
from api.public.report.models import Report
