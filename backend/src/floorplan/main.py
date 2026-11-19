from functools import lru_cache
from typing import Annotated

import openai
from fastapi import Depends, FastAPI, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from floorplan.config import Settings, get_settings
from floorplan.errors import InvalidImageError, ModelError, PlanRejectedError
from floorplan.imaging import to_data_url
from floorplan.llm.client import OpenAIPlanModel
from floorplan.models import EditRequest, PlanResponse
from floorplan.service import PlanService

app = FastAPI(title="Floor Plan API")

SettingsDep = Annotated[Settings, Depends(get_settings)]


@lru_cache
def get_service() -> PlanService:
    settings = get_settings()
    client = openai.OpenAI(api_key=settings.openai_api_key.get_secret_value())
    model = OpenAIPlanModel(client, settings.openai_model, settings.openai_reasoning_effort)
    return PlanService(model)


ServiceDep = Annotated[PlanService, Depends(get_service)]


@app.exception_handler(InvalidImageError)
def invalid_image(_: Request, exc: InvalidImageError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(ModelError)
@app.exception_handler(PlanRejectedError)
def unusable_plan(_: Request, exc: Exception) -> JSONResponse:
    return JSONResponse(status_code=502, content={"detail": str(exc)})


@app.get("/health")
def health(settings: SettingsDep) -> dict[str, str]:
    return {"status": "ok", "model": settings.openai_model}


@app.post("/plans/parse")
def parse_plan(
    image: Annotated[UploadFile, File()], service: ServiceDep, settings: SettingsDep
) -> PlanResponse:
    data = image.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Image is too large.")
    return service.parse(to_data_url(data, settings.max_image_side))


@app.post("/plans/edit")
def edit_plan(request: EditRequest, service: ServiceDep) -> PlanResponse:
    return service.edit(request.spec, request.instruction)
