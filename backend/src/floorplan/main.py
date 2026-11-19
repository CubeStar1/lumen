from enum import StrEnum
from functools import lru_cache
from typing import Annotated

import openai
from fastapi import (
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Path,
    Request,
    Response,
    UploadFile,
)
from fastapi.responses import FileResponse, JSONResponse

from floorplan.building import BuildingReader
from floorplan.config import Settings, get_settings
from floorplan.errors import (
    InvalidImageError,
    JobNotFoundError,
    LevelNotFoundError,
    ModelError,
    PlanNotFoundError,
    PlanRejectedError,
)
from floorplan.imaging import load_image, prepare, to_jpeg
from floorplan.jobs import Job, JobBoard, JobProgress
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

READING_PLAN = "Reading plan"


def plan_model(settings: Settings) -> OpenAIPlanModel:
    client = openai.OpenAI(api_key=settings.openai_api_key.get_secret_value())
    return OpenAIPlanModel(client, settings.openai_model, settings.openai_reasoning_effort)


@lru_cache
def get_service() -> PlanService:
    return PlanService(plan_model(get_settings()))


@lru_cache
def get_store() -> PlanStore:
    return PlanStore(get_settings().data_dir)


@lru_cache
def get_jobs() -> JobBoard:
    return JobBoard()


class ParseKind(StrEnum):
    FLOOR = "floor"
    SHEET = "sheet"
    PHOTOS = "photos"


SettingsDep = Annotated[Settings, Depends(get_settings)]
ServiceDep = Annotated[PlanService, Depends(get_service)]
StoreDep = Annotated[PlanStore, Depends(get_store)]
JobsDep = Annotated[JobBoard, Depends(get_jobs)]
PlanId = Annotated[str, Path(pattern=r"^[0-9a-f]{12}$")]
JobId = Annotated[str, Path(pattern=r"^[0-9a-f]{12}$")]


@app.exception_handler(InvalidImageError)
def invalid_image(_: Request, exc: InvalidImageError) -> JSONResponse:
    return JSONResponse(status_code=422, content={"detail": str(exc)})


@app.exception_handler(PlanNotFoundError)
@app.exception_handler(LevelNotFoundError)
@app.exception_handler(JobNotFoundError)
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
    picture = _read_upload(image, settings)
    plan = service.parse(prepare(picture, settings.max_image_side))
    return store.create(
        plan,
        image=to_jpeg(picture, settings.stored_image_side),
        thumbnail=to_jpeg(picture, settings.thumbnail_side),
    )


@app.post("/jobs", status_code=202)
def start_job(
    kind: Annotated[ParseKind, Form()],
    images: Annotated[list[UploadFile], File()],
    service: ServiceDep,
    store: StoreDep,
    settings: SettingsDep,
    jobs: JobsDep,
) -> Job:
    """Starts reading a floor plan, a sheet of a building's plans, or a photo per floor."""
    if kind != ParseKind.PHOTOS and len(images) != 1:
        raise HTTPException(status_code=422, detail="Send exactly one image.")
    if len(images) > settings.max_photos:
        raise HTTPException(status_code=422, detail=f"Send at most {settings.max_photos} photos.")
    pictures = [_read_upload(upload, settings) for upload in images]
    reader = BuildingReader(service, settings.max_image_side)
    stored_side = (
        settings.stored_sheet_side if kind == ParseKind.SHEET else settings.stored_image_side
    )

    def work(progress: JobProgress) -> str:
        answers = None
        if kind == ParseKind.FLOOR:
            progress.plan([READING_PLAN])
            progress.start(READING_PLAN)
            plan = service.parse(prepare(pictures[0], settings.max_image_side))
        else:
            read = (
                reader.from_sheet(pictures[0], progress)
                if kind == ParseKind.SHEET
                else reader.from_photos(pictures, progress)
            )
            plan, answers = read.response, read.answers.model_dump_json()
        record = store.create(
            plan,
            image=to_jpeg(pictures[0], stored_side),
            thumbnail=to_jpeg(pictures[0], settings.thumbnail_side),
            answers=answers,
        )
        return record.id

    return jobs.submit(work)


@app.get("/jobs/{job_id}")
def get_job(job_id: JobId, jobs: JobsDep) -> Job:
    return jobs.get(job_id)


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


def _read_upload(upload: UploadFile, settings: Settings):
    data = upload.file.read(settings.max_upload_bytes + 1)
    if len(data) > settings.max_upload_bytes:
        raise HTTPException(status_code=413, detail="Image is too large.")
    return load_image(data)


@app.get("/plans/{plan_id}/thumbnail")
def plan_thumbnail(plan_id: PlanId, store: StoreDep) -> FileResponse:
    return FileResponse(store.image_path(plan_id, thumbnail=True), media_type="image/jpeg")
