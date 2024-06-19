"""
This module contains the abstract definition of a node. The BaseNode implements this abstract class for a common
execution behavior across the project.
"""

from abc import ABC, abstractmethod
from typing import Self

from ..database import DatabaseConnector
from ..nodes.models import BaseNodeModel


class ABCBaseNode(ABC):
    """
    Global all-purpose abstract base class for a node
    """

    @abstractmethod
    def execute(self, db: DatabaseConnector, task_id: str, workflow: "Workflow", src: Self, dst: Self,
                args: dict[str, any] = None) -> tuple[int, str | None]:
        """
        Execute the node core code

        :param db: Database connector
        :param task_id: Caller task's id
        :param workflow: Workflow bind to the task
        :param src: Source node
        :param dst: Destination node
        :param args: Execution arguments
        :return: The error code and optional message
        """

    @abstractmethod
    def serialize(self) -> BaseNodeModel:
        """
        Serialize the node information

        :return: The serialized node
        """

    @abstractmethod
    def is_usable(self) -> bool:
        """
        Check the usability of a node

        :return: True if the node is usable, false otherwise
        """

    @abstractmethod
    def save_properties(self, db: DatabaseConnector) -> None:
        """
        Save in the database the node properties if some

        :param db: Database connector
        """
