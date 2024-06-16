"""
This module provides functionality for connecting to the database.
"""

import os

from mysql import connector
import mysql.connector.errorcode


class DatabaseConnector:
    """
    Database Connector class needed when executing a database query. Prefer using a new connection whenever possible to
    avoid having pending transactions.

    For example, create a new connection for every single route you have defined in the scheduler.
    """
    def __init__(self) -> None:
        try:
            self.conn = connector.connect(
                user=os.getenv("DATABASE_USER"),
                password=os.getenv("DATABASE_PASSWORD"),
                host=os.getenv("DATABASE_HOST"),
                database=os.getenv("DATABASE_NAME"),
                port=os.getenv("DATABASE_PORT"),
            )
            self.conn.autocommit = True
            self.cursor = self.conn.cursor(dictionary=True)
        except mysql.connector.errors.DatabaseError:
            self.cursor = None

    def is_connected(self) -> bool:
        if not self.cursor:
            return False

        try:
            self.conn.ping()
        except connector.InterfaceError:
            return False
        return True
