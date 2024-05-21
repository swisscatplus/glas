from pydantic import BaseModel, RootModel
from typing import Dict, Optional
from .nodes.models import BaseNodeModel


class PostWorkflow(BaseModel):
    name: str
    args: Optional[Dict] = None


class DiagnosticModel(BaseModel):
    nodes: list[object]


class StepModel(BaseModel):
    name: str
    position: int


class WorkflowsModel(RootModel):
    root: dict[str, list[StepModel]]
