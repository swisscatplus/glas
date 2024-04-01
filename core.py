import atexit

from fastapi import APIRouter, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from uvicorn import Config, Server

from src.orchestrator.core import OrchestratorState, WorkflowOrchestrator
from src.orchestrator.models import StatisticsModel, TaskModel
from src.scheduler.models import *


class RobotScheduler:
    def __init__(
        self,
        orchestrator: WorkflowOrchestrator,
        port: int,
    ) -> None:
        self.logger = logger.bind(app="Scheduler")

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

    def init_routes(self) -> None:
        self.init_lab_routes()
        self.init_admin_routes()
        self.init_monitoring_routes()

    def init_monitoring_routes(self) -> None:
        self.api_monitoring = APIRouter(prefix="/monitoring", tags=["Robot Scheduler Monitoring"])

        self.api_monitoring.add_api_route(
            "/diagnostics",
            self.diagnostics,
            methods=["GET"],
            responses={status.HTTP_200_OK: {"model": DiagnosticModel}},
        )
        self.api_monitoring.add_api_route(
            "/orchestrator-status",
            self.ochestrator_status,
            methods=["GET"],
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                status.HTTP_204_NO_CONTENT: {"description": "Ocestrator is online"},
                status.HTTP_410_GONE: {"description": "Orchestrator is offline"},
            },
        )
        self.api_monitoring.add_api_route(
            "/statistics",
            self.get_statistics,
            methods=["GET"],
            responses={
                status.HTTP_200_OK: {"description": "Statistics about the whole system", "model": StatisticsModel}
            },
        )
        self.api_monitoring.add_api_route("/statistics/node/{node_id}", self.get_node_statistics, methods=["GET"])
        self.api_monitoring.add_api_route(
            "/running",
            self.get_running,
            methods=["GET"],
            responses={status.HTTP_200_OK: {"model": list[TaskModel]}},
        )

        self.api.include_router(self.api_monitoring)

    def init_admin_routes(self) -> None:
        """TODO Those routes NEED to be account/key/password protected !!"""
        self.admin_router = APIRouter(prefix="/admin", tags=["Robot Scheduler Administration"])

        self.admin_router.add_api_route(
            "/start",
            self.start_orchestrator,
            methods=["POST"],
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                status.HTTP_204_NO_CONTENT: {"description": "The orchestrator successfully started"},
                status.HTTP_409_CONFLICT: {"description": "The orchestrator is already running"},
            },
        )
        self.admin_router.add_api_route(
            "/stop",
            self.stop,
            methods=["POST"],
            status_code=status.HTTP_204_NO_CONTENT,
            responses={
                status.HTTP_204_NO_CONTENT: {"description": "The orchestrator successfully stopped."},
                status.HTTP_409_CONFLICT: {"description": "The orchestrator is already stopped."},
            },
        )
        self.admin_router.add_api_route(
            "/full-stop",
            self.full_stop,
            methods=["POST"],
            status_code=status.HTTP_204_NO_CONTENT,
            responses={status.HTTP_204_NO_CONTENT: {"description": "Everything stopped successfully."}},
        )

        self.api.include_router(self.admin_router)

    def init_lab_routes(self) -> None:
        self.lab_router = APIRouter(prefix="/lab", tags=["Lab Scheduler"])

        self.lab_router.add_api_route("/add", self.lab_add_workflow, methods=["POST"])

        self.api.include_router(self.lab_router)

    def run(self) -> None:
        self.logger.info(f"started on {self.config.host}:{self.config.port}")
        self.orchestrator.start()
        self.server.run()  # need to run as last

    def diagnostics(self):
        """Get some information about the state of the scheduler and orchestrator."""
        nodes = [node.serialize() for node in self.orchestrator.get_all_nodes()]
        return DiagnosticModel(nodes=nodes)

    def get_statistics(self):
        """Get the statistics about the whole system."""
        return self.orchestrator.get_statistics()

    def get_node_statistics(self, node_id: str):
        """Get the statistics for a specific node"""
        return self.orchestrator.get_node_statistic(node_id)

    def ochestrator_status(self, response: Response):
        """Get the status of the orchestrator"""
        if self.orchestrator.get_state() == OrchestratorState.RUNNING:
            response.status_code = status.HTTP_204_NO_CONTENT
        else:
            response.status_code = status.HTTP_410_GONE
        return

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
        """Retrieve all the running tasks."""
        running_workflows = [task.serialize() for _, task in self.orchestrator.running_tasks]
        return running_workflows

    def lab_add_workflow(self, data: PostWorkflow, response: Response):
        """Add a new task to execute."""
        if not self.orchestrator.is_running():
            self.logger.error("The orchestrator is not running")
            response.status_code = status.HTTP_418_IM_A_TEAPOT
            return

        for w in self.orchestrator.workflows:
            # if w.name == data.name:
            self.orchestrator.add_task(w)
        return data
