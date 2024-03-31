from pydantic import BaseModel

from src.nodes.models import BaseNodeModel, BaseURModel


class PostWorkflow(BaseModel):
    name: str


class DiagnosticModel(BaseModel):
    nodes: list[BaseNodeModel | BaseURModel]
