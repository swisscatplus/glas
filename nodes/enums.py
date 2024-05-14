from enum import Enum, auto


class NodeState(Enum):
    AVAILABLE = auto()
    IN_USE = auto()
    ERROR = auto()
