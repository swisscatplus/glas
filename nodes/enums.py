from enum import Enum, auto


class NodeState(Enum):
    AVAILABLE = auto()
    IN_USE = auto()
    RECOVERY = auto()
    OFFLINE = auto()
    ERROR = auto()


class NodeErrorNextStep(Enum):
    SELF = 0
    NEXT = 1
