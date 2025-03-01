"""
Archivo centralizado que importa todos los modelos de la aplicación
para facilitar su acceso desde un solo lugar.
"""

# Modelos de comunidad
from api.public.community.models import (
    Community, 
    CommunityBase, 
    CommunityLevel, 
    CommunityRead
)

# Modelos de país
from api.public.country.models import (
    Country
)

# Modelos de región
from api.public.region.models import (
    Region
)

# Modelos de subregión
from api.public.subregion.models import (
    Subregion
)

# Modelos de localidad
from api.public.locality.models import (
    Locality
)

# Modelos de usuarios
from api.public.user.models import (
    User,
    UserRole
)

# Modelos de etiquetas
from api.public.tag.models import (
    Tag,
    TagBase,
    TagCreate,
    TagRead,
    TagUpdate,
    TagDelete
)

# Modelos de debates
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

# Modelos genéricos y relaciones
from api.utils.generic_models import (
    UserCommunityLink,
    PollCommunityLink,
    DebateCommunityLink,
    DebateTagLink,
    PollTagLink
)

