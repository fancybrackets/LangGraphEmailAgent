from fastapi import APIRouter

from app.config import settings
from app.services.ollama_service import ollama_reachable


router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {
        "status": "ok",
        "service": "langgraph-chat",
        "privacy_mode": settings.privacy_mode,
        "ollama_reachable": ollama_reachable(),
    }
