from pydantic import BaseModel

from scheduler.database.models import TasksStatisticsEntry


class TaskDifference(BaseModel):
    this_week_task_count: int
    last_week_task_count: int
    percentage_difference: float | None


class NodeStatistic(BaseModel):
    id: str
    name: str
    endpoint: str | None
    call_count: int
    average_execution_duration: float | None
    minimum_execution_duration: float | None
    maximum_execution_duration: float | None
    success_rate: float


class WorkflowStatistic(BaseModel):
    id: int
    name: str
    usage_count: int


class StatisticsModel(BaseModel):
    nodes: list[NodeStatistic]
    workflows: list[WorkflowStatistic]


class TasksStatistics(BaseModel):
    current_week: list[TasksStatisticsEntry]
    last_week: list[TasksStatisticsEntry]
    difference: TaskDifference
