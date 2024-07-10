"""
This module contains all the logging configuration used throughout the project, and the execution graph functions.
The execution graph can be viewed by running this file directly with your interpreter in the folder containing the file
`task_execution_logs.csv`.
"""

from __future__ import annotations

import csv
import os
import sys
from threading import Lock
from typing import Callable, Optional

import loguru
import matplotlib
import matplotlib.pyplot as plt
from loguru import logger
from matplotlib.colors import ListedColormap

from glas.database import DatabaseConnector
from glas.database.execution_logs import DBExecutionLogs
from glas.database.logs import DBLogs

COLLECTION_FILE = "./task_execution_logs.csv"


def _visualize():
    # pylint: disable=R0914
    font = {'weight': 'semibold',
            'size': 16}

    matplotlib.rc('font', **font)

    data = []
    with open(COLLECTION_FILE, "r", newline="", encoding="utf-8") as file:
        csv_reader = csv.reader(file)
        for row in csv_reader:
            data.append(row)

    # Organize data into a dictionary to hold actions for each test
    test_actions = {}
    u_nodes = []
    latest = 0
    earliest = float('inf')

    for parts in data:
        test_name = parts[0] + " " + parts[1]
        action = parts[2]
        start_time = float(parts[3])
        end_time = float(parts[4])

        latest = max(latest, end_time)
        earliest = min(earliest, start_time)

        if test_name not in test_actions:
            test_actions[test_name] = []

        u_nodes.append(action)
        test_actions[test_name].append((action, start_time, end_time))

    # Calculate the time range
    time_range = latest - earliest

    # Create the flame chart using Matplotlib
    _, ax = plt.subplots()

    u_nodes = list(set(u_nodes))
    n = len(u_nodes)

    cmap = plt.get_cmap("rainbow")
    colors = [cmap(i / n) for i in range(n)]
    segmented_cmap = ListedColormap(colors)
    action_colors = {action: segmented_cmap(i / n) for i, action in enumerate(u_nodes)}

    node_names = {}

    for i, (test_name, actions) in enumerate(test_actions.items()):
        for action, start, end in actions:
            # Adjust timestamps to start from 0
            adjusted_start = start - earliest
            adjusted_end = end - earliest

            exec_block = ax.barh(
                test_name, adjusted_end - adjusted_start, left=adjusted_start, color=action_colors.get(action, "black")
            )[0]
            node_names[exec_block] = action

    for c in ax.containers:
        exec_block = c[0]
        ax.bar_label(c, labels=[node_names[exec_block]], label_type="center")

    # Set x-axis limits
    ax.set_xlim(0, time_range)

    ax.set_xlabel("Time (seconds)", fontsize=20, weight="semibold")
    ax.set_ylabel("Tasks", fontsize=20, weight="semibold")
    ax.set_title("Execution Concurrency Flame Chart")

    ax.tick_params(axis='both', which='major', labelsize=20)
    ax.set_axisbelow(True)
    ax.grid(axis="x")

    plt.show()


def init_collection() -> None:
    if os.path.exists(COLLECTION_FILE):
        os.remove(COLLECTION_FILE)


class SingletonMeta(type):
    """Singleton metaclass"""
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class LoggingManager(metaclass=SingletonMeta):
    """
    Singleton logging manager class used throughout the scheduler to have a centralized log formatting.

    The format is: <date> | <level> [| <caller>] | <message>
    """
    loggers: dict[str, loguru.Logger] = {}
    mu = Lock()
    fmt = ""

    def __init__(self, save_logs: bool = True, verbose: bool = False, debug: bool = False):
        if debug:
            LoggingManager.fmt = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>[{extra[app]}] {message}</level>"
        else:
            LoggingManager.fmt = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>[{extra[app]}] {message}</level>"

        log_lvl = "DEBUG" if verbose else "INFO"

        logger.remove(0)
        logger.add(sys.stdout, level=log_lvl, format=LoggingManager.fmt)
        logger.add(DBLogs.db_sink, level=log_lvl)

        if save_logs:
            init_collection()
            logger.add("scheduler.log", format=LoggingManager.fmt, level=log_lvl, rotation="10 MB")

    @classmethod
    def insert_data_sample(cls, task_id: str, wf_id: int, name: str, start: float, end: float) -> None:
        with cls.mu:
            DBExecutionLogs.insert(DatabaseConnector(), task_id, wf_id, name, start, end)

    @classmethod
    def add_ink(cls, sink: Callable[[str], None], log_lvl: str = "INFO") -> None:
        logger.add(sink, format=cls.fmt, level=log_lvl)

    @classmethod
    def get_logger(cls, _id: str, **bind_kwargs) -> loguru.Logger:
        if _id not in cls.loggers:
            if 'app' not in bind_kwargs:
                bind_kwargs['app'] = "General"
            cls.loggers[_id] = logger.bind(**bind_kwargs)
        return cls.loggers[_id]


if __name__ == "__main__":
    _visualize()
