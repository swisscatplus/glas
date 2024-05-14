from pydantic import BaseModel

from task_scheduler.workflow.models import WorkflowModel


class TaskModel(BaseModel):
    uuid: str
    workflow: WorkflowModel
    current_step: int
    state: int
