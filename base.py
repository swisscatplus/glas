"""
This module contains the base scheduler to be used to extend the scheduling behavior wanted by your laboratory.
"""

import os
import re
from contextlib import asynccontextmanager
from typing import Awaitable, Callable

from fastapi import (APIRouter, FastAPI, HTTPException, Request, Response,
                     Security, UploadFile, status)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.security import OAuth2PasswordBearer
from uvicorn import Config, Server

from . import jwt
from .database import DatabaseConnector, DBTask, DBWorkflow
from .database.access_logs import DBAccessLogs
from .database.execution_logs import DBExecutionLogs
from .database.logs import DBLogs
from .logger import LoggingManager
from .models import PostTask
from .orchestrator.base import BaseOrchestrator
from .orchestrator.enums import OrchestratorErrorCodes, OrchestratorState
from .task.models import TaskModel


class BaseScheduler:
    """
    The BaseScheduler class contains all the necessary routes and actions needed to run a minimalistic lab scheduler. It
    can be extended as wanted by following the steps available in the official documentation to add custom behavior.
    """

    def __init__(self, orchestrator: BaseOrchestrator, port: int) -> None:
        self.logger = None

        @asynccontextmanager
        async def lifespan(_app: FastAPI):
            yield
            self.orchestrator.stop()

        self.api = FastAPI(lifespan=lifespan)
        self.api.add_middleware(
            CORSMiddleware,  # type: ignore
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.api.middleware("http")(self._ip_whitelist_middleware)

        self.api.add_exception_handler(HTTPException, self._http_exception_handler)  # type: ignore

        self.logger = LoggingManager.get_logger("glas", app="GLAS")
        self.orchestrator = orchestrator

        self.config = Config(self.api, host="0.0.0.0", port=port, log_level="warning")
        self.server = Server(config=self.config)

        # @formatter:off
        self.task_router = APIRouter(
            prefix="/task",
            tags=["GLAS Tasks"],
            dependencies=[Security(self._verify_token)],
        )
        self.orchestrator_router = APIRouter(
            prefix="/orchestrator",
            tags=["GLAS Orchestrator"],
            dependencies=[Security(self._verify_token)],
        )
        self.config_router = APIRouter(
            prefix="/config",
            tags=["GLAS Config"],
            dependencies=[Security(self._verify_token)],
        )
        self.node_router = APIRouter(
            prefix="/node",
            tags=["GLAS Nodes"],
            dependencies=[Security(self._verify_token)],
        )
        self.workflow_router = APIRouter(
            prefix="/workflow",
            tags=["GLAS Workflows"],
            dependencies=[Security(self._verify_token)],
        )
        self.log_router = APIRouter(
            prefix="/logs",
            tags=["GLAS Logs"],
            dependencies=[Security(self._verify_token)],
        )
        self.token_router = APIRouter(prefix="/token", tags=["GLAS Tokens"])
        # @formatter:on

        self._init_routes()
        self.init_extra_routes()
        self._include_routers()

    def _http_exception_handler(
        self, request: Request, exc: HTTPException
    ) -> JSONResponse:
        if exc.status_code in [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]:
            DBAccessLogs.insert(
                DatabaseConnector(),
                request.client.host,
                False,
                None,
                request.url.path,
                request.method,
            )
            self.logger.warning(
                f"Unauthorized access to {request.url.path} from {request.client.host}"
            )
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED, content=exc.detail
            )

    def _verify_localhost(self, request: Request) -> None:
        if request.client.host != "127.0.0.1":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Only localhost is allowed",
            )

    def _generate_token(self, identifier: str) -> JSONResponse:
        access_token = jwt.create_access_token(data={"sub": identifier})
        return JSONResponse(content={"token": access_token})

    def _verify_token(
        self,
        request: Request,
        token: str = Security(OAuth2PasswordBearer(tokenUrl="token")),
    ) -> str:
        identifier = jwt.verify_token(token)

        if identifier is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Could not validate credentials",
                headers={"WWW-Authenticate": "Bearer"},
            )

        DBAccessLogs.insert(
            DatabaseConnector(),
            request.client.host,
            True,
            identifier,
            request.url.path,
            request.method,
        )
        return identifier

    def bind_logger_name(self, logger_name: str):
        self.logger = LoggingManager.get_logger("scheduler", app=logger_name)

    def _init_routes(self) -> None:
        self.init_orchestrator_routes()
        self.init_task_routes()
        self._extends_orchestrator_routes()
        self._extends_task_routes()

        self.init_config_routes()
        self.init_node_routes()
        self.init_workflow_routes()
        self.init_token_routes()
        self.init_log_routes()

    def _include_routers(self) -> None:
        self.api.include_router(self.task_router)
        self.api.include_router(self.orchestrator_router)
        self.api.include_router(self.config_router)
        self.api.include_router(self.node_router)
        self.api.include_router(self.workflow_router)
        self.api.include_router(self.token_router)
        self.api.include_router(self.log_router)

    def init_extra_routes(self) -> None:
        """Override this method to add extra custom routes."""
        pass

    def _extends_orchestrator_routes(self) -> None:
        """Override this method to extends the orchestrator router."""
        pass

    def _extends_task_routes(self) -> None:
        """Override this method to extend the task router."""
        pass

    def init_config_routes(self) -> None:
        self.config_router.add_api_route(
            "/reload", self.reload_config, methods=["PATCH"]
        )

    def init_workflow_routes(self) -> None:
        self.workflow_router.add_api_route("/", self.get_workflows, methods=["GET"])

    def init_task_routes(self) -> None:
        # the route ordering matters ! Do NOT put the /{task_id} up in any case !
        self.task_router.add_api_route("/", self.lab_add_task, methods=["POST"])
        self.task_router.add_api_route(
            "/running",
            self.get_running,
            methods=["GET"],
            responses={status.HTTP_200_OK: {"model": list[TaskModel]}},
        )
        self.task_router.add_api_route(
            "/pause/{task_id}", self.pause_task, methods=["PATCH"]
        )
        self.task_router.add_api_route(
            "/continue/{task_id}", self.continue_task, methods=["PATCH"]
        )
        self.task_router.add_api_route(
            "/{task_id}", self.get_task_info, methods=["GET"]
        )

    def init_node_routes(self) -> None:
        self.node_router.add_api_route(
            "/restart/{node_id}", self.restart_node, methods=["PATCH"]
        )
        self.node_router.add_api_route(
            "/status/{node_id}", self.get_node_info, methods=["GET"]
        )

    def init_orchestrator_routes(self) -> None:
        self.orchestrator_router.add_api_route(
            "/start",
            self.start_orchestrator,
            methods=["POST"],
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                status.HTTP_204_NO_CONTENT: {
                    "description": "The orchestrator successfully started"
                },
                status.HTTP_409_CONFLICT: {
                    "description": "The orchestrator is already running"
                },
            },
        )
        self.orchestrator_router.add_api_route(
            "/stop",
            self.stop,
            methods=["DELETE"],
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                status.HTTP_204_NO_CONTENT: {
                    "description": "The orchestrator successfully stopped."
                },
                status.HTTP_409_CONFLICT: {
                    "description": "The orchestrator is already stopped."
                },
            },
        )
        self.orchestrator_router.add_api_route(
            "/status",
            self.orchestrator_status,
            methods=["GET"],
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                status.HTTP_204_NO_CONTENT: {"description": "Orchestrator is online"},
                status.HTTP_410_GONE: {"description": "Orchestrator is offline"},
            },
        )

    def init_token_routes(self) -> None:
        self.token_router.add_api_route(
            "/{identifier}",
            self._generate_token,
            dependencies=[Security(self._verify_localhost)],
        )

    def init_log_routes(self) -> None:
        self.log_router.add_api_route("/", self._logs)
        self.log_router.add_api_route("/execution", self._get_execution_logs)

    async def _ip_whitelist_middleware(
        self, request: Request, call_next: Callable[[Request], Awaitable[Response]]
    ) -> Response:
        if request.client.host not in os.getenv("AUTHORIZED_IPS", "").split(" "):
            self.logger.warning(
                f"Not allowed ip ({request.client.host}) tried to access {request.url.path}"
            )
            DBAccessLogs.insert(
                DatabaseConnector(),
                request.client.host,
                False,
                None,
                request.url.path,
                request.method,
            )
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "IP not allowed"},
            )

        response = await call_next(request)
        return response

    def run(self) -> None:
        self.logger.info(f"started on {self.config.host}:{self.config.port}")

        if (err_code := self.orchestrator.start()) != OrchestratorErrorCodes.OK:
            self.logger.critical(f"Failed to start orchestrator: {err_code}")
            return

        self.server.run()  # need to run as last

    def _logs(self):
        return DBLogs.get_all(DatabaseConnector())

    def _get_execution_logs(self):
        logs = DBExecutionLogs.get(DatabaseConnector())
        grouped_logs: dict[str, list[dict]] = {}

        db = DatabaseConnector()
        for log in logs:
            wf = DBWorkflow.get_by_id(db, log.workflow_id)

            if log.task_id not in grouped_logs:
                grouped_logs[log.task_id] = []

            grouped_logs[log.task_id].append(
                {"log": log.model_dump(), "wf": wf.model_dump()}
            )

        return grouped_logs

    def orchestrator_status(self, response: Response):
        """Get the status of the orchestrator"""
        if self.orchestrator.state == OrchestratorState.RUNNING:
            response.status_code = status.HTTP_204_NO_CONTENT
        else:
            response.status_code = status.HTTP_410_GONE

    def pause_task(self, task_id: str):
        err_code = self.orchestrator.pause_task(task_id)

        match err_code:
            case OrchestratorErrorCodes.CONTENT_NOT_FOUND:
                return PlainTextResponse(
                    status_code=status.HTTP_404_NOT_FOUND, content="Task does not exist"
                )

            case OrchestratorErrorCodes.CANCELLED:
                return PlainTextResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content="Task pause failed",
                )

    def continue_task(self, task_id: str):
        err_code = self.orchestrator.continue_task(task_id)

        match err_code:
            case OrchestratorErrorCodes.CONTENT_NOT_FOUND:
                return PlainTextResponse(
                    status_code=status.HTTP_404_NOT_FOUND, content="Task does not exist"
                )
            case OrchestratorErrorCodes.CONTINUE_TASK_FAILED:
                return PlainTextResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content="Task continuation failed",
                )

    def get_workflows(self):
        """Get all the workflows with their steps."""
        workflows = self.orchestrator.workflows
        steps = {}

        for workflow in workflows:
            steps[workflow.name] = {
                "steps": self.orchestrator.get_steps(workflow.id),
                "args": workflow.args,
            }

        return steps

    def get_task_info(self, task_id: str):
        db = DatabaseConnector()
        db_task = DBTask.get(db, task_id)

        if db_task is None:
            return JSONResponse(
                status_code=status.HTTP_204_NO_CONTENT,
                content={"task": None, "workflow": None},
            )

        db_workflow = DBWorkflow.get_by_id(db, db_task.workflow_id)
        return {"task": db_task, "workflow": db_workflow}

    def restart_node(self, node_id: str):
        err_code = self.orchestrator.restart_node(node_id)

        match err_code:
            case OrchestratorErrorCodes.CONTENT_NOT_FOUND:
                return PlainTextResponse(
                    status_code=status.HTTP_404_NOT_FOUND, content="Node does not exist"
                )
            case OrchestratorErrorCodes.CONTINUE_TASK_FAILED:
                return PlainTextResponse(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    content="Node restart failed",
                )

    def get_node_info(self, node_id: str):
        node = self.orchestrator.get_node_by_id(node_id)
        if node is None:
            return PlainTextResponse(
                status_code=status.HTTP_404_NOT_FOUND, content="Node does not exist"
            )

        return node.serialize()

    def reload_config(self, files: list[UploadFile]):
        self.logger.info("reloading config...")

        if len(self.orchestrator.running_tasks) != 0:
            self.logger.info("some tasks are still running, cancelling config reload")
            return JSONResponse(
                status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                content={"loaded_workflows": 0, "loaded_nodes": 0},
            )

        for node in self.orchestrator.nodes:
            node.shutdown()

        if (
            err_code := self.orchestrator.load_config(files[0].file, files[1].file)
        ) != OrchestratorErrorCodes.OK:
            self.logger.error(f"Failed to load config: {err_code}")
            return JSONResponse(
                status_code=status.HTTP_201_CREATED,
                content={"loaded_workflows": -1, "loaded_nodes": -1},
            )

        self.logger.success("config reloaded")

        return JSONResponse(
            content={
                "loaded_workflows": len(self.orchestrator.workflows),
                "loaded_nodes": len(self.orchestrator.nodes),
            }
        )

    def stop(self, response: Response):
        """Stop the orchestrator."""
        response.status_code = status.HTTP_204_NO_CONTENT

        if self.orchestrator.stop() != OrchestratorErrorCodes.OK:
            response.status_code = status.HTTP_409_CONFLICT

    def full_stop(self):
        """Stop the orchestrator with the scheduler. Only happens if there is a problem with the scheduler itself."""
        self.server.should_exit = True

    def start_orchestrator(self, response: Response):
        """Start the orchestrator"""
        response.status_code = status.HTTP_204_NO_CONTENT

        if self.orchestrator.start() != OrchestratorErrorCodes.OK:
            response.status_code = status.HTTP_409_CONFLICT

    def get_running(self):
        """Retrieve all the running task."""
        running_workflows = [
            task.serialize() for _, task in self.orchestrator.running_tasks
        ]
        return running_workflows

    def lab_add_task(self, data: PostTask, response: Response):
        """Add a new task to execute."""
        if not self.orchestrator.is_running():
            self.logger.error("The orchestrator is not running")
            response.status_code = status.HTTP_418_IM_A_TEAPOT
            return {}

        wf = self.orchestrator.get_workflow_by_name(data.workflow_name)

        if wf is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return data

        # check arguments are present
        if (wf.args is not None and data.args is None) or (
            wf.args.keys() != data.args.keys()
        ):
            missing_args = wf.args.keys() - (data.args.keys() if data.args else set())
            response.status_code = status.HTTP_400_BAD_REQUEST
            return f"Missing arguments: {', '.join(missing_args)}"

        # check arguments are valid
        if data.args is not None:
            invalid_args = []
            type_validators = {
                "integer": lambda x: isinstance(x, int),
                "float": lambda x: isinstance(x, float),
                "string": lambda x: isinstance(x, str),
                "boolean": lambda x: isinstance(x, bool),
                "array": lambda x: isinstance(x, list),
            }

            for arg_name, constraints in wf.args.items():
                arg_type = constraints.get("type")
                arg_value = data.args.get(arg_name)

                if arg_type not in type_validators:
                    response.status_code = status.HTTP_400_BAD_REQUEST
                    return f"Invalid argument type: {arg_type}"
                
                if not type_validators[arg_type](arg_value):
                    invalid_args.append(f"{arg_name} is not a valid {arg_type}")
                    continue

                if arg_type in {"integer", "float"}:
                    minimum = constraints.get("minimum")
                    maximum = constraints.get("maximum")

                    if minimum is not None and arg_value < minimum:
                        invalid_args.append(f"{arg_name} is below minimum value")
                    if maximum is not None and arg_value > maximum:
                        invalid_args.append(f"{arg_name} is above maximum value")
                elif arg_type == "string":
                    max_length = constraints.get("maxLength")
                    pattern = constraints.get("pattern", ".*")

                    if max_length is not None and len(arg_value) > max_length:
                        invalid_args.append(f"{arg_name} is too long")
                    if not re.match(pattern, arg_value):
                        invalid_args.append(f"{arg_name} does not match pattern")
                elif arg_type == "array":
                    max_items = constraints.get("maxItems")

                    if max_items is not None and len(arg_value) > max_items:
                        invalid_args.append(f"{arg_name} has too many items")
            
            if invalid_args:
                response.status_code = status.HTTP_400_BAD_REQUEST
                return invalid_args

        task = self.orchestrator.add_task(wf, data.args)
        return task.serialize()
