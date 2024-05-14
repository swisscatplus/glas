from datetime import datetime

from pydantic import BaseModel

from scheduler.workflow.models import WorkflowModel


class TaskModel(BaseModel):
    uuid: str
    workflow: WorkflowModel
    current_step: int
    state: int
