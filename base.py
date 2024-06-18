"""
This module contains the base scheduler to be used to extend the scheduling behavior wanted by your laboratory.
"""
import hashlib
import hmac
import os
from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Request, Response, status, UploadFile
from fastapi.responses import JSONResponse, PlainTextResponse
from fastapi.middleware.cors import CORSMiddleware
from uvicorn import Config, Server

from .database import DBTask, DatabaseConnector, DBWorkflow
from .logger import LoggingManager
from .models import PatchTask, PatchNode, PostTask
from .orchestrator.base import BaseOrchestrator
from .orchestrator.enums import OrchestratorErrorCodes, OrchestratorState


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
            CORSMiddleware,
            allow_origins=["*"],
            allow_credentials=True,
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.api.middleware("http")(self._hmac_middleware)

        self.logger = LoggingManager.get_logger("glas", app="GLAS")
        self.orchestrator = orchestrator

        self.config = Config(self.api, host="0.0.0.0", port=port, log_level="warning")
        self.server = Server(config=self.config)
        self._secret = os.getenv("SECRET").encode("utf-8")

        self.task_router = APIRouter(prefix="/task", tags=["GLAS Tasks"])
        self.orchestrator_router = APIRouter(prefix="/orchestrator", tags=["GLAS Orchestrator"])
        self.config_router = APIRouter(prefix="/config", tags=["GLAS Config"])
        self.node_router = APIRouter(prefix="/node", tags=["GLAS Node"])

        self._hmac_excluded_routes = ["/docs", "/openapi.json"]

        self.init_routes()
        self.init_extra_routes()
        self.include_routers()

    def bind_logger_name(self, logger_name: str):
        self.logger = LoggingManager.get_logger("scheduler", app=logger_name)

    def init_routes(self) -> None:
        self.init_orchestrator_routes()
        self.init_task_routes()
        self._extends_orchestrator_routes()
        self._extends_task_routes()

        self.init_config_routes()
        self.init_node_routes()

    def include_routers(self) -> None:
        self.api.include_router(self.task_router)
        self.api.include_router(self.orchestrator_router)
        self.api.include_router(self.config_router)
        self.api.include_router(self.node_router)

    def init_extra_routes(self) -> None:
        pass

    def _extends_orchestrator_routes(self) -> None:
        pass

    def _extends_task_routes(self) -> None:
        pass

    def init_config_routes(self) -> None:
        self.config_router.add_api_route("/reload", self.reload_config, methods=["PATCH"])

    def init_task_routes(self) -> None:
        self.task_router.add_api_route("/", self.lab_add_task, methods=["POST"])
        self.task_router.add_api_route("/{task_id}", self.get_task_info, methods=["GET"])
        self.task_router.add_api_route("/continue", self.continue_task, methods=["PATCH"])
        self.task_router.add_api_route("/running", self.get_running, methods=["GET"])

    def init_node_routes(self) -> None:
        self.node_router.add_api_route("/restart/{node_id}", self.restart_node, methods=["PATCH"])

    def init_orchestrator_routes(self) -> None:
        self.orchestrator_router.add_api_route(
            "/start",
            self.start_orchestrator,
            methods=["POST"],
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                status.HTTP_204_NO_CONTENT: {"description": "The orchestrator successfully started"},
                status.HTTP_409_CONFLICT: {"description": "The orchestrator is already running"},
            },
        )
        self.orchestrator_router.add_api_route(
            "/stop",
            self.stop,
            methods=["DELETE"],
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                status.HTTP_204_NO_CONTENT: {"description": "The orchestrator successfully stopped."},
                status.HTTP_409_CONFLICT: {"description": "The orchestrator is already stopped."},
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

    def _hmac_generate_signature(self, path: str, body: bytes) -> str:
        message = path.encode("utf-8") + body
        return hmac.new(self._secret, message, hashlib.sha256).hexdigest()

    def hmac_exclude_route(self, path: str):
        self._hmac_excluded_routes.append(path)

    async def _hmac_middleware(self, request: Request, call_next) -> Response:
        if request.url.path in self._hmac_excluded_routes:
            return await call_next(request)

        signature = request.headers.get("X-Signature")
        body = await request.body() if "multipart/form-data" not in request.headers.get("Content-Type") else b""
        path = request.url.path
        expected_signature = self._hmac_generate_signature(path, body)

        if not signature or expected_signature != signature:
            self.logger.warning(f"Unauthorized access to {path} form {request.client.host}:{request.client.port}")
            return JSONResponse(
                status_code=status.HTTP_401_UNAUTHORIZED,
                content={"detail": "Unauthorized access"}
            )

        response = await call_next(request)
        return response

    def run(self) -> None:
        self.logger.info(f"started on {self.config.host}:{self.config.port}")

        if (err_code := self.orchestrator.start()) != OrchestratorErrorCodes.OK:
            self.logger.critical(f"Failed to start orchestrator: {err_code}")
            return

        self.server.run()  # need to run as last

    def orchestrator_status(self, response: Response):
        """Get the status of the orchestrator"""
        if self.orchestrator.state == OrchestratorState.RUNNING:
            response.status_code = status.HTTP_204_NO_CONTENT
        else:
            response.status_code = status.HTTP_410_GONE

    def continue_task(self, data: PatchTask):
        err_code = self.orchestrator.continue_task(data.task_id)

        match err_code:
            case OrchestratorErrorCodes.CONTENT_NOT_FOUND:
                return PlainTextResponse(status_code=status.HTTP_404_NOT_FOUND, content="Task does not exist")
            case OrchestratorErrorCodes.CONTINUE_TASK_FAILED:
                return PlainTextResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                         content="Task continuation failed")

    def get_task_info(self, task_id: str):
        db = DatabaseConnector()
        db_task = DBTask.get(db, task_id)

        if db_task is None:
            return JSONResponse(status_code=status.HTTP_204_NO_CONTENT, content={"task": None, "workflow": None})

        db_workflow = DBWorkflow.get_by_id(db, db_task.workflow_id)
        return {"task": db_task, "workflow": db_workflow}

    def restart_node(self, node_id: str):
        err_code = self.orchestrator.restart_node(node_id)

        match err_code:
            case OrchestratorErrorCodes.CONTENT_NOT_FOUND:
                return PlainTextResponse(status_code=status.HTTP_404_NOT_FOUND, content="Node does not exist")
            case OrchestratorErrorCodes.CONTINUE_TASK_FAILED:
                return PlainTextResponse(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                         content="Node restart failed")

    def reload_config(self, files: list[UploadFile]):
        self.logger.info("reloading config...")

        if len(self.orchestrator.running_tasks) != 0:
            self.logger.info("some tasks are still running, cancelling config reload")
            return JSONResponse(status_code=status.HTTP_428_PRECONDITION_REQUIRED,
                                content={"loaded_workflows": 0, "loaded_nodes": 0})

        for node in self.orchestrator.nodes:
            node.shutdown()

        if (err_code := self.orchestrator.load_config(files[0].file, files[1].file)) != OrchestratorErrorCodes.OK:
            self.logger.error(f"Failed to load config: {err_code}")
            return JSONResponse(status_code=status.HTTP_201_CREATED,
                                content={"loaded_workflows": -1, "loaded_nodes": -1})
        else:
            self.logger.success("config reloaded")

        return JSONResponse(content={"loaded_workflows": len(self.orchestrator.workflows),
                                     "loaded_nodes": len(self.orchestrator.nodes)})

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
        running_workflows = [task.serialize() for _, task in self.orchestrator.running_tasks]
        return JSONResponse(content=running_workflows)

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

        task = self.orchestrator.add_task(wf, data.args)
        return task.serialize()
