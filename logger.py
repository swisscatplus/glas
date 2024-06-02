from __future__ import annotations

import csv
import os
import sys

import loguru
import matplotlib
import matplotlib.pyplot as plt
from loguru import logger
from matplotlib.colors import ListedColormap

COLLECTION_FILE = "./task_execution_logs.csv"


def _visualize():
    font = {'weight': 'semibold',
            'size': 16}

    matplotlib.rc('font', **font)

    data = []
    with open(COLLECTION_FILE, "r", newline="") as file:
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

        if end_time > latest:
            latest = end_time

        if start_time < earliest:
            earliest = start_time

        if test_name not in test_actions:
            test_actions[test_name] = []

        u_nodes.append(action)
        test_actions[test_name].append((action, start_time, end_time))

    # Calculate the time range
    time_range = latest - earliest

    # Create the flame chart using Matplotlib
    fig, ax = plt.subplots()

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

            bar = ax.barh(
                test_name, adjusted_end - adjusted_start, left=adjusted_start, color=action_colors.get(action, "black")
            )[0]
            node_names[bar] = action

    for c in ax.containers:
        bar = c[0]
        ax.bar_label(c, labels=[node_names[bar]], label_type="center")

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


def insert_data_sample(task_id: str, wf_name: str, id: str, start: float, end: float) -> None:
    with open(COLLECTION_FILE, "a+", newline="") as file:
        csv_writer = csv.writer(file)
        csv_writer.writerow([task_id, wf_name, id, start, end])


class SingletonMeta(type):
    _instances = {}

    def __call__(cls, *args, **kwargs):
        if cls not in cls._instances:
            instance = super().__call__(*args, **kwargs)
            cls._instances[cls] = instance
        return cls._instances[cls]


class LoggingManager(metaclass=SingletonMeta):
    loggers: dict[str, loguru.Logger] = {}

    def __init__(self, save_logs: bool = True, debug: bool = False):
        if debug:
            fmt = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - <level>[{extra[app]}] {message}</level>"
        else:
            fmt = "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | <level>{level: <8}</level> | <level>[{extra[app]}] {message}</level>"

        logger.remove(0)
        logger.add(
            sys.stdout,
            level="TRACE",
            format=fmt,
        )

        if save_logs:
            init_collection()
            logger.add("scheduler.log", format=fmt, rotation="10 MB")

    @classmethod
    def get_logger(cls, _id: str, **bind_kwargs) -> loguru.Logger:
        if _id not in cls.loggers:
            cls.loggers[_id] = logger.bind(**bind_kwargs)
        return cls.loggers[_id]


if __name__ == "__main__":
    _visualize()
