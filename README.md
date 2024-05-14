# Task Scheduler

> [!WARNING]
> Do not use as a standalone, only as a project submodule !

# How To
```
cd <your-project>
git submodule add git@github.com:swisscatplus/task-scheduler.git <path>/task_scheduler
```

Once you have the submodule, you need to implement some things:

1. Implement the `Orchestrator`'s abstract functions
2. Extends if needed the scheduler
3. Update the following script to you preferences and use it as the entrypoint

```python
# run.py
from <my_orchestrator_impl> import MyOrchestrator
from <my_extended_scheduler> import MyScheduler
from task_scheduler.logger import setup_logger
from task_scheduler.parser import parse_args


def main():
    args = parse_args()

    setup_logger(args.logs)

    wm = MyOrchestrator(
        args.path_to_nodes, args.path_to_workflows, args.verbose, args.emulate
    )
    app = MyScheduler(wm, args.port)
    app.run()


if __name__ == "__main__":
    main()
```

And also, tu run the project, create the following script and run it instead of using the python command:

```shell
# exec.sh
#!/usr/bin/env bash

port=$1

PYTHONPATH=./src python3 -m run -p "$port" -vel
```

Finally, you should have a project structure like:

```
project/
├─ src/
│  ├─ task_scheduler/
│  │  ├─ __init__.py
│  ├─ my_other_modules/
│  │  ├─ __init__.py
│  ├─ __init__.py
│  ├─ run.py
│  ├─ my_scheduler.py
├─ exec.sh
```