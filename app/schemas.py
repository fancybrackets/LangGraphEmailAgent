from pydantic import BaseModel, Field


class ChatRequest(BaseModel):
    thread_id: str = Field(min_length=1, description="Conversation session id")
    message: str = Field(min_length=1, description="User message")
    model: str | None = Field(default=None, description="Optional model override")


class ChatResponse(BaseModel):
    reply: str
    thread_id: str
    model: str


class ModelInfo(BaseModel):
    name: str
    size: str | None = None
    modified: str | None = None


class ModelCatalogItem(BaseModel):
    name: str
    label: str
    notes: str


class ModelListResponse(BaseModel):
    models: list[ModelInfo]
    active_model: str | None = None


class PullModelRequest(BaseModel):
    model: str = Field(min_length=1, description="Model name to download")


class ModelActionRequest(BaseModel):
    model: str = Field(min_length=1, description="Model name")


class ActiveModelResponse(BaseModel):
    active_model: str | None = None


class ModelCatalogResponse(BaseModel):
    catalog: list[ModelCatalogItem]


class ToolCatalogResponse(BaseModel):
    tools: list[str]
