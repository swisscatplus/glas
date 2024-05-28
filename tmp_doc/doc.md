Documentation
1. Requirements
2. Installation
3. Task Scheduler
3.1 scheduler
3.2 orchestrator
3.3 nodes
3.4 workflows
3.5 tasks
3.6 database
4. Extending the Task Scheduler
4.1 [...]
5. Running an extended Task Scheduler
6. Real-time visualizer


# 1. Requirements
## 1.1 Software
The following must be installed before proceeding with the installation

- [Python 3.11](https://www.python.org/downloads/)
- [Docker Engine](https://docs.docker.com/engine/install/debian/)
- [Docker compose](https://docs.docker.com/compose/install/)
- [Git](https://git-scm.com/downloads)

## 1.2 IDE
We recommend using vscode for this project, or PyCharm.

## 1.3 Git
A working Git environnement is necessary, and it must have access to the repository.

# 2. Installation

This chapter explains how to create a repository and include the task scheduler inside. This step is crutial so read carefully.

## 2.1 Creating a Git Repository for the project

First, create an empty repository wherever you want.
Clone it and inside, create folders and files following this example :

```
<my-project>/
├─ src/
│  ├─ <my_other_modules>/      <----- Can be ignored for now.
│  │  └─ __init__.py
│  │
│  ├─ nodes/
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
│  ├─ __init__.py
│  └─ run.py
│
├─ [tests/]       <------ optional
│
└─ exec.sh
```

You can keep all files empty for now.

Once done, go into the \<my-project> folder and execute the following command :

```bash
cd <my-project>
git submodule add git@github.com:swisscatplus/task-scheduler.git src/task_scheduler
```

This will import the task-scheduler as a submodule in the path `<my-project>/src/task-scheduler`.

To update the submodule, run the command :
```bash
git submodule update
```

## 2.2 Preparing the Python environment

The Python executable on Linux-based OS is `python3`, but on Windows it is `py`. If you are on Windows, replace the executable accordingly on the following commands.

For a better experience, create a Python virtual environment :

```bash
../<my-project>$ python3 -m venv .venv
```

Run the venv :
```bash
../<my-project>$ source .venv/bin/activate
```

Install the required packages :
```bash
(.venv) ../<my-project>$ pip install ./requirements.txt
```