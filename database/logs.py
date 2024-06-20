import datetime

from glas.database import DatabaseConnector
from glas.database.models import DBLogsModel


class DBLogs:
    __tablename__ = "logs"

    @classmethod
    def db_sink(cls, message):
        record = message.record
        db = DatabaseConnector()

        if db.cursor is not None:
            cls.insert(db, record["time"], record["extra"]["app"], record["level"].name,
                       record["name"], record["function"], record["line"], record["message"])

    @classmethod
    def get_all(cls, db: DatabaseConnector) -> list[DBLogsModel]:
        sql = f"SELECT * FROM (SELECT * FROM {cls.__tablename__} ORDER BY timestamp DESC LIMIT 1000) as d ORDER BY timestamp"
        db.cursor.execute(sql)
        return [DBLogsModel(**entry) for entry in db.cursor.fetchall()]

    @classmethod
    def insert(cls, db: DatabaseConnector, timestamp: datetime.datetime, logger_name: str, log_level: str, module: str,
               function: str, line: int,
               message: str):
        sql = f"INSERT INTO {cls.__tablename__}(timestamp, logger_name, log_level, module, caller, line, message) VALUES(%s, %s, %s, %s, %s, %s, %s)"
        data = (timestamp, logger_name, log_level, module, function, line, message)
        db.cursor.execute(sql, data)
