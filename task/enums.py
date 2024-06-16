"""
This module contains the enumeration used by tasks.
"""

from enum import Enum, auto


class TaskState(Enum):
    """Enumeration for the task's state"""
    PENDING = auto()
    ACTIVE = auto()
    FINISHED = auto()
    ERROR = auto()
