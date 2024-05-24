import atexit

from fastapi import APIRouter, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from uvicorn import Config, Server

from .orchestrator.base import BaseOrchestrator
from .models import *


class BaseScheduler:
    def __init__(self, orchestrator: BaseOrchestrator, port: int) -> None:
        self.logger = None
        self.api = FastAPI()
        self.api.add_middleware(
            CORSMiddleware,
            allow_origins=["http://localhost:5173"],
            allow_methods=["*"],
            allow_headers=["*"],
        )
        self.orchestrator = orchestrator

        self.config = Config(self.api, host="0.0.0.0", port=port, log_level="warning")
        self.server = Server(config=self.config)

        atexit.register(lambda: self.orchestrator.stop())

        self.init_routes()

    def bind_logger_name(self, logger_name: str):
        self.logger = logger.bind(app=logger_name)

    def init_routes(self) -> None:
        self.init_lab_routes()
        self.init_admin_routes()

    def init_admin_routes(self) -> None:
        """TODO Those routes NEED to be account/key/password protected !"""
        admin_router = APIRouter(prefix="/admin", tags=["Robot Scheduler Administration"])

        admin_router.add_api_route(
            "/start",
            self.start_orchestrator,
            methods=["POST"],
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                status.HTTP_204_NO_CONTENT: {"description": "The orchestrator successfully started"},
                status.HTTP_409_CONFLICT: {"description": "The orchestrator is already running"},
            },
        )
        admin_router.add_api_route(
            "/stop",
            self.stop,
            methods=["POST"],
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                status.HTTP_204_NO_CONTENT: {"description": "The orchestrator successfully stopped."},
                status.HTTP_409_CONFLICT: {"description": "The orchestrator is already stopped."},
            },
        )
        admin_router.add_api_route(
            "/full-stop",
            self.full_stop,
            methods=["POST"],
            status_code=status.HTTP_204_NO_CONTENT,
            responses={status.HTTP_204_NO_CONTENT: {"description": "Everything stopped successfully."}},
        )

        self.api.include_router(admin_router)

    def init_lab_routes(self) -> None:
        lab_router = APIRouter(prefix="/lab", tags=["Lab Scheduler"])

        lab_router.add_api_route("/add", self.lab_add_task, methods=["POST"])

        self.api.include_router(lab_router)

    def run(self) -> None:
        self.logger.info(f"started on {self.config.host}:{self.config.port}")
        self.orchestrator.start()
        self.server.run()  # need to run as last

    def stop(self, response: Response):
        """Stop the orchestrator."""
        response.status_code = status.HTTP_204_NO_CONTENT

        if self.orchestrator.stop() != 0:
            response.status_code = status.HTTP_409_CONFLICT
        return

    def full_stop(self):
        """Stop the orchestrator with the scheduler. Only happens if there is a problem with the scheduler itself."""
        self.orchestrator.stop()
        self.server.should_exit = True
        return

    def start_orchestrator(self, response: Response):
        """Start the orchestrator"""
        response.status_code = status.HTTP_204_NO_CONTENT

        if self.orchestrator.start() != 0:
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
