"""
This module contains the class that defines a workflow.
"""

from typing import Any, Optional

from ..nodes.base import BaseNode
from .models import WorkflowModel


class Workflow:
    """
    This class defined a workflow as a static entity. When wanting to name a workflow being executed, please refer it as
    a task.
    """

    def __init__(
        self, _id: int, name: str, steps: list[BaseNode], args: Optional[dict] = None
    ) -> None:
        if len(steps) < 2:
            raise ValueError("Steps must at least have 2 nodes")
        self.id = _id
        self.name = name
        self.steps = steps
        self.source = steps[0]
        self.destination = steps[-1]
        self.args = args

    def __repr__(self) -> str:
        return f"{self.source} - {self.destination}"

    def serialize(self) -> WorkflowModel:
        return WorkflowModel(
            id=self.id,
            name=self.name,
            source=self.source.serialize(),
            destination=self.destination.serialize(),
            steps=[step.serialize() for step in self.steps],
            args=self.args,
        )

    def model_dump(self) -> dict[str, Any]:
        return self.serialize().model_dump()
