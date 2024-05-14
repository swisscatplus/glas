from pydantic import BaseModel

from scheduler.nodes.models import BaseNodeModel


class WorkflowModel(BaseModel):
    id: int
    name: str
    source: BaseNodeModel
    destination: BaseNodeModel
    steps: list[BaseNodeModel]
