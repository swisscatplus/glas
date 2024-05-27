from abc import ABC, abstractmethod

from typing import Self

from ..database import DatabaseConnector
from ..nodes.models import BaseNodeModel


class ABCBaseNode(ABC):
    @abstractmethod
    def is_error(self) -> bool:
        ...

    @abstractmethod
    def error(self) -> None:
        ...

    @abstractmethod
    def execute(self, db: DatabaseConnector, task_id: str, wf_name: str, src: Self, dst: Self,
                save: bool = True) -> int:
        ...

    @abstractmethod
    def serialize(self) -> BaseNodeModel:
        ...

    @abstractmethod
    def is_reachable(self) -> bool:
        """Check the reachability of a node.

        Note: This method's implementation is based on current specifications for
        simulation purposes only. It will need to raise a NotImplementedError when
        using real hardware.

        For now, it returns True for simulation purposes.

        Future modifications:
        - raise NotImplementedError
        """
        ...

    @abstractmethod
    def _execute(self, src: Self, dst: Self) -> tuple[int, str | None]:
        """Executes a node for simulation purposes."""
        ...

    @abstractmethod
    def save_properties(self, db: DatabaseConnector) -> None:
        """Save in the database the node properties if some"""
        ...