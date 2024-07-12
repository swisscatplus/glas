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
├─ config/
│  ├─ nodes.json
│  └─ config.json
│ 
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
│  ├─ task_scheduler/       <------- this is the submodule which will be imported and shoule not be touched
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

Once you have such structure, cd into it and import the Task Scheduler submodule (make sure that the project is using
git).

```shell
cd my-project
git submodule add git@github.com:swisscatplus/task-scheduler.git src/task_scheduler
```

Once you have the submodule, you need to install the dependencies found in `requirements.txt` and proceed with the
following:

1. Create a `.env` file with this content:
```env
DATABASE_HOST=<database-host>
DATABASE_USER=<database-user>
DATABASE_PASSWORD=<database-pwd>
DATABASE_PORT=<database-port>
DATABASE_NAME=<database-name>
```

2. Create the files `config/nodes.json` and `config/workflows.json` with, for example, the following:
> config/nodes.json
```json
{
  "nodes": [
    {
      "id": "node-1",
      "name": "Node one",
      "type": "FirstNode"
    },
    {
      "id": "node-2",
      "name": "Node two",
      "type": "SecondNode"
    }
  ]
}
```

> config/workflows.json
```json
{
  "workflows": [
    {
      "name": "my-workflow",
      "steps": [
        "node-1",
        "node-2"
      ]
    }
  ]
}
```

3. Create the nodes' implementations in those files for example:
> src/nodes/firstnode.py
```python
from typing import Self

from task_scheduler.nodes.base import BaseNode


class FirstNode(BaseNode):
    def _execute(self, src: Self, dst: Self, task_id: str, args: dict[str, any] = None) -> tuple[
        int, str | None, str | None]:
        self.logger.info("Executing first node")
        return 0, None, None
```
> src/nodes/secondnode.py

```python
from typing import Self

from task_scheduler.nodes.base import BaseNode


class SecondNode(BaseNode):
    def _execute(self, src: Self, dst: Self, task_id: str, args: dict[str, any] = None) -> tuple[
        int, str | None, str | None]:
        self.logger.info("Executing second node")
        return 0, None, None
```

4. Implement the `BaseOrchestrator`'s abstract functions (`_load_nodes` and `_load_workflows`) in a concrete class

```python
import json
from typing import Optional

from nodes.firstnode import FirstNode
from nodes.secondnode import SecondNode
from task_scheduler.nodes.base import BaseNode
from task_scheduler.orchestrator.base import BaseOrchestrator
from task_scheduler.orchestrator.enums import OrchestratorErrorCodes
from task_scheduler.workflow.core import Workflow


class MyOrchestrator(BaseOrchestrator):
    """An example of implementation can be found in the Omnifire or Robot Scheduler repository"""

    def _find_node_by_id(self, _id: str) -> Optional[BaseNode]:
        for node in self._nodes:
            if node.id == _id:
                return node
        return None

    def _load_workflows(self, path: str) -> OrchestratorErrorCodes:
        """Populate the list of workflows: `self.workflows` by parsing the workflow config file"""

        # WARNING: NO ERROR HANDLING IS DONE IN THIS EXAMPLE
        data = json.load(open(path, "r"))
        workflows = data.get("workflows", [])

        for i, workflow in enumerate(workflows):
            name = workflow["name"]
            steps = [self._find_node_by_id(node_id) for node_id in workflows["steps"]]

            if None in steps:
                self.logger.error(f"Skipping workflow, some node weren't found")
                continue

            self._workflows.append(Workflow(i, name, steps))

        return OrchestratorErrorCodes.OK

    def _load_nodes(self, path: str) -> OrchestratorErrorCodes:
        """Populate the list of nodes: `self.nodes` by parsing the node config file"""

        # WARNING: NO ERROR HANDLING IS DONE IN THIS EXAMPLE
        data = json.load(open(path, "r"))
        nodes = data.get("nodes", [])

        for node in nodes:
            _id = node["id"]
            name = node["name"]
            _type = node["type"]

            match _type:
                case "FirstNode":
                    self._nodes.append(FirstNode(_id, name))
                case "SecondNode":
                    self._nodes.append(SecondNode(_id, name))
        return OrchestratorErrorCodes.OK
```

5. Extends the `BaseScheduler`'s constructor as such:

```python
from fastapi import APIRouter

from orchestrator.core import MyOrchestrator
from task_scheduler.base import BaseScheduler


class MyScheduler(BaseScheduler):
    def __init__(self, orchestrator: MyOrchestrator, port: int) -> None:
        super().__init__(orchestrator, port)

        self.orchestrator: MyOrchestrator = orchestrator
        self.bind_logger_name("My Scheduler")

    def init_extra_routes(self) -> None:
        """
        This function is empty defined in the BaseScheduler.
        Add any additional router you want to define here.
        """
        self.init_my_extra_personalized_routes()

    def init_my_extra_personalized_routes(self) -> None:
        my_personalized_router = APIRouter(prefix="/my-prefix", tags=["My Personalized tags"])

        my_personalized_router.add_api_route("/hello", self.hello_route_handler)
        self.api.include_router(my_personalized_router)

    def hello_route_handler(self):
        return {"message": "Hello World!"}
```

6. Add the following executions scripts

```python
# run.py
from dotenv import load_dotenv

from orchestrator.core import MyOrchestrator
from scheduler.core import MyScheduler
from task_scheduler.logger import LoggingManager
from task_scheduler.parser import parse_args


def main():
    args = parse_args()

    load_dotenv()

    LoggingManager(args.logs, args.debug)

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

PYTHONPATH=./src python3 -m run -p "$port" -vl
```

# Node Implementation

As you may already know, a task is the execution of a workflow, which is defined by a predefined sequence of steps.
Those steps are represented by nodes in the codebase. Every single node can have a fully customized execution code, use
any kind of protocol, as long as it is writable in Python.

The nodes files can be created in a new folder called `nodes` in the source folder for a better file structure.

# How to Execute

> For more information about the execution, please read the help menu `python3 -m run -h`

## Linux

```shell
cd my-project
chmod u+x exec.sh
./exec.sh 3000
```

## Windows

```shell
cd Myproject\src
python3 -m run -p 3000 -vl
```
