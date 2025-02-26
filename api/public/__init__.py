from fastapi import APIRouter
from api.public.community import views as communities
from api.public.country import views as country
from api.public.user import views as user
from api.public.poll import views as poll
from api.public.region import views as region
from api.public.subregion import views as subregion

api = APIRouter()

api.include_router(
    communities.router,
    prefix="/communities",
    tags=["Communities"]
)
api.include_router(
    country.router,
    prefix="/countries",
    tags=["Countries"]
)
api.include_router(
    region.router,
    prefix="/regions",
    tags=["Regions"]
)
api.include_router(
    subregion.router,
    prefix="/subregions",
    tags=["Subregion"]
)
api.include_router(
    poll.router,
    prefix="/polls",
    tags=["Polls"]
)
api.include_router(
    user.router,
    prefix="/users",
    tags=["Users"]
)