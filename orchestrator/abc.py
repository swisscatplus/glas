from abc import ABC, abstractmethod

from scheduler.orchestrator.enums import OrchestratorState
from scheduler.workflow.core import Workflow


class IOrchestrator(ABC):
    @abstractmethod
    def start(self) -> None:
        ...

    @abstractmethod
    def stop(self) -> None:
        ...

    @abstractmethod
    def get_state(self) -> OrchestratorState:
        ...

    @abstractmethod
    def is_running(self) -> bool:
        ...

    @abstractmethod
    def add_task(self, workflow: Workflow) -> None:
        ...
