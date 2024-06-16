"""
This file defines the models used in the GLAS routing system.
"""

# pylint: disable=missing-class-docstring

from typing import Dict, Optional

from pydantic import BaseModel


class PostTask(BaseModel):
    workflow_name: str
    args: Optional[Dict] = None


class PatchConfig(BaseModel):
    nodes_config: str
    workflows_config: str


class PatchTask(BaseModel):
    task_id: str


class PatchNode(BaseModel):
    name: str
