"""
This module contains the data models for a node when serialized.
"""

# pylint: disable=missing-class-docstring

from typing import Optional

from pydantic import BaseModel


class BaseNodeModel(BaseModel):
    """Serialization of a node"""
    id: str
    name: str
    status: str
    online: bool
    task_id: Optional[str]
