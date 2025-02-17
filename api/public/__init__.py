from fastapi import APIRouter
from api.public.community import views as communities
from api.public.country import views as country
from api.public.user import views as user
from api.public.poll import views as poll

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
    poll.router,
    prefix="/polls",
    tags=["Polls"]
)
api.include_router(
    user.router,
    prefix="/users",
    tags=["Users"]
)