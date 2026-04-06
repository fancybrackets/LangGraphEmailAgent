from fastapi import APIRouter, HTTPException

from app.agent.graph import run_agent_turn
from app.config import settings
from app.schemas import ChatRequest, ChatResponse
from app.services.ollama_service import get_active_model


router = APIRouter(tags=["chat"])


@router.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest):
    model_name = request.model or get_active_model() or settings.default_model
    try:
        reply = run_agent_turn(
            message=request.message,
            thread_id=request.thread_id,
            model_name=model_name,
        )
    except Exception as exc:  # noqa: BLE001
        raise HTTPException(status_code=500, detail=str(exc)) from exc

    return ChatResponse(
        reply=reply,
        thread_id=request.thread_id,
        model=model_name,
    )
