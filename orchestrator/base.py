"""
This module contains the base orchestrator used by the base scheduler in order to manager nodes and tasks.
"""
import os
import threading
from abc import ABC, abstractmethod
from typing import Callable, Optional, IO, BinaryIO
import requests

from .enums import OrchestratorErrorCodes
from ..database import DatabaseConnector, DBTask, DBWorkflowUsageRecord, DBWorkflow, DBStep
from ..database.models import DBWorkflowModel, DBStepModel
from ..logger import LoggingManager
from ..nodes.base import BaseNode
from ..orchestrator.enums import OrchestratorState
from ..task.core import Task
from ..workflow.core import Workflow


class BaseOrchestrator(ABC):
    """
    Base orchestrator class which need to be extended to be used. The `_load_nodes` and `_load_workflows` methods
    must be implemented to populate the nodes and workflows lists.
    """

    def __init__(self, nodes_path: str, workflows_path: str, emulate: bool = False) -> None:
        self.logger = LoggingManager.get_logger("orchestrator", app="Orchestrator")
        self._emulate = emulate
        self._state = OrchestratorState.STOPPED

        if self._emulate:
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

        self._nodes_path = nodes_path
        self._workflows_path = workflows_path

        self._nodes: list[BaseNode] = []
        self._workflows: list[Workflow] = []

        self._terminate_event = threading.Event()

        self._running_mutex = threading.Lock()
        self._running_tasks: list[tuple[threading.Thread, Task]] = []

        self._stop_callback: Callable[[], None] = lambda: None
        self._start_callback: Callable[[], None] = lambda: None

    @abstractmethod
    def _load_workflows(self, file: IO) -> OrchestratorErrorCodes:
        """
        Parse and store the workflows defined in the file

        :param file: Configuration file
        :return: Orchestrator error code
        """

    @abstractmethod
    def _load_nodes(self, file: IO) -> OrchestratorErrorCodes:
        """
        Parse and store the nodes defined in the file

        :param file: Configuration file
        :return: Orchestrator error code
        """

    def register_stop_callback(self, callback: Callable) -> None:
        """
        Register a callback function to be called just before the stop event is set

        :param callback: Callback function
        """
        self._stop_callback = callback

    def register_start_callback(self, callback: Callable) -> None:
        """
        Register a callback function to be called just after the starting procedure ended

        :param callback: Callback function
        """
        self._start_callback = callback

    @property
    def nodes(self) -> list[BaseNode]:
        return self._nodes

    @property
    def workflows(self) -> list[Workflow]:
        return self._workflows

    @property
    def running_tasks(self) -> list[tuple[threading.Thread, Task]]:
        return self._running_tasks

    @property
    def state(self) -> OrchestratorState:
        return self._state

    @classmethod
    def get_all_db_workflows(cls) -> list[DBWorkflowModel]:
        return DBWorkflow.get_all(DatabaseConnector())

    @classmethod
    def get_steps(cls, workflow_id: int) -> list[DBStepModel]:
        return DBStep.get_all_for_workflow(DatabaseConnector(), workflow_id)

    def _remove_finished_task(self, task_thread: threading.Thread, task: Task):
        """
        Remove a given task from the list of running tasks

        :param task_thread: Thread of the task
        :param task: Task itself
        """
        with self._running_mutex:
            self._running_tasks.remove((task_thread, task))

    def get_task_by_id(self, task_id: str) -> Optional[Task]:
        """
        Retrieve a task by its ID

        :param task_id: Task id
        :return: Task found, None otherwise
        """
        for _, task in self._running_tasks:
            if str(task.uuid) == task_id:
                return task
        return None
    
    def get_node_by_id(self, node_id: str) -> Optional[BaseNode]:
        """
        Retrieve a node by its ID

        :param node_id: Node id
        :return: Node found, None otherwise
        """
        for node in self.nodes:
            if node.id == node_id:
                return node
        return None

    def get_workflow_by_name(self, name: str) -> Optional[Workflow]:
        """
        Retrieve a workflow by its name

        :param name: Workflow name
        :return: Workflow found, None otherwise
        """
        return next((w for w in self._workflows if w.name == name), None)

    def is_running(self) -> bool:
        return not self._terminate_event.is_set()

    def _set_error(self, message: Optional[str] = None) -> None:
        self._state = OrchestratorState.ERROR
        if message is not None:
            self.logger.error(message)

    def load_config(self, nodes_config: BinaryIO = None, workflows_config: BinaryIO = None) -> OrchestratorErrorCodes:
        """
        Clear the already stored nodes and workflows, and load the newly given config

        :param nodes_config: Nodes configuration
        :param workflows_config: Workflows configuration
        :return: Orchestrator error code
        """
        # pylint: disable=consider-using-with
        if nodes_config is None:
            nodes_config = open(self._nodes_path, "rb")
        if workflows_config is None:
            workflows_config = open(self._workflows_path, "rb")

        # load the nodes
        self._nodes.clear()
        if (err_code := self._load_nodes(nodes_config)) != OrchestratorErrorCodes.OK:
            self._set_error(f"nodes config file not found: {nodes_config}")
            nodes_config.close()
            workflows_config.close()
            return err_code

        if len(self._nodes) == 0:
            self.logger.error("no nodes found")
        else:
            successfully_loaded = [n for n in self._nodes if not n.is_error()]
            self.logger.success(f"successfully loaded {len(successfully_loaded)} nodes")
            if len(self._nodes) != len(successfully_loaded):
                self.logger.error(f"failed to load {len(self._nodes) - len(successfully_loaded)} nodes")

        # load the workflows
        self._workflows.clear()
        if (err_code := self._load_workflows(workflows_config)) != OrchestratorErrorCodes.OK:
            message = None
            match err_code:
                case OrchestratorErrorCodes.COULD_NOT_FIND_CONFIGURATION:
                    message = f"workflows config file not found: {workflows_config}"
                case OrchestratorErrorCodes.COULD_NOT_PARSE_CONFIGURATION:
                    message = f"workflows config file incorrect: {workflows_config}"

            self._set_error(message)
            nodes_config.close()
            workflows_config.close()
            return err_code

        if len(self._workflows) == 0:
            self.logger.error("no workflows found")
        else:
            self.logger.success(f"successfully loaded {len(self._workflows)} workflows")

        nodes_config.close()
        workflows_config.close()

        return OrchestratorErrorCodes.OK

    def start(self) -> OrchestratorErrorCodes:
        """
        Start the orchestrator

        :return: Orchestrator error code
        """
        if self._state == OrchestratorState.RUNNING:
            self.logger.info("already running")
            return OrchestratorErrorCodes.CANCELLED

        self._terminate_event.clear()
        self.logger.info("starting...")

        db = DatabaseConnector()
        if not db.is_connected():
            return OrchestratorErrorCodes.DATABASE_CONNECTION_REFUSED

        if (err_code := self.load_config()) != OrchestratorErrorCodes.OK:
            self._state = OrchestratorState.ERROR
            return err_code

        self._state = OrchestratorState.RUNNING
        self.logger.success("started")

        self._start_callback()

        return OrchestratorErrorCodes.OK

    def stop(self) -> OrchestratorErrorCodes:
        """
        Stop the orchestrator

        :return: Orchestrator error code
        """
        if self._state == OrchestratorState.STOPPED:
            self.logger.info("already stopped")
            return OrchestratorErrorCodes.CANCELLED

        self._stop_callback()

        self._terminate_event.set()
        self.logger.warning("stopping...")

        # interrupt all running task and terminate all threads
        for _, task in self._running_tasks:
            task.stop()

        for thread, _ in self._running_tasks:
            thread.join()

        self._running_tasks.clear()

        # shutdown all nodes
        for node in self._nodes:
            node.shutdown()

        self._nodes.clear()
        self._workflows.clear()

        self._state = OrchestratorState.STOPPED
        self.logger.warning("stopped")

        return OrchestratorErrorCodes.OK

    def add_task(self, workflow: Workflow, args: Optional[dict[str, any]] = None) -> Task:
        """
        Add a task to the orchestrator

        :param workflow: Workflow to bind to the task (defines the steps)
        :param args: Optional arguments to pass to the task
        """
        database = DatabaseConnector()

        task = Task(workflow, args)

        DBTask.insert(database, str(task.uuid), task.workflow.id, args)
        DBWorkflowUsageRecord.insert(database, workflow.id)

        task_thread = threading.Thread(
            name=f"task:{task.workflow.name}", target=task.run, args=(self._remove_finished_task,)
        )
        task_thread.start()
        self._running_tasks.append((task_thread, task))

        return task

    def pause_task(self, uuid: str) -> OrchestratorErrorCodes:
        """
        Pause a task to let an operator enter without risk in the laboratory

        :param uuid: UUID of the task to pause
        :return: Orchestrator error code
        """
        task = self.get_task_by_id(uuid)

        if task is None:
            return OrchestratorErrorCodes.CONTENT_NOT_FOUND

        self.logger.info(f"pausing task {uuid}")
        if task.pause_execution() != 0:
            self.logger.error(f"Impossible to pause task: {uuid}")
            return OrchestratorErrorCodes.CANCELLED

        return OrchestratorErrorCodes.OK

    def continue_task(self, uuid: str) -> OrchestratorErrorCodes:
        """
        Continue a task that has been stopped due to an error

        :param uuid: UUID of the task to continue
        :return: Orchestrator error code
        """
        task = self.get_task_by_id(uuid)

        if task is None:
            return OrchestratorErrorCodes.CONTENT_NOT_FOUND

        self.logger.info(f"continuing task {uuid}")
        if task.continue_execution() != 0:
            self.logger.critical(f"Impossible to continue task: {uuid}")
            return OrchestratorErrorCodes.CONTINUE_TASK_FAILED

        return OrchestratorErrorCodes.OK

    def restart_node(self, node_id: str) -> OrchestratorErrorCodes:
        """
        Restart a node

        :param node_id: ID of the node to restart
        :return: Orchestrator error code
        """
        node = next((n for n in self._nodes if n.id == node_id), None)

        if node is None:
            return OrchestratorErrorCodes.CONTENT_NOT_FOUND

        self.logger.info(f"Restarting node {node_id}")
        if node.restart() != 0:
            self.logger.critical(f"Impossible to restart node: {node_id}")
            return OrchestratorErrorCodes.RESTART_NODE_FAILED

        return OrchestratorErrorCodes.OK
