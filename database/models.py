"""
This module contains all the models mapping to the database tables. All the models are prefixed with `DB` to not confuse
with the models used in GLAS.
"""

# pylint: disable=missing-class-docstring

from typing import Optional

from datetime import datetime
from pydantic import BaseModel


class DBLogs(BaseModel):
    id: int
    logger_name: str
    log_level: str
    module: str
    function: str
    line: int
    message: str


class DBExecutionLogs(BaseModel):
    id: int
    task_id: int
    workflow_id: int
    name: str
    start: float
    end: float


class DBNodePropertyModel(BaseModel):
    id: int
    node_id: int
    name: str
    value: str


class DBNodeModel(BaseModel):
    id: str
    name: str
    node_state_id: int
    updated_at: str


class DBTaskModel(BaseModel):
    id: str
    workflow_id: int
    active_step: str | None
    task_state_id: int
    args: Optional[dict]
    created_at: datetime
    updated_at: datetime


class DBWorkflowModel(BaseModel):
    id: int
    name: str
    source_node_id: str
    destination_node_id: str


class DBStepModel(BaseModel):
    id: int
    node_id: str
    worflow_id: int
    postion: int


class DBNodeCallRecordModel(BaseModel):
    id: int
    node_id: str
    endpoint: str | None
    message: str | None
    timestamp: datetime
    duration: float
    outcome: str


class DBWorkflowUsageRecordModel(BaseModel):
    id: int
    workflow_id: int
    timestamp: str


class TasksStatisticsEntry(BaseModel):
    uuid: str
    workflow: str
    state: str
    created_at: datetime
    execution_time_seconds: int
