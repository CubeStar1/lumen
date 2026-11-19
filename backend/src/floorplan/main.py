from functools import lru_cache
from typing import Annotated

import openai
from fastapi import Depends, FastAPI, File, HTTPException, Path, Request, Response, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from floorplan.config import Settings, get_settings
from floorplan.errors import (
    InvalidImageError,
    LevelNotFoundError,
    ModelError,
    PlanNotFoundError,
    PlanRejectedError,
)
from floorplan.imaging import load_image, prepare, to_jpeg
from floorplan.llm.client import OpenAIPlanModel
from floorplan.models import (
    EditRequest,
    InstructionRequest,
    PlanRecord,
    PlanResponse,
    PlanSummary,
    RenameRequest,
)
from floorplan.service import PlanService
from floorplan.store import PlanStore

app = FastAPI(title="Floor Plan API")


def plan_model(settings: Settings) -> OpenAIPlanModel:
    client = openai.OpenAI(api_key=settings.openai_api_key.get_secret_value())
    return OpenAIPlanModel(client, settings.openai_model, settings.openai_reasoning_effort)


@lru_cache
def get_service() -> PlanService:
    return PlanService(plan_model(get_settings()))


@lru_cache
def get_store() -> PlanStore:
    return PlanStore(get_settings().data_dir)


SettingsDep = Annotated[Settings, Depends(get_settings)]
ServiceDep = Annotated[PlanService, Depends(get_service)]
StoreDep = Annotated[PlanStore, Depends(get_store)]
PlanId = Annotated[str, Path(pattern=r"^[0-9a-f]{12}$")]


@app.exception_handler(InvalidImageError)
def invalid_image(_: Request, exc: InvalidImageError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(PlanNotFoundError)
@app.exception_handler(LevelNotFoundError)
def plan_not_found(_: Request, exc: PlanNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"detail": str(exc)})


@app.exception_handler(ModelError)
@app.exception_handler(PlanRejectedError)
def unusable_plan(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/health")
def health(settings: SettingsDep) -> dict[str, str]:
    return {"status": "ok", "model": settings.openai_model}


@app.post("/plans/parse")
def parse_plan(
    image: Annotated[UploadFile, File()],
    service: ServiceDep,
    store: StoreDep,
    settings: SettingsDep,
) -> PlanRecord:
    data = image.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Image is too large.")

    picture = load_image(data)
    plan = service.parse(prepare(picture, settings.max_image_side))
    return store.create(
        plan,
        image=to_jpeg(picture, settings.stored_image_side),
        thumbnail=to_jpeg(picture, settings.thumbnail_side),
    )


@app.post("/plans/edit")
def edit_unsaved_plan(request: EditRequest, service: ServiceDep) -> PlanResponse:
    return service.edit(request.spec, request.instruction, request.level)


@app.get("/plans")
def list_plans(store: StoreDep) -> list[PlanSummary]:
    return store.summaries()


@app.get("/plans/{plan_id}")
def get_plan(plan_id: PlanId, store: StoreDep) -> PlanRecord:
    return store.get(plan_id)


@app.patch("/plans/{plan_id}")
def rename_plan(plan_id: PlanId, request: RenameRequest, store: StoreDep) -> PlanRecord:
    return store.rename(plan_id, request.name)


@app.delete("/plans/{plan_id}", status_code=204)
def delete_plan(plan_id: PlanId, store: StoreDep) -> Response:
    store.delete(plan_id)
    return Response(status_code=204)


@app.post("/plans/{plan_id}/edit")
def edit_plan(
    plan_id: PlanId, request: InstructionRequest, service: ServiceDep, store: StoreDep
) -> PlanRecord:
    current = store.get(plan_id).plan
    return store.replace_plan(
        plan_id, service.edit(current.spec, request.instruction, request.level)
    )


@app.get("/plans/{plan_id}/image")
def plan_image(plan_id: PlanId, store: StoreDep) -> FileResponse:
    return FileResponse(store.image_path(plan_id), media_type="image/jpeg")


@app.get("/plans/{plan_id}/thumbnail")
def plan_thumbnail(plan_id: PlanId, store: StoreDep) -> FileResponse:
    return FileResponse(store.image_path(plan_id, thumbnail=True), media_type="image/jpeg")
