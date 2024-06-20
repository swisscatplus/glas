from typing import Optional

from glas.database import DatabaseConnector


class DBAccessLogs:
    __tablename__ = "access_logs"

    @classmethod
    def insert(cls, db: DatabaseConnector, host: str, authorized: bool, identifier: Optional[str], path: str,
               method: str):
        sql = f"INSERT INTO {cls.__tablename__}(host, authorized, identifier, path, method) VALUES(%s, %s, %s, %s, %s)"
        data = (host, authorized, identifier, path, method)
        db.cursor.execute(sql, data)
