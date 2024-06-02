from contextlib import asynccontextmanager

from fastapi import APIRouter, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from uvicorn import Config, Server

from .logger import LoggingManager
from .models import *
from .orchestrator.base import BaseOrchestrator
from .orchestrator.enums import OrchestratorErrorCodes


class BaseScheduler:
    def __init__(self, orchestrator: BaseOrchestrator, port: int) -> None:
        self.logger = None

        @asynccontextmanager
        async def lifespan(app: FastAPI):
            yield
            self.orchestrator.stop()

        self.api = FastAPI(lifespan=lifespan)
        self.api.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.orchestrator = orchestrator

        self.config = Config(self.api, host="0.0.0.0", port=port, log_level="warning")
        self.server = Server(config=self.config)

        self.admin_router = APIRouter(prefix="/admin", tags=["Robot Scheduler Administration"])
        self.lab_router = APIRouter(prefix="/lab", tags=["Lab Scheduler"])

        self.init_routes()
        self.init_extra_routes()
        self.include_routers()

    def bind_logger_name(self, logger_name: str):
        self.logger = LoggingManager.get_logger("scheduler", app=logger_name)

    def init_routes(self) -> None:
        self.init_lab_routes()
        self.init_admin_routes()
        self._extends_lab_routes()
        self._extends_admin_routes()

    def include_routers(self) -> None:
        self.api.include_router(self.admin_router)
        self.api.include_router(self.lab_router)

    def init_extra_routes(self) -> None:
        pass

    def _extends_lab_routes(self) -> None:
        pass

    def _extends_admin_routes(self) -> None:
        pass

    def init_admin_routes(self) -> None:
        """TODO Those routes NEED to be account/key/password protected !"""
        self.admin_router.add_api_route(
            "/orchestrator/start",
            self.start_orchestrator,
            methods=["POST"],
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                status.HTTP_204_NO_CONTENT: {"description": "The orchestrator successfully started"},
                status.HTTP_409_CONFLICT: {"description": "The orchestrator is already running"},
            },
        )
        self.admin_router.add_api_route(
            "/orchestrator/stop",
            self.stop,
            methods=["DELETE"],
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                status.HTTP_204_NO_CONTENT: {"description": "The orchestrator successfully stopped."},
                status.HTTP_409_CONFLICT: {"description": "The orchestrator is already stopped."},
            },
        )
        self.admin_router.add_api_route(
            "/stop",
            self.full_stop,
            methods=["DELETE"],
            status_code=status.HTTP_204_NO_CONTENT,
            responses={status.HTTP_204_NO_CONTENT: {"description": "Everything stopped successfully."}},
        )
        self.admin_router.add_api_route(
            "/reload-config",
            self.reload_config,
            methods=["PATCH"],
        )

    def init_lab_routes(self) -> None:
        self.lab_router.add_api_route("/add", self.lab_add_task, methods=["POST"])

    def run(self) -> None:
        self.logger.info(f"started on {self.config.host}:{self.config.port}")

        if (err_code := self.orchestrator.start()) != OrchestratorErrorCodes.OK:
            self.logger.critical(f"Failed to start orchestrator: {err_code}")
            return

        self.server.run()  # need to run as last

    def reload_config(self, data: PatchConfig, response: Response):
        self.logger.info("reloading config...")

        if len(self.orchestrator.get_running_tasks()) != 0:
            self.logger.info("some tasks are still running, cancelling config reload")
            response.status_code = status.HTTP_428_PRECONDITION_REQUIRED
            return

        if (err_code := self.orchestrator.load_config(data.nodes_config, data.workflows_config)) != OrchestratorErrorCodes.OK:
            self.logger.error(f"Failed to load config: {err_code}")
            response.status_code = status.HTTP_201_CREATED
        else:
            self.logger.success(f"config reloaded")

        return {"loaded_workflows": len(self.orchestrator.workflows), "loaded_nodes": len(self.orchestrator.nodes)}

    def stop(self, response: Response):
        """Stop the orchestrator."""
        response.status_code = status.HTTP_204_NO_CONTENT

        if self.orchestrator.stop() != OrchestratorErrorCodes.OK:
            response.status_code = status.HTTP_409_CONFLICT
        return

    def full_stop(self):
        """Stop the orchestrator with the scheduler. Only happens if there is a problem with the scheduler itself."""
        self.server.should_exit = True
        return

    def start_orchestrator(self, response: Response):
        """Start the orchestrator"""
        response.status_code = status.HTTP_204_NO_CONTENT

        if self.orchestrator.start() != OrchestratorErrorCodes.OK:
            response.status_code = status.HTTP_409_CONFLICT
        return

    def get_running(self):
        """Retrieve all the running task."""
        running_workflows = [task.serialize() for _, task in self.orchestrator.get_running_tasks()]
        return running_workflows

    def lab_add_task(self, data: PostWorkflow, response: Response):
        """Add a new task to execute."""
        if not self.orchestrator.is_running():
            self.logger.error("The orchestrator is not running")
            response.status_code = status.HTTP_418_IM_A_TEAPOT
            return

        wf = self.orchestrator.get_workflow_by_name(data.name)

        if wf is None:
            response.status_code = status.HTTP_404_NOT_FOUND
            return data

        self.orchestrator.add_task(wf, data.args)
        return data
