import os

import mysql.connector as connector
import mysql.connector.errorcode


class DatabaseConnector:
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
        except:
            return False
        return True
