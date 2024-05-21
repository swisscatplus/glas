import errno
import threading
import uuid
from datetime import datetime
from typing import Callable, Self

from loguru import logger

from ..database import DatabaseConnector, DBTask
from ..task.enums import TaskState
from ..task.models import TaskModel
from ..workflow.core import Workflow


class Task:
    def __init__(self, workflow: Workflow, verbose: bool = False) -> None:
        self.start_time = datetime.now()
        self.uuid = uuid.uuid4()
        self.workflow = workflow
        self.verbose = verbose
        self.state = TaskState.PENDING
        self.stop_flag = False
        self.current_step = -1
        self.logger = logger.bind(app=f"Task {self.uuid} : {self.workflow.name}")
        self.db = DatabaseConnector()

    def _log_info(self, *values: object):
        if self.verbose:
            self.logger.info(" ".join(values))

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
            state=self.state,
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
        unreachable_steps = filter(lambda step: not step.is_reachable(), self.workflow.steps)
        unreachable_ids = list(map(lambda step: step.id, unreachable_steps))
        return any(unreachable_ids), unreachable_ids

    def any_error_node(self) -> tuple[bool, list[str]]:
        error_nodes = filter(lambda step: step.is_error(), self.workflow.steps)
        error_ids = list(map(lambda step: step.id, error_nodes))
        return any(error_ids), error_ids

    def stop(self) -> None:
        self.stop_flag = True

    def _run(self, step_id: int = 0) -> int:
        # check task interruption
        if self.stop_flag:
            self.set_error()
            self._log_error("interrupted at node", self.workflow.steps[self.current_step].id)
            return errno.EINTR

        # check node reachability
        unreachable_node, unreachable_ids = self.any_unreachable_node()
        if unreachable_node:
            self.set_error()
            self._log_error("unreachable steps:", ",".join(unreachable_ids))
            return errno.EHOSTUNREACH

        # check node error
        error_node, error_ids = self.any_error_node()
        if error_node:
            self.set_error()
            self._log_error("node error:", ",".join(error_ids))
            return errno.EFAULT

        # stop the task execution when last node reached
        if step_id >= len(self.workflow.steps):
            return 0

        # execute the step
        self.current_step = step_id
        current_node = self.workflow.steps[step_id]
        src_node = self.workflow.steps[step_id - 1] if step_id > 0 else None
        dst_node = self.workflow.steps[step_id + 1] if step_id < len(self.workflow.steps) - 1 else None

        DBTask.update_active_step(self.db, str(self.uuid), current_node.id)

        status = current_node.execute(self.db, str(self.uuid), self.workflow.name, src_node, dst_node)
        if status != 0:
            self.set_error()
            self._log_error(f"Node execution error: {status}")
            return errno.EFAULT

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
