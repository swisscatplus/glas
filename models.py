from typing import Dict, Optional

from pydantic import BaseModel, RootModel


class PostWorkflow(BaseModel):
    name: str
    args: Optional[Dict] = None


class DiagnosticModel(BaseModel):
    nodes: list[object]


class PatchConfig(BaseModel):
    nodes_config: str
    workflows_config: str


class StepModel(BaseModel):
    name: str
    position: int


class WorkflowsModel(RootModel):
    root: dict[str, list[StepModel]]


class RestartNodeModel(BaseModel):
    node_id: str
