import sys

from loguru import logger


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
