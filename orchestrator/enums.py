from enum import Enum


class OrchestratorErrorCodes(Enum):
    OK = 0
    CANCELLED = 1
    COULD_NOT_FIND_CONFIGURATION = 2
    COULD_NOT_PARSE_CONFIGURATION = 3
    DATABASE_CONNECTION_REFUSED = 4


class OrchestratorState(Enum):
    STOPPED = 0
    RUNNING = 1
    ERROR = 2
