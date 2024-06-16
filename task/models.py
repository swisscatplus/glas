"""
This module contains the data models for the task serialization.
"""

# pylint: disable=missing-function-docstring

from typing import Optional

from pydantic import BaseModel

from ..workflow.models import WorkflowModel


class TaskModel(BaseModel):
    """Task serialization model"""
    uuid: str
    workflow: WorkflowModel
    current_step: int
    state: str
    args: Optional[dict]
