from mariadb.connectionpool import ConnectionPool

from src.orchestrator.core import WorkflowOrchestrator
from src.scheduler.core import RobotScheduler
from src.scheduler.parser import parse_args
from src.scheduler.logger import setup_logger


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
