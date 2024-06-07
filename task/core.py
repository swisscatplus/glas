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
    def __init__(self, workflow: Workflow, args: dict[str, any] = None, verbose: bool = False) -> None:
        self.start_time = datetime.now()
        self.uuid = uuid.uuid4()
        self.workflow = workflow
        self.args = args
        self.verbose = verbose
        self.state = TaskState.PENDING
        self.stop_flag = False
        self.current_step = -1
        self.logger = LoggingManager.get_logger(f"task-{self.uuid}", app=f"Task {self.uuid}: {self.workflow.name}")
        self.db = DatabaseConnector()
        self.pause_event = threading.Event()
        self.pause_condition = threading.Condition()

    def _log_info(self, *values: object):
        if self.verbose:
            self.logger.info(" ".join(values))

    def _log_debug(self, *values: object):
        if self.verbose:
            self.logger.debug(" ".join(values))

    def _log_success(self, *values: object):
        if self.verbose:
            self.logger.success(" ".join(values))

    def _log_error(self, *values: object):
        if self.verbose:
            self.logger.error(" ".join(values))

    def _log_critical(self, *values: object):
        if self.verbose:
            self.logger.critical(" ".join(values))

    def serialize(self) -> TaskModel:
        return TaskModel(
            uuid=str(self.uuid),
            current_step=self.current_step,
            state=self.state.name,
            workflow=self.workflow.model_dump(),
        )

    def is_active(self) -> bool:
        return self.state == TaskState.ACTIVE

    def is_pending(self) -> bool:
        return self.state == TaskState.PENDING

    def is_finished(self) -> bool:
        return self.state == TaskState.FINISHED

    def is_error(self) -> bool:
        return self.state == TaskState.ERROR

    def set_active(self) -> None:
        DBTask.set_active(self.db, str(self.uuid))
        self.state = TaskState.ACTIVE

    def set_pending(self) -> None:
        self.state = TaskState.PENDING

    def set_finished(self) -> None:
        DBTask.set_finished(self.db, str(self.uuid))
        self.state = TaskState.FINISHED

    def set_error(self) -> None:
        DBTask.set_error(self.db, str(self.uuid))
        self.state = TaskState.ERROR

    def any_unreachable_node(self) -> tuple[bool, list[str]]:
        # check the reachability of all future nodes
        unreachable_steps = filter(lambda step: not step.is_reachable(), self.workflow.steps[self.current_step:])
        unreachable_ids = list(map(lambda step: step.id, unreachable_steps))
        return any(unreachable_ids), unreachable_ids

    def stop(self) -> None:
        self.stop_flag = True
        self.pause_event.clear()

    def continue_(self) -> int:
        for node in self.workflow.steps:
            if node.state in [NodeState.ERROR, NodeState.RECOVERY]:
                status = node.restart()

                if status != 0:
                    return status

        self.set_active()
        self.pause_event.clear()

        with self.pause_condition:
            self.pause_condition.notify()

        return 0

    def _recursion_exit(self, step_id: int) -> Optional[int]:
        # check task interruption
        if self.stop_flag:
            self.set_error()
            self._log_error("interrupted at node", self.workflow.steps[self.current_step].name)
            return errno.EINTR

        # check node reachability, which include whether a node is in the error state
        unreachable_node, unreachable_ids = self.any_unreachable_node()
        if unreachable_node:
            self.set_error()
            self._log_error("unreachable steps:", ",".join(unreachable_ids))
            return errno.EHOSTUNREACH

        # stop the task execution when last node reached
        if step_id >= len(self.workflow.steps):
            return 0

        return None

    def _pre_step_execution(self, current_node: BaseNode, src_node: BaseNode, dst_node: BaseNode):
        pass

    def _post_step_execution(self, status: int, message: str, current_node: BaseNode, src_node: BaseNode, dst_node: BaseNode):
        pass

    def _run(self, step_id: int = 0) -> int:
        if (exit_code := self._recursion_exit(step_id)) is not None:
            return exit_code

        # fetch the step nodes (source, current, destination)
        self.current_step = step_id
        current_node = self.workflow.steps[step_id]
        src_node = self.workflow.steps[step_id - 1] if step_id > 0 else None
        dst_node = self.workflow.steps[step_id + 1] if step_id < len(self.workflow.steps) - 1 else None

        self._pre_step_execution(current_node, src_node, dst_node)

        DBTask.update_active_step(self.db, str(self.uuid), current_node.id)
        status, message = current_node.execute(self.db, str(self.uuid), self.workflow.name, src_node, dst_node, self.args)

        self._post_step_execution(status, message, current_node, src_node, dst_node)

        if status != 0:
            self.set_error()
            self._log_error(f"Node execution error [{current_node.name}]: {status}: {message}")
            self.pause_event.set()

        with self.pause_condition:
            while self.pause_event.is_set():
                self.logger.warning("waiting for task to continue")
                self.pause_condition.wait()

        return self._run(self.current_step + 1)

    def run(self, callback: Callable[[threading.Thread, Self], None]) -> int:
        self.stop_flag = False
        self.set_pending()

        self.start_time = datetime.now()

        self.set_active()
        self._log_info("started")

        status = self._run()
        if status == 0:
            self.set_finished()
            self._log_success("finished")

        callback(threading.current_thread(), self)
        return status
