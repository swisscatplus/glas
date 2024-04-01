from pydantic import BaseModel

from src.nodes.models import BaseNodeModel, BaseURModel, BaseEMModel


class PostWorkflow(BaseModel):
    name: str


class DiagnosticModel(BaseModel):
    nodes: list[BaseNodeModel | BaseURModel | BaseEMModel]
