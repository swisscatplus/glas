from pydantic import BaseModel, RootModel

from nodes.models import BaseNodeModel, BaseURModel, BaseEMModel


class PostWorkflow(BaseModel):
    name: str


class DiagnosticModel(BaseModel):
    nodes: list[BaseNodeModel | BaseURModel | BaseEMModel]


class StepModel(BaseModel):
    name: str
    position: int


class WorkflowsModel(RootModel):
    root: dict[str, list[StepModel]]
