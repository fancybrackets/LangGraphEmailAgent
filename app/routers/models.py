from fastapi import APIRouter, HTTPException

from app.schemas import (
    ActiveModelResponse,
    ModelActionRequest,
    ModelCatalogItem,
    ModelCatalogResponse,
    ModelInfo,
    ModelListResponse,
    PullModelRequest,
)
from app.services.ollama_service import (
    delete_model,
    get_active_model,
    get_model_catalog,
    is_catalog_model,
    list_models,
    pull_model,
    set_active_model,
)


router = APIRouter(tags=["models"])


@router.get("/models/catalog", response_model=ModelCatalogResponse)
def models_catalog():
    catalog = [ModelCatalogItem(**item) for item in get_model_catalog()]
    return ModelCatalogResponse(catalog=catalog)


@router.get("/models", response_model=ModelListResponse)
def models():
    try:
        rows = list_models()
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ModelListResponse(
        models=[ModelInfo(**row) for row in rows],
        active_model=get_active_model(),
    )


@router.post("/models/pull")
def models_pull(request: PullModelRequest):
    if not is_catalog_model(request.model):
        raise HTTPException(status_code=400, detail="Sadece katalogdaki modeller indirilebilir.")
    try:
        message = pull_model(request.model)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "ok", "message": message}


@router.post("/models/delete")
def models_delete(request: ModelActionRequest):
    try:
        message = delete_model(request.model)
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return {"status": "ok", "message": message}


@router.get("/models/active", response_model=ActiveModelResponse)
def models_active_get():
    return ActiveModelResponse(active_model=get_active_model())


@router.post("/models/active", response_model=ActiveModelResponse)
def models_active_set(request: ModelActionRequest):
    try:
        active = set_active_model(request.model)
    except RuntimeError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return ActiveModelResponse(active_model=active)
