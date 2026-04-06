from fastapi import APIRouter

from app.agent.tool_registry import get_tools
from app.schemas import ToolCatalogResponse


router = APIRouter(tags=["tools"])


@router.get("/tools", response_model=ToolCatalogResponse)
def tools_catalog():
    return ToolCatalogResponse(tools=[tool.name for tool in get_tools()])
