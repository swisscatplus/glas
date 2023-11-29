import argparse
import sys

from loguru import logger
from mariadb.connectionpool import ConnectionPool

from src.orchestrator.orchestrator import WorkflowOrchestrator
from src.scheduler.core import RobotScheduler


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="RobotScheduler",
        description="Scheduler to automate the lab's worlkflows",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )

    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="Port of the scheduler to communicate with",
    )
    parser.add_argument(
        "-n",
        "--nodes",
        type=str,
        default="./config/nodes.json",
        help="File path of the node descriptions",
        dest="path_to_nodes",
    )
    parser.add_argument(
        "-w",
        "--workflows",
        type=str,
        default="./config/workflows.json",
        help="File path of the workflow descriptions",
        dest="path_to_workflows",
    )
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose mode")
    parser.add_argument(
        "-l", "--logs", action="store_true", help="Store the logs in a file as well"
    )

    return parser.parse_args()


def setup_logger(save_logs: bool = True) -> None:
    fmt = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>[{extra[app]}] {message}</level>"

    logger.remove(0)
    logger.add(
        sys.stdout,
        level="TRACE",
        format=fmt,
    )

    if save_logs:
        logger.add("scheduler.log", format=fmt, rotation="10 MB")


def main():
    args = parse_args()

    setup_logger(args.logs)

    db_pool = ConnectionPool(
        pool_name="main_pool",
        user="epfl",
        password="Super2019",
        host="localhost",
        database="epfl",
        pool_size=20,
    )

    wm = WorkflowOrchestrator(
        args.path_to_nodes, args.path_to_workflows, db_pool, args.verbose
    )

    app = RobotScheduler(wm, args.port, db_pool)
    app.run()


if __name__ == "__main__":
    main()
