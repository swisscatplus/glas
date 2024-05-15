from typing import Any

from ..nodes.base import BaseNode
from .models import WorkflowModel


class Workflow:
    def __init__(self, _id: int, name: str, steps: list[BaseNode], verbose: bool = False) -> None:
        if len(steps) < 2:
            raise ValueError("Steps must at least have 2 nodes")
        self.id = _id
        self.name = name
        self.steps = steps
        self.source = steps[0]
        self.destination = steps[-1]

        self.verbose = verbose

        self.stop_flag = False

    def __repr__(self) -> str:
        return f"{self.source} - {self.destination}"

    def serialize(self) -> WorkflowModel:
        return WorkflowModel(
            id=self.id,
            name=self.name,
            source=self.source.serialize(),
            destination=self.destination.serialize(),
            steps=[step.serialize() for step in self.steps],
        )

    def model_dump(self) -> dict[str, Any]:
        return self.serialize().model_dump()
