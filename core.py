import atexit
from functools import wraps

from fastapi import APIRouter, FastAPI, Response, status
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel
from uvicorn import Config, Server

from src.orchestrator.core import WorkflowOrchestrator
from src.orchestrator.task import Task


class Msg(BaseModel):
    data: str
    error: int


class WorkflowAdd(BaseModel):
    name: str


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

        atexit.register(self.stop)

        self.init_routes()

    def init_routes(self) -> None:
        self.init_lab_routes()
        self.init_admin_routes()
        self.init_monitoring_routes()

    def init_monitoring_routes(self) -> None:
        self.api_monitoring = APIRouter(prefix="/monitoring", tags=["Robot Scheduler Monitoring"])

        self.api_monitoring.add_api_route("/diagnostics", self.diagnostics, methods=["GET"])
        self.api_monitoring.add_api_route("/running", self.get_running, methods=["GET"])

        self.api.include_router(self.api_monitoring)

    def init_admin_routes(self) -> None:
        """TODO Those routes NEED to be account/key/password protected !!"""
        self.admin_router = APIRouter(prefix="/admin", tags=["Robot Scheduler Administration"])

        self.admin_router.add_api_route("/start", self.start_orchestrator, methods=["GET"])
        self.admin_router.add_api_route("/stop", self.stop, methods=["GET"])
        self.admin_router.add_api_route("/full-stop", self.full_stop, methods=["GET"])

        self.api.include_router(self.admin_router)

    def init_lab_routes(self) -> None:
        self.lab_router = APIRouter(prefix="/lab", tags=["Lab Scheduler"])

        self.lab_router.add_api_route("/add", self.lab_add_workflow, methods=["POST"])

        self.api.include_router(self.lab_router)

    def decorator_with_orchestrator(func):
        @wraps(func)
        def wrapper(self, *args, **kwrgs):
            if not self.orchestrator.is_running():
                self.logger.error("The orchestrator is not running")
                return

            result = func(self, *args, **kwrgs)
            return result

        return wrapper

    def run(self) -> None:
        self.logger.info(f"started on {self.config.host}:{self.config.port}")
        self.orchestrator.start()
        self.server.run()  # need to run as last

    def diagnostics(self, response: Response):
        # response.status_code = status.HTTP_202_ACCEPTED
        return {"orchestrator": self.orchestrator.get_state()}

    def stop(self):
        """Stop the entire scheduler due to some error of some kind"""
        self.orchestrator.stop()
        return {"orchestrator": self.orchestrator.get_state()}

    def full_stop(self):
        self.stop()
        self.server.should_exit = True
        return {"fullStop": True}

    def start_orchestrator(self):
        self.orchestrator.start()
        return {"orchestrator": self.orchestrator.get_state()}

    def get_running(self):
        # TODO remove finished tasks from the list
        running_workflows = [task.serialize() for _, task in self.orchestrator.running_tasks]
        return running_workflows

    @decorator_with_orchestrator
    def lab_add_workflow(self, workflow: WorkflowAdd):
        for w in self.orchestrator.workflows:
            # if w.name == workflow.name:
            self.orchestrator.add_task(Task(w, True))
        return workflow
