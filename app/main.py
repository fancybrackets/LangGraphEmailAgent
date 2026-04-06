from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.config import settings
from app.routers.chat import router as chat_router
from app.routers.health import router as health_router
from app.routers.models import router as models_router
from app.routers.tools import router as tools_router


app = FastAPI(title=settings.app_name)
BASE_DIR = Path(__file__).resolve().parent
WEB_DIR = BASE_DIR / "web"

app.mount("/assets", StaticFiles(directory=WEB_DIR), name="assets")


@app.get("/", include_in_schema=False)
def root():
    return FileResponse(WEB_DIR / "index.html")


@app.get("/settings", include_in_schema=False)
def settings_page():
    return FileResponse(WEB_DIR / "settings.html")


@app.get("/api", include_in_schema=False)
def api_info():
    return {"message": "Step 13 API is running", "ui": "/", "settings": "/settings"}


app.include_router(health_router)
app.include_router(chat_router)
app.include_router(models_router)
app.include_router(tools_router)
