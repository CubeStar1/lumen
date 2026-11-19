from dataclasses import dataclass

import openai
from openai.types.responses import ResponseInputContentParam
from pydantic import BaseModel

from floorplan.errors import ModelError
from floorplan.extraction import FloorExtraction
from floorplan.imaging import PreparedImage
from floorplan.llm.prompts import EDIT_INSTRUCTIONS, EXTRACT_INSTRUCTIONS, REPAIR_TEMPLATE
from floorplan.models import FloorSpec


@dataclass(frozen=True)
class Feedback:
    previous: BaseModel
    problems: list[str]

    def as_text(self) -> str:
        return REPAIR_TEMPLATE.format(
            problems="\n".join(f"- {p}" for p in self.problems),
            previous=self.previous.model_dump_json(),
        )


class OpenAIPlanModel:
    def __init__(self, client: openai.OpenAI, model: str, reasoning_effort: str | None = None):
        self._client = client
        self._model = model
        self._reasoning = {"effort": reasoning_effort} if reasoning_effort else openai.omit

    def extract(self, image: PreparedImage, feedback: Feedback | None = None) -> FloorExtraction:
        size = f"The image is {image.width} x {image.height} pixels."
        content: list[ResponseInputContentParam] = [
            {"type": "input_text", "text": f"Read this floor plan. {size}"},
            {"type": "input_image", "image_url": image.url, "detail": "high"},
        ]
        return self._parse(EXTRACT_INSTRUCTIONS, content, feedback, FloorExtraction)

    def edit(
        self, floor: FloorSpec, instruction: str, feedback: Feedback | None = None
    ) -> FloorSpec:
        content: list[ResponseInputContentParam] = [
            {"type": "input_text", "text": f"Current plan:\n{floor.model_dump_json()}"},
            {"type": "input_text", "text": f"Instruction: {instruction}"},
        ]
        return self._parse(EDIT_INSTRUCTIONS, content, feedback, FloorSpec)

    def _parse[T: BaseModel](
        self,
        instructions: str,
        content: list[ResponseInputContentParam],
        feedback: Feedback | None,
        answer: type[T],
    ) -> T:
        if feedback:
            content = [*content, {"type": "input_text", "text": feedback.as_text()}]
        try:
            response = self._client.responses.parse(
                model=self._model,
                instructions=instructions,
                input=[{"role": "user", "content": content}],
                text_format=answer,
                reasoning=self._reasoning,
            )
        except openai.APIError as exc:
            raise ModelError(f"The language model request failed: {exc.message}") from exc

        if response.output_parsed is None:
            raise ModelError("The language model did not return a plan.")
        return response.output_parsed
