"""
This module contains the base class for all GLAS nodes. The common behavior allows the project to run in a predictable
manner also allows to have a common logging scheme and basic error handling.
"""

import threading
import time
from typing import Self, Optional, TypeVar

from ..database import DatabaseConnector, DBNodeCallRecord, DBNode
from ..logger import LoggingManager
from ..nodes.abc import ABCBaseNode
from ..nodes.enums import NodeState, NodeErrorNextStep
from ..nodes.models import BaseNodeModel

Workflow = TypeVar("Workflow")


class BaseNode(ABCBaseNode):
    """
    Base class for all GLAS nodes. By default, no core execution has been implemented and is left to the developers in
    the _execute method.
    """

    def __init__(self, _id: str, name: str) -> None:
        self.id = _id
        self.name = name
        self.state = NodeState.AVAILABLE
        self.mu = threading.Lock()
        self.logger = LoggingManager.get_logger(self.id, app=f"Node {self.name}")
        self._task_id = None

        DBNode.update_state(DatabaseConnector(), self.id, self.state.value)

    def __repr__(self) -> str:
        return self.name

    def _pre_execution(self, task_id: str, wf_name: str, src: "BaseNode", dst: "BaseNode",
                       args: Optional[dict[str, any]] = None) -> None:
        """
        Method execute just before the _execute call.

        :param task_id: Caller task's id
        :param wf_name: Workflow bind to the task
        :param src: Source node
        :param dst: Destination node
        :param args: Execution arguments
        """

    def _post_execution(self, status: int, msg: str, task_id: str, wf_name: str, src: "BaseNode", dst: "BaseNode",
                        args: Optional[dict[str, any]] = None) -> None:
        """
        Method execute just after the _execute call.

        :param status: _execute status
        :param msg: _execute message
        :param task_id: Caller task's id
        :param wf_name: Workflow bind to the task
        :param src: Source node
        :param dst: Destination node
        :param args: Execution arguments
        """

    def is_reachable(self) -> bool:
        """
        Node specific implementation of the reachability test

        :return: Is the node reachable
        """
        return True

    def _execute(self, src: Self, dst: Self, task_id: str, args: Optional[dict[str, any]] = None) -> tuple[
        int, Optional[str], Optional[str]]:
        """
        Node specific implementation of its own execution logic

        :param src: Source node
        :param dst: Destination node
        :param task_id: Caller task's id
        :param args: Execution arguments
        :return:
        """
        return 0, None, None

    def _restart(self) -> int:
        """
        Node specific implementation of its own restart logic

        :return: Restart status
        """
        return 0

    def _shutdown(self) -> int:
        """
        Node specific implementation of its own shutdown logic

        :return: Shutdown status
        """
        return 0

    def next_node_execution(self) -> NodeErrorNextStep:
        return NodeErrorNextStep.NEXT

    def execute(self, db: DatabaseConnector, task_id: str, workflow: "Workflow", src: Self, dst: Self,
                args: Optional[dict[str, any]] = None, save: bool = True) -> tuple[int, Optional[str]]:
        """
        Common wrapper around the specific `_execute` method.

        This wrapper ensure thread-safe execution by using a mutex and aims to set the node state automatically
        according to the execution result. It also saves in the database all the state changes and execution statistics,
        as well as the execution time log for the graph view.

        :param db: Database connector
        :param task_id: Caller task's id
        :param workflow: Workflow bind to the task
        :param src: Source node
        :param dst: Destination node
        :param args: Execution arguments
        :param save: Save the execution time log
        :return: The error code and optional message
        """
        start = time.time()

        with self.mu:
            # save the access waiting time
            if save:
                LoggingManager.insert_data_sample(task_id, workflow.id, "w. acc.", start, time.time())

            self._task_id = task_id
            task_logger = LoggingManager.get_logger(f"task-{task_id}")
            task_logger.debug(f"Executing {self}...")

            start = time.time()
            self.state = NodeState.IN_USE
            DBNode.update_state(db, self.id, self.state.value)

            # call the implementation specific `_execute` method
            self._pre_execution(task_id, workflow.name, src, dst, args)
            # pylint: disable=assignment-from-no-return
            status, message, endpoint = self._execute(src, dst, task_id, args)

            if status != 0:
                self.state = NodeState.ERROR
                DBNode.update_state(db, self.id, self.state.value)
                DBNodeCallRecord.insert(db, self.id, endpoint, message, time.time() - start, "error")
                self._task_id = None
                return status, message

            self._post_execution(status, message, task_id, workflow.name, src, dst, args)

            DBNodeCallRecord.insert(db, self.id, endpoint, message, time.time() - start, "success")
            self.state = NodeState.AVAILABLE
            DBNode.update_state(db, self.id, self.state.value)

            if save:
                LoggingManager.insert_data_sample(task_id, workflow.id, self.id, start, time.time())

            self._task_id = None

            return 0, None

    def serialize(self) -> BaseNodeModel:
        return BaseNodeModel(
            id=self.id, name=self.name, status=self.state.name, online=self.is_reachable(), task_id=self._task_id
        )

    def is_usable(self) -> bool:
        return self.is_reachable() and not self.is_error()

    def save_properties(self, db: DatabaseConnector) -> None:
        """
        Empty saving procedure, left to the user to implement for each child classes

        :param db: Database connector
        """

    def restart(self) -> int:
        """
        Restart the node

        :return: Restart status
        """
        self.logger.info("restarting...")

        status = self._restart()

        if status == 0:
            self.set_available()
            self.logger.success("restarted successfully")
        else:
            self.logger.error(f"restart failed: {status}")

        DBNode.update_state(DatabaseConnector(), self.id, self.state.value)

        return status

    def shutdown(self):
        """
        Shutdown the node
        """
        self.logger.warning("shutting down...")

        status = self._shutdown()

        if status == 0:
            self.logger.success("shutdown successfully")
        else:
            self.logger.error(f"shutdown failed: {status}")

        DBNode.update_state(DatabaseConnector(), self.id, NodeState.OFFLINE.value)

    def is_error(self) -> bool:
        return self.state == NodeState.ERROR

    def is_available(self) -> bool:
        return self.state == NodeState.AVAILABLE

    def set_error(self, message: str = "No Comment"):
        self.state = NodeState.ERROR
        db = DatabaseConnector()
        DBNode.update_state(db, self.id, self.state.value)
        self.logger.error(message)

    def set_available(self) -> None:
        self.state = NodeState.AVAILABLE
