from pydantic import BaseModel

from src.nodes.models import BaseNodeModel, BaseURModel


class PostWorkflow(BaseModel):
    name: str


class DiagnosticModel(BaseModel):
    orchestrator: str
    nodes: list[BaseNodeModel | BaseURModel]
