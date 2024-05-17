<a name="readme-top"></a>
<br />
<div align="center">
  <a href="https://github.com/swisscatplus/task-scheduler">
    <img src="https://images.squarespace-cdn.com/content/v1/6012a0a1f4c67c587a8eff67/d7731755-2fa3-4548-bf1e-5a25182d67ae/Combined+Logo+CAT-ETH-EPFL+%282%29.png?format=1500w" alt="Logo" height="80">
  </a>

  <h1 align="center">Task Scheduler - Common Task Handling System</h1>

  <p align="center">
    In this repository, you will find the code common code base of most of the schedulers at SwissCAT+.
    <br />
    <a href="https://github.com/swisscatplus/task-scheduler"><strong>Explore the docs »</strong></a>
    <br />
    <br />
    <a href="https://github.com/swisscatplus/task-scheduler/issues">Report Mistake</a>
    ·
    <a href="https://github.com/swisscatplus/task-scheduler/issues">Request Feature</a>
  </p>
</div>

# Table of Contents
- [Table of Contents](#table-of-contents)
- [How to Use](#how-to-use)
- [How to Execute](#how-to-execute)

# How to Use

> [!WARNING]
> Do not use as a standalone, only as a project submodule !

First and foremost one will need to create the project that will use the Task Scheduler with the following structure:

```
my-project/
├─ src/
│  ├─ my_other_modules/
│  │  └─ __init__.py
│  │
│  ├─ orchestrator/
│  │  ├─ __init__.py
│  │  └─ core.py
│  │
│  ├─ scheduler/
│  │  ├─ __init__.py
│  │  └─ core.py
│  │
│  ├─ task_scheduler/       <------- this is the submodule which will be imported
│  │  ├─ ...
│  │  └─ ...
│  │
│  ├─ __init__.py
│  └─ run.py
│
├─ [tests/]
│
└─ exec.sh
```

Once you have such structure, cd into it and import the Task Scheduler submodule (make sure that the project is using git).

```shell
cd my-project
git submodule add git@github.com:swisscatplus/task-scheduler.git src/task_scheduler
```

Once you have the submodule, you need to install the dependencies found in `requirements.txt` and proceed with the following:

1. Implement the `BaseOrchestrator`'s abstract functions (`_load_nodes` and `_load_workflows`) in a concrete class
```python
from task_scheduler.orchestrator.base import BaseOrchestrator


class MyOrchestrator(BaseOrchestrator):
    def _load_workflows(self, path: str) -> None:
        pass

    def _load_nodes(self, path: str) -> None:
        pass
```
3. Extends the `BaseScheduler`'s constructor as such:
```python
from orchestrator.core import MyOrchestrator
from task_scheduler.base import BaseScheduler


class MyScheduler(BaseScheduler):
    def __init__(self, orchestrator: MyOrchestrator, port: int) -> None:
        super().__init__(orchestrator, port)

        self.orchestrator: MyOrchestrator = orchestrator
        self.bind_logger_name("My Scheduler")
```
3. Add the following executions scripts

```python
# run.py
from orchestrator.core import MyOrchestrator
from scheduler.core import MyScheduler
from task_scheduler.logger import setup_logger
from task_scheduler.parser import parse_args


def main():
    args = parse_args()

    setup_logger(args.logs)

    orchestrator = MyOrchestrator(
        args.path_to_nodes, args.path_to_workflows, args.verbose, args.emulate
    )
    app = MyScheduler(orchestrator, args.port)

    app.run()


if __name__ == "__main__":
    main()
```

```shell
# exec.sh
#!/usr/bin/env bash

port=$1

PYTHONPATH=./src python3 -m run -p "$port" -vel
```

# How to Execute

```shell
cd my-project
chmod u+x exec.sh
./exec.sh 3000
```

