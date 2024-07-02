"""
This module contains all the node's enumerations.
"""

from enum import Enum, auto


class NodeState(Enum):
    """Enumeration for node states"""
    AVAILABLE = auto()
    IN_USE = auto()
    RECOVERY = auto()
    OFFLINE = auto()
    ERROR = auto()
    RESTARTING = auto()


class NodeErrorNextStep(Enum):
    """
    Enumeration to use when a node is in error and the task needs to continue.
    If the value `SELF` is used, the task redo the current node, and `NEXT` goes to the next one.
    """
    SELF = 0
    NEXT = 1
