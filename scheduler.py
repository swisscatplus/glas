import random
import sqlite3

from fastapi import APIRouter, Depends, FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger
from mariadb.connectionpool import ConnectionPool
from pydantic import BaseModel
from uvicorn import Config, Server

from src.orchestrator.orchestrator import WorkflowOrchestrator


class Msg(BaseModel):
    data: str
    error: int


class RobotScheduler:
    def __init__(
        self,
        orchestrator: WorkflowOrchestrator,
        port: int,
        db_pool: ConnectionPool,
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
        self.db_pool = db_pool
        self.db_conn = self.db_pool.get_connection()
        self.db_conn.autocommit = True
        self.db_cursor = self.db_conn.cursor()

        self.config = Config(self.api, host="0.0.0.0", port=port, log_level="error")
        self.server = Server(config=self.config)

        self.lab_router = APIRouter(prefix="/lab", tags=["Lab Scheduler"])

        self.init_routes()
        self.init_lab_routes()

        self.api.add_websocket_route("/ws", self.websocket_endpoint)

        self.api.include_router(self.lab_router)

    def init_routes(self) -> None:
        self.api.add_api_route("/", self.root, methods=["GET"])
        self.api.add_api_route("/stop", self.stop, methods=["GET"])
        self.api.add_api_route("/add", self.add, methods=["GET"])
        self.api.add_api_route("/running", self.get_running, methods=["GET"])

    def init_lab_routes(self) -> None:
        self.lab_router.add_api_route("/add", self.lab_add_workflow, methods=["POST"])

    async def websocket_endpoint(self, websocket: WebSocket):
        await websocket.accept()
        self.orchestrator.add_observer(websocket)
        self.logger.info(
            f"connected observer {websocket.client.host}:{websocket.client.port}"
        )

        try:
            while True:
                msg = await websocket.receive_text()

                if msg.lower() == "close":
                    self.orchestrator.remove_observer(websocket)
        except WebSocketDisconnect:
            self.logger.info(
                f"disconnected observer {websocket.client.host}:{websocket.client.port}"
            )
            self.orchestrator.remove_observer(websocket)

    def run(self) -> None:
        self.logger.info(f"started on {self.config.host}:{self.config.port}")
        self.orchestrator.run()
        self.server.run()  # need to run as last

    def root(self):
        msg = Msg(data="AWDAWD", error=200)
        return {"msg": msg}

    def stop(self):
        self.orchestrator.stop()
        self.server.should_exit = True
        return {"terminated": True}

    def add(self):
        w = random.choice(self.orchestrator.workflows)
        # self.orchestrator.add_workflow(w)
        self.orchestrator.add_workflow(self.orchestrator.workflows[0])
        self.orchestrator.add_workflow(self.orchestrator.workflows[12])
        self.orchestrator.add_workflow(self.orchestrator.workflows[5])
        self.orchestrator.add_workflow(self.orchestrator.workflows[8])
        self.orchestrator.add_workflow(self.orchestrator.workflows[10])
        self.orchestrator.add_workflow(self.orchestrator.workflows[2])
        self.orchestrator.add_workflow(self.orchestrator.workflows[9])
        self.orchestrator.add_workflow(self.orchestrator.workflows[1])
        self.orchestrator.add_workflow(self.orchestrator.workflows[11])
        self.orchestrator.add_workflow(self.orchestrator.workflows[10])
        # self.orchestrator.add_workflow(random.choice(self.orchestrator.workflows))
        # self.orchestrator.add_workflow(random.choice(self.orchestrator.workflows))
        # self.orchestrator.add_workflow(random.choice(self.orchestrator.workflows))
        # self.orchestrator.add_workflow(random.choice(self.orchestrator.workflows))
        return {"data": self.orchestrator.nodes[0]}

    def get_running(self):
        self.db_cursor.execute(
            "SELECT * FROM running_workflows JOIN workflows ON running_workflows.workflow_id = workflows.id"
        )
        return {"running": self.db_cursor.fetchall()}

    def lab_add_workflow(self):
        return {"data": "AWDWAD"}
