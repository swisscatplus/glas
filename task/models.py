from typing import Optional

from pydantic import BaseModel

from ..workflow.models import WorkflowModel


class TaskModel(BaseModel):
    uuid: str
    workflow: WorkflowModel
    current_step: int
    state: str
    args: Optional[dict]
