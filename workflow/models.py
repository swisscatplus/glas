"""
This module contains the data models for the workflow serialization.
"""

# pylint: disable=missing-class-docstring

from pydantic import BaseModel

from ..nodes.models import BaseNodeModel


class WorkflowModel(BaseModel):
    """Workflow serialization model"""
    id: int
    name: str
    source: BaseNodeModel
    destination: BaseNodeModel
    steps: list[BaseNodeModel]
