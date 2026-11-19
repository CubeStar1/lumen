class FloorPlanError(Exception):
    """Base for errors that are reported to the client."""


class InvalidImageError(FloorPlanError):
    pass


class ModelError(FloorPlanError):
    pass


class PlanNotFoundError(FloorPlanError):
    def __init__(self, plan_id: str):
        super().__init__(f"No saved plan with id '{plan_id}'.")


class PlanRejectedError(FloorPlanError):
    def __init__(self, problems: list[str]):
        super().__init__("The plan could not be interpreted: " + "; ".join(problems))
        self.problems = problems
