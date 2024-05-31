import errno
import threading
from abc import ABC, abstractmethod
from typing import Callable, Dict

from loguru import logger

from .enums import OrchestratorErrorCodes
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

        if self.emulate:
            print("")
            print("┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓")
            print("┃                                                                              ┃")
            print("┃                              !!! WARNING !!!                                 ┃")
            print("┃                                                                              ┃")
            print("┃       You are running this program in EMULATION MODE.                        ┃")
            print("┃                                                                              ┃")
            print("┃       This mode is intended for testing and development purposes only.       ┃")
            print("┃                                                                              ┃")
            print("┃       Some features may not work as expected, and performance might be       ┃")
            print("┃       different from the live environment.                                   ┃")
            print("┃                                                                              ┃")
            print("┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛")
            print("")

        self.nodes_path = nodes_path
        self.workflows_path = workflows_path
        self.nodes: list[BaseNode] = []
        self.workflows: list[Workflow] = []

        self.terminate_event = threading.Event()

        self.running_mutex = threading.Lock()
        self.running_tasks: list[tuple[threading.Thread, Task]] = []

        self.workflow_runner_mutex = threading.Lock()
        self.workflow_runner_threads: list[threading.Thread] = []

        self._stop_callback: Callable[[], None] = lambda: None
        self._start_callback: Callable[[], None] = lambda: None

    @abstractmethod
    def _load_workflows(self, path: str) -> OrchestratorErrorCodes:
        raise NotImplementedError

    @abstractmethod
    def _load_nodes(self, path: str) -> OrchestratorErrorCodes:
        raise NotImplementedError

    def register_stop_callback(self, callback: Callable) -> None:
        self._stop_callback = callback

    def register_start_callback(self, callback: Callable) -> None:
        self._start_callback = callback

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

    def get_workflow_by_name(self, name: str) -> Workflow | None:
        found = list(filter(lambda w: w.name == name, self.get_workflows()))

        return found[0] if len(found) == 1 else None

    def get_workflows(self) -> list[Workflow]:
        return self.workflows

    def get_state(self) -> OrchestratorState:
        return self.state

    def is_running(self) -> bool:
        return not self.terminate_event.is_set()

    def start(self) -> OrchestratorErrorCodes:
        if self.state == OrchestratorState.RUNNING:
            self.logger.info("already running")
            return OrchestratorErrorCodes.CANCELLED

        self.terminate_event.clear()
        self.logger.info("starting...")

        db = DatabaseConnector()
        if not db.is_connected():
            return OrchestratorErrorCodes.DATABASE_CONNECTION_REFUSED

        if (err_code := self._load_nodes(self.nodes_path)) != OrchestratorErrorCodes.OK:
            self.state = OrchestratorState.ERROR
            return err_code

        if (err_code := self._load_workflows(self.workflows_path)) != OrchestratorErrorCodes.OK:
            self.state = OrchestratorState.ERROR
            return err_code

        self.state = OrchestratorState.RUNNING
        self.logger.success("started")

        self._start_callback()

        return OrchestratorErrorCodes.OK

    def stop(self) -> int:
        if self.state == OrchestratorState.STOPPED:
            self.logger.info("already stopped")
            return 1

        self._stop_callback()

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

    def add_task(self, workflow: Workflow, args: Dict[str, any] = None) -> None:
        database = DatabaseConnector()
        
        task = Task(workflow, args, self.verbose)

        DBTask.insert(database, str(task.uuid), task.workflow.id)
        DBWorkflowUsageRecord.insert(database, workflow.id)
        
        task_thread = threading.Thread(
            name=f"task:{task.workflow.name}", target=task.run, args=(self._remove_finished_task,)
        )
        task_thread.start()
        self.running_tasks.append((task_thread, task))
