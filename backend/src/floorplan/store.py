import json
import re
import shutil
import threading
import uuid
from datetime import UTC, datetime
from pathlib import Path

from floorplan.errors import PlanNotFoundError
from floorplan.legacy import upgrade_record
from floorplan.models import BuildingKind, PlanRecord, PlanResponse, PlanSummary, RoomType

RECORD = "record.json"
IMAGE = "image.jpg"
THUMBNAIL = "thumbnail.jpg"
ANSWERS = "answers.json"

_ID_PATTERN = re.compile(r"^[0-9a-f]{12}$")


class PlanStore:
    """Keeps each saved plan in its own folder: the record JSON plus the uploaded image."""

    def __init__(self, root: Path):
        self._root = root
        self._lock = threading.Lock()

    def create(
        self,
        plan: PlanResponse,
        image: bytes | None = None,
        thumbnail: bytes | None = None,
        answers: str | None = None,
    ) -> PlanRecord:
        """Saves a new plan. `answers` is the model's raw reading, kept so the plan can be
        rebuilt later without asking the model again."""
        now = datetime.now(UTC)
        plan_id = uuid.uuid4().hex[:12]
        record = _record(plan_id, default_name(plan), now, now, image is not None, plan)
        with self._lock:
            folder = self._root / plan_id
            folder.mkdir(parents=True)
            if image is not None:
                (folder / IMAGE).write_bytes(image)
            if thumbnail is not None:
                (folder / THUMBNAIL).write_bytes(thumbnail)
            if answers is not None:
                (folder / ANSWERS).write_text(answers, "utf-8")
            _write(folder / RECORD, record)
        return record

    def summaries(self) -> list[PlanSummary]:
        if not self._root.exists():
            return []
        records = [
            self._read(folder.name) for folder in self._root.iterdir() if (folder / RECORD).exists()
        ]
        summaries = [PlanSummary.model_validate(r.model_dump(exclude={"plan"})) for r in records]
        return sorted(summaries, key=lambda s: s.updated_at, reverse=True)

    def get(self, plan_id: str) -> PlanRecord:
        return self._read(plan_id)

    def replace_plan(self, plan_id: str, plan: PlanResponse) -> PlanRecord:
        return self._update(
            plan_id, lambda r: _record(r.id, r.name, r.created_at, _now(), r.has_image, plan)
        )

    def rename(self, plan_id: str, name: str) -> PlanRecord:
        return self._update(
            plan_id, lambda r: r.model_copy(update={"name": name.strip(), "updated_at": _now()})
        )

    def delete(self, plan_id: str) -> None:
        with self._lock:
            shutil.rmtree(self._folder(plan_id))

    def image_path(self, plan_id: str, thumbnail: bool = False) -> Path:
        path = self._folder(plan_id) / (THUMBNAIL if thumbnail else IMAGE)
        if not path.exists():
            raise PlanNotFoundError(plan_id)
        return path

    def _update(self, plan_id: str, change) -> PlanRecord:
        with self._lock:
            record = change(self._read(plan_id))
            _write(self._folder(plan_id) / RECORD, record)
        return record

    def _read(self, plan_id: str) -> PlanRecord:
        data = json.loads((self._folder(plan_id) / RECORD).read_text("utf-8"))
        return PlanRecord.model_validate(upgrade_record(data))

    def _folder(self, plan_id: str) -> Path:
        folder = self._root / plan_id
        if not _ID_PATTERN.match(plan_id) or not (folder / RECORD).exists():
            raise PlanNotFoundError(plan_id)
        return folder


def default_name(plan: PlanResponse) -> str:
    if plan.spec.kind == BuildingKind.BUILDING:
        return f"{len(plan.spec.levels)}-floor building"
    rooms = [room for room in plan.geometry.rooms if not room.outdoor]
    bedrooms = sum(1 for room in rooms if room.type == RoomType.BEDROOM)
    return f"{bedrooms}-bedroom plan" if bedrooms else f"{len(rooms)}-room plan"


def _record(
    plan_id: str,
    name: str,
    created: datetime,
    updated: datetime,
    has_image: bool,
    plan: PlanResponse,
) -> PlanRecord:
    bounds = plan.geometry.bounds
    indoor = [room for room in plan.geometry.rooms if not room.outdoor]
    return PlanRecord(
        id=plan_id,
        name=name,
        created_at=created,
        updated_at=updated,
        has_image=has_image,
        kind=plan.spec.kind,
        level_count=len(plan.spec.levels),
        room_count=len(indoor),
        area=round(sum(room.area for room in indoor), 1),
        width=round(bounds.max.x - bounds.min.x, 2),
        depth=round(bounds.max.y - bounds.min.y, 2),
        plan=plan,
    )


def _write(path: Path, record: PlanRecord) -> None:
    temporary = path.with_suffix(".tmp")
    temporary.write_text(record.model_dump_json(), "utf-8")
    temporary.replace(path)


def _now() -> datetime:
    return datetime.now(UTC)
