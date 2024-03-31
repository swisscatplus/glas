from src.orchestrator.core import WorkflowOrchestrator
from src.scheduler.core import RobotScheduler
from src.scheduler.logger import setup_logger
from src.scheduler.parser import parse_args


def main():
    args = parse_args()

    setup_logger(args.logs)

    wm = WorkflowOrchestrator(
        args.path_to_nodes, args.path_to_workflows, args.verbose, args.emulate
    )
    app = RobotScheduler(wm, args.port)
    app.run()


if __name__ == "__main__":
    main()
