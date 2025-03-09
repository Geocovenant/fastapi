from fastapi import APIRouter
from api.public.community import views as communities
from api.public.country import views as country
from api.public.user import views as user
from api.public.poll import views as poll
from api.public.region import views as region
from api.public.subregion import views as subregion
from api.public.debate import views as debate
from api.public.project import views as project
from api.public.issue import views as issue_views
from api.public.tag import views as tag
from api.public.report import views as report
from api.public.organization import views as organization_views
from api.public.cloudinary import views as cloudinary

api = APIRouter()

api.include_router(
    cloudinary.router,
    prefix="/cloudinary",
    tags=["Cloudinary"],
)
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
    debate.router,
    prefix="/debates",
    tags=["Debates"]
)
api.include_router(
    issue_views.router,
    prefix="/issues",
    tags=["Issues"]
)
api.include_router(
    poll.router,
    prefix="/polls",
    tags=["Polls"]
)
api.include_router(
    project.router,
    prefix="/projects",
    tags=["Projects"]
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
    tag.router,
    prefix="/tags",
    tags=["Tags"]
)
api.include_router(
    user.router,
    prefix="/users",
    tags=["Users"]
)
api.include_router(
    report.router,
    prefix="/reports",
    tags=["Reports"]
)
api.include_router(
    organization_views.router,
    prefix="/organizations",
    tags=["Organizations"]
)