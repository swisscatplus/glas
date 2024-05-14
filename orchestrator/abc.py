import threading
from abc import ABC, abstractmethod

from task_scheduler.orchestrator.enums import OrchestratorState
from task_scheduler.task.core import Task
from task_scheduler.workflow.core import Workflow


class IOrchestrator(ABC):

    @abstractmethod
    def get_running_tasks(self) -> list[tuple[threading.Thread, Task]]:
        ...

    @abstractmethod
    def get_workflow_by_name(self, name: str) -> Workflow:
        ...

    @abstractmethod
    def get_workflows(self) -> list[Workflow]:
        ...

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
