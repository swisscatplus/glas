from enum import Enum, auto


class TaskState(Enum):
    PENDING = auto()
    ACTIVE = auto()
    FINISHED = auto()
    ERROR = auto()
