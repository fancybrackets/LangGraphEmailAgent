import json
from datetime import datetime

from langchain_core.tools import tool

from app.services.ollama_service import list_models


@tool
def get_current_local_time() -> str:
    """Return current local time in ISO format."""
    return datetime.now().isoformat(timespec="seconds")


@tool
def list_local_models_tool() -> str:
    """List local Ollama models as JSON."""
    try:
        models = list_models()
    except Exception as exc:  # noqa: BLE001
        return json.dumps({"error": str(exc)})
    return json.dumps(models)
