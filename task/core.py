import errno
import threading
import uuid
from datetime import datetime
from typing import Callable, Self, Optional

from ..database import DatabaseConnector, DBTask
from ..logger import LoggingManager
from ..nodes.base import BaseNode
from ..nodes.enums import NodeState
from ..task.enums import TaskState
from ..task.models import TaskModel
from ..workflow.core import Workflow


class Task:
    def __init__(self, workflow: Workflow, args: dict[str, any] = None) -> None:
        self._start_time = datetime.now()
        self._uuid = uuid.uuid4()
        self._workflow = workflow
        self._args = args
        self._state = TaskState.PENDING
        self._stop_flag = False
        self._current_step = -1
        self._db = DatabaseConnector()
        self._pause_event = threading.Event()
        self._pause_condition = threading.Condition()

        self.logger = LoggingManager.get_logger(f"task-{self._uuid}", app=f"Task {self._uuid}: {self._workflow.name}")

    def serialize(self) -> TaskModel:
        return TaskModel(
            uuid=str(self._uuid),
            current_step=self._current_step,
            state=self._state.name,
            workflow=self._workflow.model_dump(),
        )

    def is_active(self) -> bool:
        return self._state == TaskState.ACTIVE

    def is_pending(self) -> bool:
        return self._state == TaskState.PENDING

    def is_finished(self) -> bool:
        return self._state == TaskState.FINISHED

    def is_error(self) -> bool:
        return self._state == TaskState.ERROR

    def set_active(self) -> None:
        DBTask.set_active(self._db, str(self._uuid))
        self._state = TaskState.ACTIVE

    def set_pending(self) -> None:
        self._state = TaskState.PENDING

    def set_finished(self) -> None:
        DBTask.set_finished(self._db, str(self._uuid))
        self._state = TaskState.FINISHED

    def set_error(self) -> None:
        DBTask.set_error(self._db, str(self._uuid))
        self._state = TaskState.ERROR

    def any_unreachable_node(self) -> tuple[bool, list[str]]:
        """
        Is there any unreachable nodes in the future steps

        :return: A tuple of a boolean if any unreachable nodes were found and the list of those unreachable nodes
        """
        # check the reachability of all future nodes
        unreachable_steps = filter(lambda step: not step.is_usable(), self._workflow.steps[self._current_step:])
        unreachable_ids = list(map(lambda step: step.id, unreachable_steps))
        return any(unreachable_ids), unreachable_ids

    def stop(self) -> None:
        self._stop_flag = True
        self._pause_event.clear()
        self._pause_event.clear()

    def continue_execution(self) -> int:
        """
        Continue the execution of the task when the task has been paused.

        The pause is only set when a step encounters an error. In this case, the task will pause after the node in error
        state has exited. Thus, the continuation will start at the next node.

        :return: Restart status
        """
        for node in self._workflow.steps:
            if node.state in [NodeState.ERROR, NodeState.RECOVERY]:
                status = node.restart()

                if status != 0:
                    return status

        self.set_active()
        self._pause_event.clear()

        with self._pause_condition:
            self._pause_condition.notify()

        return 0

    def _recursion_exit(self, step_id: int) -> Optional[int]:
        # check task interruption
        if self._stop_flag:
            self.set_error()
            self.logger.error("interrupted at node", self._workflow.steps[self._current_step].name)
            return errno.EINTR

        # check node reachability, which include whether a node is in the error state
        unreachable_node, unreachable_ids = self.any_unreachable_node()
        if unreachable_node:
            self.set_error()
            self.logger.error("unreachable steps:", ",".join(unreachable_ids))
            return errno.EHOSTUNREACH

        # stop the task execution when last node reached
        if step_id >= len(self._workflow.steps):
            return 0

        return None

    def _pre_step_execution(self, current_node: BaseNode, src_node: BaseNode, dst_node: BaseNode):
        pass

    def _post_step_execution(self, status: int, message: str, current_node: BaseNode, src_node: BaseNode,
                             dst_node: BaseNode):
        pass

    def _run(self, step_id: int = 0) -> int:
        """
        Task execution core code. This method is executed in a recursive manner, starting at step 0 and ending when all
        the steps have finished, or an interruption occurred (see self._recursion_exit for more details).

        :param step_id: Current step ID
        :return:
        """
        if (exit_code := self._recursion_exit(step_id)) is not None:
            return exit_code

        # fetch the step nodes (source, current, destination)
        self._current_step = step_id
        cur_node = self._workflow.steps[step_id]
        src_node = self._workflow.steps[step_id - 1] if step_id > 0 else None
        dst_node = self._workflow.steps[step_id + 1] if step_id < len(self._workflow.steps) - 1 else None

        self._pre_step_execution(cur_node, src_node, dst_node)
        DBTask.update_active_step(self._db, str(self._uuid), cur_node.id)
        status, msg = cur_node.execute(self._db, str(self._uuid), self._workflow.name, src_node, dst_node, self._args)
        self._post_step_execution(status, msg, cur_node, src_node, dst_node)

        if status != 0:
            self.set_error()
            self.logger.error(f"Node execution error [{cur_node.name}]: {status}: {msg}")
            self._pause_event.set()

        with self._pause_condition:
            while self._pause_event.is_set():
                self.logger.warning("waiting for task to continue")
                self.logger.info(f"Manually move the plate from {cur_node.name} to {dst_node.name}")
                self._pause_condition.wait()

        return self._run(self._current_step + 1)

    def run(self, callback: Callable[[threading.Thread, Self], None]) -> int:
        """
        Wrapper around the task execution that is run as a thread

        :param callback: Callback function that will be called when a thread exits
        :return: Execution status
        """
        self._stop_flag = False
        self.set_pending()

        self._start_time = datetime.now()

        self.set_active()
        self.logger.info("started")

        status = self._run()
        if status == 0:
            self.set_finished()
            self.logger.success("finished")

        callback(threading.current_thread(), self)
        return status
