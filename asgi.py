import uvicorn
from api.app import create_app
from api.config import settings
from api.utils.verify_env import check_required_env_vars

# Verificar variables de entorno requeridas
if settings.ENV != "development":
    check_required_env_vars()

app = create_app(settings)

if __name__ == "__main__":
    uvicorn.run("asgi:app", host="0.0.0.0", port=settings.PORT, reload=settings.ENV == "development")
    