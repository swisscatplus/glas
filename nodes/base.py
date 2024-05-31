import threading
import time
import json
from typing import Self, Dict

from loguru import logger

from ..database import DatabaseConnector, DBNodeCallRecord
from ..nodes.models import BaseNodeModel
from ..nodes.abc import ABCBaseNode
from ..nodes.enums import NodeState
from ..logger import insert_data_sample


class BaseNode(ABCBaseNode):
    def __init__(self, _id: str, name: str, args: Dict[str, any] = None) -> None:
        self.id = _id
        self.name = name
        self.state = NodeState.AVAILABLE
        self.mu = threading.Lock()
        self.logger = logger.bind(app=f"Node {name}")   

    def __repr__(self) -> str:
        return self.name

    def is_error(self) -> bool:
        return self.state == NodeState.ERROR

    def is_available(self) -> bool:
        return self.state == NodeState.AVAILABLE

    def error(self) -> None:
        self.state = NodeState.ERROR

    def available(self) -> None:
        self.state = NodeState.AVAILABLE

    def execute(self, db: DatabaseConnector, task_id: str, wf_name: str, src: Self, dst: Self,
                args: Dict[str, any] = None,
                save: bool = True) -> tuple[int, str | None]:
        with self.mu:
            start = time.time()
            self.state = NodeState.IN_USE

            status, message, endpoint = self._execute(src, dst, args)
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
        status = self._restart()

        self.available()

        return status

    def serialize(self) -> BaseNodeModel:
        return BaseNodeModel(
            id=self.id, name=self.name, status=self.state.name, online=self.is_reachable(), type="other"
        )

    def _is_reachable(self) -> bool:
        """
        Needs to be implemented in a custom fashion for each node derived from this class.

        :return: Is the node reachable
        """
        return True

    def is_reachable(self) -> bool:
        return self._is_reachable() and not self.is_error()

    def _execute(self, src: "BaseNode", dst: "BaseNode", args: Dict[str, any] = None) -> tuple[
        int, str | None, str | None]:
        """Executes a node for simulation purposes."""
        raise NotImplementedError

    def _restart(self) -> int:
        raise NotImplementedError

    def save_properties(self, db: DatabaseConnector) -> None:
        """Save in the database the node properties if some"""
        pass
