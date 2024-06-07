from enum import Enum, auto


class OrchestratorErrorCodes(Enum):
    OK = auto()
    CANCELLED = auto()
    COULD_NOT_FIND_CONFIGURATION = auto()
    COULD_NOT_PARSE_CONFIGURATION = auto()
    DATABASE_CONNECTION_REFUSED = auto()
    CONTENT_NOT_FOUND = auto()
    CONTINUE_TASK_FAILED = auto()
    RESTART_NODE_FAILED = auto()


class OrchestratorState(Enum):
    STOPPED = 0
    RUNNING = 1
    ERROR = 2
