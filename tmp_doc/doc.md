Documentation
1. Introduction
2. Requirements
3. Installation
4. Task Scheduler
4.1 scheduler
4.2 orchestrator
4.3 nodes
4.4 workflows
4.5 tasks
4.6 database
5. Extending the Task Scheduler
5.1 [...]
6. Running an extended Task Scheduler
7. Real-time visualizer

# 1. Introduction

> [!WARNING]
> Do not use as a standalone, only as a project submodule !

This project is a task scheduler with no implementation whatsoever. It is aimed to be used by any kind of project necessiting such scheduling. You can easily extend this project to fit you needs and it is highly modular.

Once set up, adding a new node is simply adding a new class object and adding it in the configuration file. On startup, the configuration file is parsed and will instanciate everything for you.

This document will help you to set up your first scheduler and configure it.

# 2. Requirements
## 2.1 Software
The following must be installed before proceeding with the installation

- [Python 3.11](https://www.python.org/downloads/)
- [Docker Engine](https://docs.docker.com/engine/install/debian/)
- [Docker compose](https://docs.docker.com/compose/install/)
- [Git](https://git-scm.com/downloads)

## 2.2 IDE
We recommend using vscode for this project, or PyCharm.

## 2.3 Git
A working Git environnement is necessary, and it must have access to the repository.

# 3. Installation

This chapter explains how to create a repository and include the task scheduler inside. This step is crutial so read carefully.

## 3.1 Creating a Git Repository for the project

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
├─ compose.yaml
├─ Dockerfile
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

## 3.2 Preparing the Python environment

The Python executable on Linux-based OS is `python3`, but on Windows it is `py` or `python`. If you are on Windows, replace the executable accordingly on the following commands.

For a better experience, create a Python virtual environment :

```bash
../<my-project>$ python3 -m venv .venv
```

Run the venv :
```bash
../<my-project>$ source .venv/bin/activate # Linux
..\my-project> .venv\Scripts\activate.bat # Windows
```

Install the required packages :
```bash
(.venv) ../<my-project>$ pip install requirements.txt
```

## 3.3 Preparing the Docker environment

This project uses a dockerized database to store the state of all executions and configurations.

In the file `<my-project>/Dockerfile`, write the following :
```Dockerfile
# Use an official MySQL image as a base image
FROM mysql:latest

# Set environment variables
ENV MYSQL_ROOT_PASSWORD=Super2019
ENV MYSQL_DATABASE=epfl
ENV MYSQL_USER=epfl
ENV MYSQL_PASSWORD=Super2019
ENV TZ=Europe/Zurich

# Copy the SQL file containing your specific database model to the container
COPY ./src/task_scheduler/database/sql/schema.sql /docker-entrypoint-initdb.d/

# Expose the MySQL default port
EXPOSE 3306
```

in the file `<my-project>/compose.yaml`, write the following :
```yaml
services:
  db:
    build: .
    ports:
      - 3306:3306
  phpmyadmin:
    image: phpmyadmin
    restart: on-failure
    ports:
      - 8080:80
```

To build and run the database container, run the following command :
```shell
docker compose up -d
```