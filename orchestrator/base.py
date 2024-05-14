import threading
from abc import ABC, abstractmethod

from loguru import logger

from ..database import DatabaseConnector, DBTask, DBWorkflowUsageRecord
from ..nodes.base import BaseNode
from ..orchestrator.enums import OrchestratorState
from ..task.core import Task
from ..workflow.core import Workflow


class BaseOrchestrator(ABC):
    def __init__(
            self,
            nodes_path: str,
            workflows_path: str,
            verbose: bool = False,
            emulate: bool = False,
    ) -> None:
        self.logger = logger.bind(app="Orchestrator")
        self.verbose = verbose
        self.emulate = emulate
        self.state = OrchestratorState.STOPPED

        self.nodes_path = nodes_path
        self.workflows_path = workflows_path
        self.nodes: list[BaseNode] = []
        self.workflows: list[Workflow] = []

        self.terminate_event = threading.Event()

        self.running_mutex = threading.Lock()
        self.running_tasks: list[tuple[threading.Thread, Task]] = []

        self.workflow_runner_mutex = threading.Lock()
        self.workflow_runner_threads: list[threading.Thread] = []

    @abstractmethod
    def _load_workflows(self, path: str) -> None:
        ...

    @abstractmethod
    def _load_nodes(self, path: str) -> None:
        ...

    def _get_active_tasks(self) -> list[Task]:
        with self.running_mutex:
            return [task for _, task in self.running_tasks if task.is_active()]

    def get_all_nodes(self) -> list[BaseNode]:
        return [node for node in self.nodes]

    def _remove_finished_task(self, task_thread: threading.Thread, task: Task):
        with self.running_mutex:
            self.running_tasks.remove((task_thread, task))

    def get_running_tasks(self) -> list[tuple[threading.Thread, Task]]:
        return self.running_tasks

    def get_workflow_by_name(self, name: str) -> Workflow:
        return list(filter(lambda w: w.name == name, self.get_workflows()))[0]

    def get_workflows(self) -> list[Workflow]:
        return self.workflows

    def get_state(self) -> OrchestratorState:
        return self.state

    def is_running(self) -> bool:
        return not self.terminate_event.is_set()

    def start(self) -> int:
        if self.state == OrchestratorState.RUNNING:
            self.logger.info("already running")
            return 1

        self.terminate_event.clear()
        self.logger.info("starting...")

        self._load_nodes(self.nodes_path)
        self._load_workflows(self.workflows_path)

        self.state = OrchestratorState.RUNNING
        self.logger.success("started")

        return 0

    def stop(self) -> int:
        if self.state == OrchestratorState.STOPPED:
            self.logger.info("already stopped")
            return 1

        self.terminate_event.set()
        self.logger.warning("stopping...")

        for _, task in self.running_tasks:
            task.stop()

        for thread, _ in self.running_tasks:
            thread.join()

        self.running_tasks.clear()

        self.nodes.clear()
        self.workflows.clear()

        self.state = OrchestratorState.STOPPED
        self.logger.warning("stopped")

        return 0

    def add_task(self, workflow: Workflow) -> None:
        database = DatabaseConnector()
        task = Task(workflow, self.verbose)

        DBTask.insert(database, str(task.uuid), task.workflow.id)
        DBWorkflowUsageRecord.insert(database, workflow.id)

        task_thread = threading.Thread(
            name=f"task:{task.workflow.name}", target=task.run, args=(self._remove_finished_task,)
        )
        task_thread.start()
        self.running_tasks.append((task_thread, task))
