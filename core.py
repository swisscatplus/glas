import random
from functools import wraps

from fastapi import APIRouter, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from pydantic import BaseModel
from uvicorn import Config, Server

from src.orchestrator.core import WorkflowOrchestrator
from src.orchestrator.task import Task


class Msg(BaseModel):
    data: str
    error: int


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

        self.lab_router = APIRouter(prefix="/lab", tags=["Lab Scheduler"])

        self.init_routes()
        self.init_lab_routes()

        self.api.include_router(self.lab_router)

    def init_routes(self) -> None:
        self.api.add_api_route("/", self.root, methods=["GET"])
        self.api.add_api_route("/diagnostics", self.diagnostics, methods=["GET"])
        self.api.add_api_route("/stop", self.stop, methods=["GET"])
        self.api.add_api_route("/full-stop", self.full_stop, methods=["GET"])
        self.api.add_api_route("/run", self.run_orchestrator, methods=["GET"])
        self.api.add_api_route("/add", self.add, methods=["GET"])
        self.api.add_api_route("/running", self.get_running, methods=["GET"])

    def init_lab_routes(self) -> None:
        self.lab_router.add_api_route("/add", self.lab_add_workflow, methods=["POST"])

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
        self.orchestrator.run()
        self.server.run()  # need to run as last

    def diagnostics(self):
        return {"orchestrator": self.orchestrator.is_running()}

    def root(self):
        msg = Msg(data="AWDAWD", error=200)
        return {"msg": msg}

    def stop(self):
        """Stop the entire scheduler due to some error of some kind"""
        self.orchestrator.stop()
        return {"orchestrator": False}

    def full_stop(self):
        self.stop()
        self.server.should_exit = True
        return {"fullStop": True}

    def run_orchestrator(self):
        self.orchestrator.run()
        return {"orchestrator": True}

    @decorator_with_orchestrator
    def add(self):
        for w in self.orchestrator.workflows:
            self.orchestrator.add_task(Task(w, True))
        # w = random.choice()
        # self.orchestrator.add_workflow(w)
        # self.orchestrator.add_workflow(self.orchestrator.workflows[0])
        # self.orchestrator.add_workflow(self.orchestrator.workflows[12])
        # self.orchestrator.add_workflow(self.orchestrator.workflows[5])
        # self.orchestrator.add_workflow(self.orchestrator.workflows[8])
        # self.orchestrator.add_workflow(self.orchestrator.workflows[10])
        # self.orchestrator.add_workflow(self.orchestrator.workflows[2])
        # self.orchestrator.add_workflow(self.orchestrator.workflows[9])
        # self.orchestrator.add_workflow(self.orchestrator.workflows[1])
        # self.orchestrator.add_workflow(self.orchestrator.workflows[11])
        # self.orchestrator.add_workflow(self.orchestrator.workflows[10])
        # self.orchestrator.add_workflow(random.choice(self.orchestrator.workflows))
        # self.orchestrator.add_workflow(random.choice(self.orchestrator.workflows))
        # self.orchestrator.add_workflow(random.choice(self.orchestrator.workflows))
        # self.orchestrator.add_workflow(random.choice(self.orchestrator.workflows))
        return {"data": "blablabla"}

    def get_running(self):
        running_workflows = [
            {"id": uuid, "workflow": w.model_dump()}
            for uuid, w in self.orchestrator.running_tasks
        ]
        return running_workflows

    def lab_add_workflow(self):
        return {"data": "AWDWAD"}
