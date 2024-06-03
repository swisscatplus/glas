import threading
import time
from typing import Self

from ..database import DatabaseConnector, DBNodeCallRecord
from ..logger import insert_data_sample, LoggingManager
from ..nodes.abc import ABCBaseNode
from ..nodes.enums import NodeState
from ..nodes.models import BaseNodeModel


class BaseNode(ABCBaseNode):
    def __init__(self, _id: str, name: str) -> None:
        self.id = _id
        self.name = name
        self.state = NodeState.AVAILABLE
        self.mu = threading.Lock()
        self.logger = LoggingManager.get_logger(self.id, app=f"Node {self.name}")
        
    def __repr__(self) -> str:
        return self.name

    def is_error(self) -> bool:
        return self.state == NodeState.ERROR

    def is_available(self) -> bool:
        return self.state == NodeState.AVAILABLE

    def error(self) -> None:
        """Deprecated, use self.set_error()"""
        self.state = NodeState.ERROR

    def available(self) -> None:
        self.state = NodeState.AVAILABLE

    def execute(self, db: DatabaseConnector, task_id: str, wf_name: str, src: Self, dst: Self,
                args: dict[str, any] = None, save: bool = True) -> tuple[int, str | None]:
        with self.mu:
            start = time.time()
            self.state = NodeState.IN_USE

            status, message, endpoint = self._execute(src, dst, task_id, args)
            if status != 0:
                self.error()
                DBNodeCallRecord.insert(db, self.id, endpoint, message, time.time() - start, "error")
                return status, message

            DBNodeCallRecord.insert(db, self.id, endpoint, message, time.time() - start, "success")
            self.state = NodeState.AVAILABLE

            if save:
                insert_data_sample(task_id, wf_name, self.id, start, time.time())

            return 0, None

    def restart(self) -> int:
        self.logger.info("restarting...")

        status = self._restart()

        if status == 0:
            self.available()
            self.logger.success("restarted successfully")
        else:
            self.logger.error(f"restart failed: {status}")

        return status

    def shutdown(self):
        pass

    def serialize(self) -> BaseNodeModel:
        return BaseNodeModel(
            id=self.id, name=self.name, status=self.state.name, online=self.is_reachable()
        )

    def _is_reachable(self) -> bool:
        """
        Needs to be implemented in a custom fashion for each node derived from this class.

        :return: Is the node reachable
        """
        return True

    def is_reachable(self) -> bool:
        return self._is_reachable() and not self.is_error()

    def _execute(self, src: Self, dst: Self, task_id: str, args: dict[str, any] = None) -> tuple[int, str | None, str | None]:
        raise NotImplementedError

    def _restart(self) -> int:
        return 0

    def save_properties(self, db: DatabaseConnector) -> None:
        """Save in the database the node properties if some"""
        pass

    def set_error(self, message: str):
        self.state = NodeState.ERROR
        self.logger.error(message)
