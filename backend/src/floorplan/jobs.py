"""Background jobs for parses that take longer than a phone should wait on one request.

A job runs on a worker thread and reports its stages as it goes ("Reading sheet", one per floor,
"Stacking floors"), so the app can show real progress. Jobs live in memory; finished ones are
kept for a while so a client that polls late still gets the result.
"""

import threading
import uuid
from collections import OrderedDict
from collections.abc import Callable
from concurrent.futures import ThreadPoolExecutor
from enum import StrEnum

from pydantic import BaseModel, computed_field

from floorplan.errors import FloorPlanError, JobNotFoundError

KEEP = 50


class JobState(StrEnum):
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"


class StageState(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"


class JobStage(BaseModel):
    name: str
    state: StageState


class Job(BaseModel):
    id: str
    state: JobState
    stages: list[JobStage] = []
    plan_id: str | None = None
    error: str | None = None

    @computed_field
    @property
    def stage(self) -> str:
        running = [s.name for s in self.stages if s.state == StageState.RUNNING]
        if running:
            return ", ".join(running)
        return "Done" if self.state == JobState.DONE else "Starting"

    @computed_field
    @property
    def progress(self) -> float:
        if self.state == JobState.DONE:
            return 1.0
        if not self.stages:
            return 0.0
        done = sum(
            1.0 if s.state == StageState.DONE else 0.4 if s.state == StageState.RUNNING else 0
            for s in self.stages
        )
        return round(done / len(self.stages), 3)


class JobProgress:
    """What a running job's work calls to report its stages."""

    def __init__(self, board: "JobBoard", job_id: str):
        self._board = board
        self._id = job_id

    def plan(self, stages: list[str]) -> None:
        def add(job: Job) -> None:
            known = {s.name for s in job.stages}
            job.stages += [
                JobStage(name=n, state=StageState.PENDING) for n in stages if n not in known
            ]

        self._board.change(self._id, add)

    def start(self, stage: str) -> None:
        self._set(stage, StageState.RUNNING)

    def finish(self, stage: str) -> None:
        self._set(stage, StageState.DONE)

    def _set(self, stage: str, state: StageState) -> None:
        def update(job: Job) -> None:
            match = next((s for s in job.stages if s.name == stage), None)
            if match is None:
                job.stages.append(JobStage(name=stage, state=state))
            else:
                match.state = state

        self._board.change(self._id, update)


class JobBoard:
    def __init__(self, workers: int = 2):
        self._jobs: OrderedDict[str, Job] = OrderedDict()
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=workers)

    def submit(self, work: Callable[[JobProgress], str]) -> Job:
        """Runs `work` in the background; it returns the id of the plan it saved."""
        job = Job(id=uuid.uuid4().hex[:12], state=JobState.RUNNING)
        with self._lock:
            self._jobs[job.id] = job
            while len(self._jobs) > KEEP:
                self._jobs.popitem(last=False)
        self._pool.submit(self._run, job.id, work)
        return job.model_copy(deep=True)

    def get(self, job_id: str) -> Job:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is None:
                raise JobNotFoundError(job_id)
            return job.model_copy(deep=True)

    def change(self, job_id: str, update: Callable[[Job], None]) -> None:
        with self._lock:
            job = self._jobs.get(job_id)
            if job is not None:
                update(job)

    def _run(self, job_id: str, work: Callable[[JobProgress], str]) -> None:
        try:
            plan_id = work(JobProgress(self, job_id))
        except FloorPlanError as exc:
            message = str(exc)
        except Exception as exc:  # noqa: BLE001 - reported to the client instead of lost
            message = f"Unexpected error: {exc}"
        else:
            self.change(job_id, lambda job: _finish(job, plan_id))
            return
        self.change(job_id, lambda job: _fail(job, message))


def _fail(job: Job, message: str) -> None:
    job.state = JobState.FAILED
    job.error = message


def _finish(job: Job, plan_id: str) -> None:
    job.state = JobState.DONE
    job.plan_id = plan_id
    for stage in job.stages:
        stage.state = StageState.DONE
